"""Orchestrator worker that consumes events from Redis and processes them."""

import asyncio
import contextlib
import logging
import signal
import sys
import uuid
from typing import Any

from forge.api.routes.metrics import (
    record_workflow_completed,
    record_workflow_failed,
    record_workflow_started,
)
from forge.config import get_settings
from forge.models.events import EventSource
from forge.models.workflow import TicketType
from forge.orchestrator.checkpointer import get_checkpointer
from forge.queue.consumer import QueueConsumer
from forge.queue.models import QueueMessage
from forge.workflow.registry import create_default_router
from forge.workflow.router import WorkflowRouter
from forge.workflow.utils.comment_classifier import CommentType, classify_comment

logger = logging.getLogger(__name__)


class OrchestratorWorker:
    """Worker that processes workflow events from Redis queue."""

    def __init__(
        self,
        consumer_name: str | None = None,
        router: WorkflowRouter | None = None,
    ) -> None:
        """Initialize the worker.

        Args:
            consumer_name: Unique name for this consumer. Auto-generated if not provided.
            router: WorkflowRouter for selecting workflows. Uses default if not provided.
        """
        self.settings = get_settings()
        self.consumer_name = consumer_name or f"worker-{uuid.uuid4().hex[:8]}"
        self.consumer = QueueConsumer(self.consumer_name)
        self.router = router or create_default_router()
        self._shutdown_event = asyncio.Event()
        self._checkpointer = None
        self._compiled_workflows: dict[str, Any] = {}  # Cache compiled workflows by name

    async def _handle_jira_event(self, message: QueueMessage) -> None:
        """Handle a Jira webhook event.

        Args:
            message: The queue message to process.
        """
        await self._process_workflow(message)

    async def _handle_github_event(self, message: QueueMessage) -> None:
        """Handle a GitHub webhook event.

        Args:
            message: The queue message to process.
        """
        await self._process_workflow(message)

    async def _process_workflow(self, message: QueueMessage) -> None:
        """Process a message through the workflow.

        Args:
            message: The queue message to process.
        """
        ticket_key = message.ticket_key
        logger.info(f"Processing {message.source.value} event for {ticket_key}")

        try:
            # Determine ticket type early to select workflow
            ticket_type = self._extract_ticket_type(message)

            workflow_instance = None
            existing_state = None
            config = {"configurable": {"thread_id": ticket_key}}

            if ticket_type == TicketType.UNKNOWN:
                # GitHub events (and other non-Jira sources) don't carry ticket type.
                # Find the workflow by scanning checkpoint state across all registered workflows.
                workflow_instance, existing_state = await self._find_workflow_by_state(ticket_key)
                if workflow_instance is None:
                    logger.warning(
                        f"No existing workflow state found for {ticket_key} "
                        f"({message.source.value} event with unknown ticket type). Skipping."
                    )
                    return
                # Recover ticket type from checkpointed state so metrics are accurate.
                if existing_state and existing_state.values:
                    stored_type = existing_state.values.get("ticket_type", "Unknown")
                    with contextlib.suppress(ValueError):
                        ticket_type = TicketType(stored_type)
                logger.info(
                    f"Resolved workflow for {ticket_key} from checkpoint state "
                    f"(type={ticket_type}, workflow={workflow_instance.name})"
                )
            else:
                # Use router to resolve which workflow to use
                workflow_instance = self.router.resolve(
                    ticket_type=ticket_type,
                    labels=[],  # TODO: Extract labels from message payload
                    event=message.payload,
                )

                if workflow_instance is None:
                    logger.error(
                        f"No workflow found for ticket {ticket_key} "
                        f"(type={ticket_type}). Skipping."
                    )
                    return

            # Get or compile the workflow graph
            compiled_workflow = self._get_compiled_workflow(workflow_instance)

            # Fetch existing state if not already loaded (non-GitHub path)
            if existing_state is None:
                existing_state = await compiled_workflow.aget_state(config)

            # Debug logging for checkpoint state
            logger.debug(f"Existing state for {ticket_key}: {existing_state}")
            if existing_state:
                logger.debug(f"State values: {existing_state.values}")
                logger.debug(f"is_paused: {existing_state.values.get('is_paused') if existing_state.values else None}")

            # Check if we should resume an existing workflow
            should_resume = False
            if existing_state and existing_state.values:
                values = existing_state.values
                current_node = values.get("current_node", "")
                is_paused = values.get("is_paused", False)
                has_error = values.get("last_error") is not None

                # Resume if: explicitly paused, or has a node state (not at start/end)
                if is_paused:
                    should_resume = True
                    logger.info(f"Workflow is paused at {current_node}")
                elif current_node and current_node not in ("entry", "__end__", ""):
                    # Workflow has progress - resume from current state
                    should_resume = True
                    if has_error:
                        logger.info(f"Workflow has error at {current_node}, resuming")
                    else:
                        logger.info(f"Workflow in progress at {current_node}, resuming")

            if should_resume:
                # Resume workflow - check for approval/rejection signals
                updated_values = await self._handle_resume_event(message, existing_state.values)
                logger.info(f"Resuming workflow for {ticket_key}")

                # Check if we're retrying from an error state
                was_errored = (
                    not existing_state.values.get("is_paused")
                    and existing_state.values.get("last_error") is not None
                )

                # Nodes that wait for external events (CI webhooks, human review)
                # must be re-invoked fresh so route_by_ticket_type re-runs them.
                # ainvoke(None) only replays the routing edge after the node, not
                # the node itself, so CI status would never be re-checked.
                needs_fresh_invoke = updated_values.get("current_node") in (
                    "ci_evaluator",
                    "attempt_ci_fix",
                    "ai_review",
                    "human_review_gate",
                )

                if was_errored or needs_fresh_invoke:
                    logger.info(
                        f"{'Retrying' if was_errored else 'Re-invoking'} workflow "
                        f"from {updated_values.get('current_node')}"
                    )
                    result = await compiled_workflow.ainvoke(updated_values, config=config)
                else:
                    # For normal resume (paused at approval gate): update state and continue
                    await compiled_workflow.aupdate_state(config, updated_values)
                    result = await compiled_workflow.ainvoke(None, config=config)
            else:
                # New workflow - build initial state
                state = self._build_initial_state(message)
                logger.info(f"Starting new workflow for {ticket_key}")

                # Record workflow started metric
                ticket_type_str = state.get("ticket_type", "unknown")
                record_workflow_started(ticket_type=ticket_type_str)

                # Run the workflow from the beginning
                result = await compiled_workflow.ainvoke(state, config=config)

            final_node = result.get("current_node", "unknown")
            is_paused = result.get("is_paused", False)
            logger.info(
                f"Workflow completed for {ticket_key}, "
                f"final node: {final_node}, "
                f"paused: {is_paused}"
            )

            # Record workflow completed metric (only if not paused - paused means waiting for approval)
            if not is_paused:
                ticket_type = result.get("ticket_type", "unknown")
                record_workflow_completed(ticket_type=ticket_type, final_node=final_node)

        except Exception as e:
            import traceback
            logger.error(f"Workflow failed for {ticket_key}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Record workflow failed metric
            record_workflow_failed(ticket_type="unknown", error_type=type(e).__name__)
            raise  # Let consumer handle retry logic

    async def _handle_resume_event(
        self, message: QueueMessage, current_state: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle a resume event for a paused workflow.

        Detects approval/rejection signals from the webhook payload.

        Args:
            message: The queue message.
            current_state: Current workflow state from checkpoint.

        Returns:
            Updated state for workflow resumption.
        """
        payload = message.payload
        changelog = payload.get("changelog", {})
        comment = payload.get("comment", {})

        # Check for label changes indicating approval or retry
        label_changes = [
            item for item in changelog.get("items", [])
            if item.get("field") == "labels"
        ]

        is_approved = False
        is_rejected = False
        is_retry = False
        is_question = False
        feedback = None

        current_node = current_state.get("current_node", "")

        for change in label_changes:
            to_labels = change.get("toString", "")
            from_labels = change.get("fromString", "")

            # Check for retry label - triggers retry of current stage
            if "forge:retry" in to_labels.lower() and "forge:retry" not in from_labels.lower():
                is_retry = True
                logger.info(
                    f"Detected retry signal via forge:retry label for {current_node}"
                )

            # Check for approval labels - but only if it matches the current stage
            if "approved" in to_labels.lower() and "pending" in from_labels.lower():
                # Validate the approval matches the workflow stage
                approval_stage = None
                if "prd-approved" in to_labels.lower():
                    approval_stage = "prd"
                elif "spec-approved" in to_labels.lower():
                    approval_stage = "spec"
                elif "plan-approved" in to_labels.lower():
                    approval_stage = "plan"
                elif "task-approved" in to_labels.lower():
                    approval_stage = "task"

                # Map current node to expected approval stage
                node_to_stage = {
                    "prd_approval_gate": "prd",
                    "generate_prd": "prd",
                    "regenerate_prd": "prd",
                    "spec_approval_gate": "spec",
                    "generate_spec": "spec",
                    "regenerate_spec": "spec",
                    "plan_approval_gate": "plan",
                    "decompose_epics": "plan",
                    "regenerate_all_epics": "plan",
                    "update_single_epic": "plan",
                    "task_approval_gate": "task",
                    "generate_tasks": "task",
                }
                expected_stage = node_to_stage.get(current_node)

                if approval_stage and expected_stage and approval_stage == expected_stage:
                    is_approved = True
                    logger.info(
                        f"Detected {approval_stage} approval via label change: "
                        f"{from_labels} -> {to_labels}"
                    )
                elif approval_stage:
                    logger.warning(
                        f"Ignoring {approval_stage} approval - workflow at {current_node} "
                        f"(expects {expected_stage})"
                    )

        # Check for rejection comment (contains feedback)
        # Determine if comment is on Epic/Task (child) vs Feature (parent)
        # based on current workflow phase
        comment_ticket_key = None
        comment_ticket_type = None  # "epic" or "task"
        if comment:
            comment_body = comment.get("body", "")
            # Extract text from ADF if needed
            if isinstance(comment_body, dict):
                comment_body = self._extract_text_from_adf(comment_body)

            if comment_body.strip():
                comment_type = classify_comment(comment_body)

                if comment_type == CommentType.QUESTION:
                    is_question = True
                    feedback = comment_body
                    logger.info(f"Detected question comment: {feedback[:100]}...")
                elif comment_type == CommentType.APPROVAL:
                    # Approval via comment (not label) - set approved flag
                    is_approved = True
                    logger.info(f"Detected approval comment: {comment_body[:100]}...")
                else:
                    # Treat as feedback for rejection
                    is_rejected = True
                    feedback = comment_body

                # Determine workflow phase from current_node for feedback/questions
                # (skip for approvals since they don't have feedback)
                if feedback:
                    workflow_ticket_key = current_state.get("ticket_key", "")
                    epic_keys = current_state.get("epic_keys", [])
                    task_keys = current_state.get("task_keys", [])

                    # Determine which phase we're in based on current_node
                    plan_phase_nodes = (
                        "plan_approval_gate", "decompose_epics",
                        "regenerate_all_epics", "update_single_epic",
                    )
                    task_phase_nodes = (
                        "task_approval_gate", "generate_tasks",
                        "regenerate_all_tasks", "update_single_task",
                    )

                    if message.ticket_key != workflow_ticket_key:
                        # Comment is on a child ticket - determine type by phase
                        if current_node in plan_phase_nodes:
                            # In plan phase - check if it's an Epic
                            if message.ticket_key in epic_keys:
                                comment_ticket_key = message.ticket_key
                                comment_ticket_type = "epic"
                                logger.info(
                                    f"Detected Epic-level comment on {comment_ticket_key}: "
                                    f"{feedback[:100]}..."
                                )
                            else:
                                logger.info(
                                    f"Detected comment on child ticket {message.ticket_key} "
                                    f"(not in epic_keys): {feedback[:100]}..."
                                )
                        elif current_node in task_phase_nodes:
                            # In task phase - check if it's a Task
                            if message.ticket_key in task_keys:
                                comment_ticket_key = message.ticket_key
                                comment_ticket_type = "task"
                                logger.info(
                                    f"Detected Task-level comment on {comment_ticket_key}: "
                                    f"{feedback[:100]}..."
                                )
                            else:
                                logger.info(
                                    f"Detected comment on child ticket {message.ticket_key} "
                                    f"(not in task_keys): {feedback[:100]}..."
                                )
                        else:
                            # Not in a phase that handles child comments
                            logger.info(
                                f"Detected comment on child ticket {message.ticket_key} "
                                f"at unexpected node {current_node}: {feedback[:100]}..."
                            )
                    else:
                        logger.info(
                            f"Detected Feature-level comment: {feedback[:100]}..."
                        )

        # Build updated state
        updated_state = {
            **current_state,
            "is_paused": False,
            "context": {
                **current_state.get("context", {}),
                "resume_event": message.event_type,
                "payload": payload,
            },
        }

        # Check if workflow was in an error state (not paused, but has error)
        was_errored = (
            not current_state.get("is_paused")
            and current_state.get("last_error") is not None
        )

        # Check if workflow is at a terminal state (complete)
        terminal_states = ("complete", "complete_tasks", "aggregate_feature_status")
        is_terminal = current_node in terminal_states

        if is_retry:
            # Explicit retry signal - but only if there's an error to retry from
            prev_error = current_state.get("last_error")
            if not prev_error and not was_errored:
                logger.info(
                    f"Ignoring forge:retry for {message.ticket_key} - no error to retry from"
                )
                return current_state

            logger.info(
                f"Retry requested for {message.ticket_key} at {current_node} "
                f"(clearing error: {prev_error[:100] if prev_error else 'none'})"
            )
            updated_state["last_error"] = None
            updated_state["revision_requested"] = False
            updated_state["feedback_comment"] = None
            updated_state["terminal_error_notified"] = False  # Reset for next potential error
            updated_state["retry_count"] = 0  # Reset retry counter for fresh start
            # For terminal states, route back to task_router to retry implementation
            if is_terminal:
                logger.info(
                    f"Terminal state retry: resetting {current_node} -> task_router"
                )
                updated_state["current_node"] = "task_router"
            # Otherwise keep current_node so we retry the same stage
        elif is_approved:
            updated_state["revision_requested"] = False
            updated_state["feedback_comment"] = None
            updated_state["last_error"] = None
        elif is_question:
            updated_state["is_question"] = True
            updated_state["feedback_comment"] = feedback
            updated_state["revision_requested"] = False
            # Keep is_paused=False so workflow can process the question
        elif is_rejected and feedback:
            updated_state["revision_requested"] = True
            updated_state["feedback_comment"] = feedback
            # Set current_epic_key or current_task_key based on comment type
            if comment_ticket_key and comment_ticket_type == "epic":
                updated_state["current_epic_key"] = comment_ticket_key
                updated_state["current_task_key"] = None
            elif comment_ticket_key and comment_ticket_type == "task":
                updated_state["current_task_key"] = comment_ticket_key
                updated_state["current_epic_key"] = None
            else:
                # Feature-level comment - clear both
                updated_state["current_task_key"] = None
                updated_state["current_epic_key"] = None
        elif was_errored:
            # Workflow had an error - check if we should retry
            if is_terminal and not is_retry:
                # Terminal state without explicit retry - don't restart
                last_error = current_state.get("last_error", "Unknown error")
                logger.info(
                    f"Workflow for {message.ticket_key} is at terminal state '{current_node}' "
                    f"with error, ignoring event (use forge:retry label to restart)"
                )
                # Post a comment to Jira explaining how to retry (only once)
                if not current_state.get("terminal_error_notified"):
                    await self._post_terminal_error_comment(
                        message.ticket_key, last_error
                    )
                    # Mark as notified so we don't post again
                    return {**current_state, "terminal_error_notified": True}
                # Return current state as-is (no changes)
                return current_state
            else:
                # Non-terminal state, or explicit retry requested - clear error
                prev_error = current_state.get("last_error", "")
                logger.info(
                    f"Clearing last_error for {message.ticket_key} to allow retry "
                    f"(was: {prev_error[:100] if prev_error else 'unknown'})"
                )
                updated_state["last_error"] = None

        return updated_state

    @staticmethod
    def _extract_text_from_adf(adf: dict) -> str:
        """Extract plain text from Atlassian Document Format."""
        if not isinstance(adf, dict):
            return str(adf) if adf else ""

        texts = []
        for node in adf.get("content", []):
            if node.get("type") == "paragraph":
                for child in node.get("content", []):
                    if child.get("type") == "text":
                        texts.append(child.get("text", ""))
        return " ".join(texts)

    async def _post_terminal_error_comment(
        self, ticket_key: str, error: str
    ) -> None:
        """Post a comment explaining how to retry a terminal error.

        Args:
            ticket_key: The Jira ticket key.
            error: The error message.
        """
        from forge.integrations.jira.client import JiraClient

        try:
            jira = JiraClient()
            error_preview = error[:200] if error else "Unknown error"
            comment = (
                f"*Forge workflow stopped with error:*\n\n"
                f"{{code}}{error_preview}{{code}}\n\n"
                f"To retry the workflow, add the label `forge:retry` to this ticket."
            )
            await jira.add_comment(ticket_key, comment)
            await jira.close()
            logger.info(f"Posted terminal error comment to {ticket_key}")
        except Exception as e:
            logger.warning(f"Failed to post terminal error comment to {ticket_key}: {e}")

    async def _find_workflow_by_state(self, ticket_key: str) -> tuple[Any, Any]:
        """Find a workflow that has existing checkpoint state for the given ticket.

        Used when the ticket type cannot be determined from the event payload
        (e.g. GitHub webhooks). Checks all registered workflows and returns the
        first one that has a non-empty checkpoint for this ticket.

        Args:
            ticket_key: The Jira ticket key.

        Returns:
            Tuple of (workflow_instance, checkpoint_state), or (None, None) if
            no existing state is found.
        """
        config = {"configurable": {"thread_id": ticket_key}}
        for workflow_class in self.router._workflows:
            workflow_instance = workflow_class()
            compiled = self._get_compiled_workflow(workflow_instance)
            state = await compiled.aget_state(config)
            if state and state.values:
                logger.debug(
                    f"Found existing state for {ticket_key} "
                    f"in workflow '{workflow_instance.name}'"
                )
                return workflow_instance, state
        return None, None

    def _extract_ticket_type(self, message: QueueMessage) -> TicketType:
        """Extract ticket type from queue message.

        Args:
            message: The queue message.

        Returns:
            TicketType enum value.
        """
        if message.source == EventSource.JIRA:
            issue_data = message.payload.get("issue", {})
            fields = issue_data.get("fields", {})
            issue_type = fields.get("issuetype", {})
            ticket_type_str = issue_type.get("name", "Unknown")

            # Map string to TicketType enum
            try:
                return TicketType(ticket_type_str)
            except ValueError:
                logger.warning(
                    f"Unknown ticket type '{ticket_type_str}' for {message.ticket_key}"
                )
                return TicketType.UNKNOWN

        return TicketType.UNKNOWN

    def _get_compiled_workflow(self, workflow_instance: Any) -> Any:
        """Get or compile a workflow graph.

        Args:
            workflow_instance: A BaseWorkflow instance.

        Returns:
            Compiled workflow graph.
        """
        workflow_name = workflow_instance.name

        # Check cache
        if workflow_name in self._compiled_workflows:
            return self._compiled_workflows[workflow_name]

        # Build and compile the workflow graph
        logger.info(f"Compiling workflow: {workflow_name}")
        graph = workflow_instance.build_graph()
        compiled = graph.compile(checkpointer=self._checkpointer)

        # Cache it
        self._compiled_workflows[workflow_name] = compiled

        return compiled

    def _build_initial_state(self, message: QueueMessage) -> dict[str, Any]:
        """Build initial workflow state from queue message.

        Args:
            message: The queue message.

        Returns:
            Initial state dictionary.
        """
        # Extract ticket type from payload
        ticket_type = "Unknown"  # Require explicit type, don't default to Feature
        if message.source == EventSource.JIRA:
            issue_data = message.payload.get("issue", {})
            fields = issue_data.get("fields", {})
            issue_type = fields.get("issuetype", {})
            ticket_type = issue_type.get("name", "Unknown")

        # Validate ticket type - only Features and Bugs can start workflows directly
        valid_top_level_types = ("Feature", "Bug", "Story")
        if ticket_type not in valid_top_level_types:
            logger.warning(
                f"Ticket {message.ticket_key} has type '{ticket_type}' which cannot "
                f"start a workflow directly. Valid types: {valid_top_level_types}"
            )

        return {
            "ticket_key": message.ticket_key,
            "ticket_type": ticket_type,
            "event_type": message.event_type,
            "context": {
                "source": message.source.value,
                "event_id": message.event_id,
                "payload": message.payload,
            },
            "current_node": "entry",
            "is_paused": False,
            "retry_count": message.retry_count,
        }

    async def start(self) -> None:
        """Start the worker and begin processing events."""
        logger.info(f"Starting orchestrator worker: {self.consumer_name}")

        # Start Prometheus metrics HTTP server
        if self.settings.worker_metrics_enabled:
            from prometheus_client import start_http_server
            metrics_port = self.settings.worker_metrics_port
            start_http_server(metrics_port)
            logger.info(f"Worker metrics server started on port {metrics_port}")

        # Initialize checkpointer
        self._checkpointer = await get_checkpointer()
        logger.info("Checkpointer initialized")

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_shutdown)

        # Register handlers
        self.consumer.register_handler(EventSource.JIRA, self._handle_jira_event)
        self.consumer.register_handler(EventSource.GITHUB, self._handle_github_event)

        try:
            await self.consumer.start()
        except asyncio.CancelledError:
            pass
        finally:
            await self.consumer.stop()
            logger.info("Worker shut down gracefully")

    def _handle_shutdown(self) -> None:
        """Handle shutdown signal."""
        logger.info("Shutdown signal received")
        asyncio.create_task(self.consumer.stop())


async def run_single_ticket(ticket_key: str) -> dict[str, Any]:
    """Run workflow for a single ticket (for testing/CLI use).

    Args:
        ticket_key: The Jira ticket key to process.

    Returns:
        Final workflow state.
    """
    from forge.integrations.jira.client import JiraClient

    logger.info(f"Running workflow for {ticket_key}")

    # Fetch ticket to determine type
    jira = JiraClient()
    try:
        issue = await jira.get_issue(ticket_key)
        ticket_type_str = issue.issue_type
        # Convert string to TicketType enum
        try:
            ticket_type = TicketType(ticket_type_str)
        except ValueError:
            logger.warning(f"Unknown ticket type '{ticket_type_str}', using UNKNOWN")
            ticket_type = TicketType.UNKNOWN
    finally:
        await jira.close()

    # Create router and resolve workflow
    router = create_default_router()
    workflow_instance = router.resolve(
        ticket_type=ticket_type,
        labels=[],
        event={},
    )

    if workflow_instance is None:
        raise ValueError(f"No workflow found for ticket type: {ticket_type}")

    # Build and compile workflow
    checkpointer = await get_checkpointer()
    graph = workflow_instance.build_graph()
    compiled_workflow = graph.compile(checkpointer=checkpointer)

    initial_state = {
        "ticket_key": ticket_key,
        "ticket_type": ticket_type_str,
        "event_type": "manual_trigger",
        "context": {},
        "current_node": "entry",
        "is_paused": False,
        "retry_count": 0,
    }

    # Use ticket_key as thread_id for checkpointing
    config = {"configurable": {"thread_id": ticket_key}}

    result = await compiled_workflow.ainvoke(initial_state, config=config)
    logger.info(f"Workflow completed: {result.get('current_node')}")
    return result


def main() -> None:
    """Main entry point for the worker."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Check for single-ticket mode via command line
    if len(sys.argv) > 1:
        ticket_key = sys.argv[1]
        asyncio.run(run_single_ticket(ticket_key))
    else:
        # Run as continuous worker
        worker = OrchestratorWorker()
        asyncio.run(worker.start())


if __name__ == "__main__":
    main()
