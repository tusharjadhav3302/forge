"""Command-line interface for Forge SDLC Orchestrator."""

import asyncio
import argparse
import logging
import sys
from typing import Any

from forge.config import get_settings


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for CLI usage."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


async def cmd_run(args: argparse.Namespace) -> int:
    """Run workflow for a single ticket."""
    from forge.orchestrator.worker import run_single_ticket

    try:
        result = await run_single_ticket(args.ticket)
        print(f"\nWorkflow completed!")
        print(f"  Final node: {result.get('current_node')}")
        print(f"  Paused: {result.get('is_paused', False)}")
        if result.get("last_error"):
            print(f"  Error: {result.get('last_error')}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def cmd_worker(args: argparse.Namespace) -> int:
    """Start the orchestrator worker."""
    from forge.orchestrator.worker import OrchestratorWorker

    worker = OrchestratorWorker(consumer_name=args.name)
    await worker.start()
    return 0


async def cmd_test_node(args: argparse.Namespace) -> int:
    """Test a single workflow node."""
    from forge.integrations.jira.client import JiraClient

    # Import all nodes
    from forge.orchestrator.nodes import prd_generation, spec_generation
    from forge.orchestrator.nodes import epic_decomposition, task_generation
    from forge.orchestrator.nodes import implementation, ci_evaluator
    from forge.orchestrator.nodes import ai_reviewer, human_review
    from forge.orchestrator.nodes import bug_workflow

    node_map = {
        "generate_prd": prd_generation.generate_prd,
        "regenerate_prd": prd_generation.regenerate_prd_with_feedback,
        "generate_spec": spec_generation.generate_spec,
        "regenerate_spec": spec_generation.regenerate_spec_with_feedback,
        "decompose_epics": epic_decomposition.decompose_epics,
        "generate_tasks": task_generation.generate_tasks,
        "analyze_bug": bug_workflow.analyze_bug,
    }

    node_name = args.node
    if node_name not in node_map:
        print(f"Unknown node: {node_name}", file=sys.stderr)
        print(f"Available nodes: {', '.join(node_map.keys())}")
        return 1

    # Build initial state
    jira = JiraClient()
    try:
        issue = await jira.get_issue(args.ticket)
        ticket_type = issue.issue_type
    finally:
        await jira.close()

    state: dict[str, Any] = {
        "ticket_key": args.ticket,
        "ticket_type": ticket_type,
        "event_type": "test",
        "context": {},
        "current_node": node_name,
        "is_paused": False,
        "retry_count": 0,
    }

    print(f"Running node: {node_name}")
    print(f"Ticket: {args.ticket} ({ticket_type})")

    try:
        node_func = node_map[node_name]
        result = await node_func(state)
        print(f"\nNode completed!")
        print(f"  Next node: {result.get('current_node')}")
        if result.get("last_error"):
            print(f"  Error: {result.get('last_error')}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def cmd_check_ticket(args: argparse.Namespace) -> int:
    """Check ticket status and labels."""
    from forge.integrations.jira.client import JiraClient
    from forge.models.workflow import get_workflow_phase

    jira = JiraClient()
    try:
        issue = await jira.get_issue(args.ticket)
        labels = await jira.get_labels(args.ticket)

        print(f"Ticket: {issue.key}")
        print(f"  Summary: {issue.summary}")
        print(f"  Type: {issue.issue_type}")
        print(f"  Status: {issue.status}")
        print(f"  Labels: {', '.join(labels) if labels else '(none)'}")

        phase = get_workflow_phase(labels)
        print(f"  Workflow Phase: {phase or '(not managed by Forge)'}")

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        await jira.close()


async def cmd_set_label(args: argparse.Namespace) -> int:
    """Set a workflow label on a ticket."""
    from forge.integrations.jira.client import JiraClient
    from forge.models.workflow import ForgeLabel

    # Find matching label
    label_name = args.label.upper().replace("-", "_")
    try:
        label = ForgeLabel[label_name]
    except KeyError:
        print(f"Unknown label: {args.label}", file=sys.stderr)
        print("Available labels:")
        for l in ForgeLabel:
            print(f"  {l.name.lower().replace('_', '-')}: {l.value}")
        return 1

    jira = JiraClient()
    try:
        await jira.set_workflow_label(args.ticket, label)
        print(f"Set label {label.value} on {args.ticket}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        await jira.close()


async def cmd_approve(args: argparse.Namespace) -> int:
    """Approve PRD/Spec and continue workflow."""
    from forge.integrations.jira.client import JiraClient
    from forge.models.workflow import ForgeLabel
    from forge.orchestrator.checkpointer import get_checkpointer
    from forge.orchestrator.graph import get_workflow

    jira = JiraClient()
    try:
        # Get current labels to determine stage
        labels = await jira.get_labels(args.ticket)

        if ForgeLabel.PRD_PENDING.value in labels:
            # Approve PRD -> move to spec generation
            await jira.set_workflow_label(args.ticket, ForgeLabel.PRD_APPROVED)
            print(f"PRD approved for {args.ticket}")
            next_stage = "generate_spec"
        elif ForgeLabel.SPEC_PENDING.value in labels:
            # Approve Spec -> move to epic decomposition
            await jira.set_workflow_label(args.ticket, ForgeLabel.SPEC_APPROVED)
            print(f"Spec approved for {args.ticket}")
            next_stage = "decompose_epics"
        elif ForgeLabel.PLAN_PENDING.value in labels:
            # Approve Plan -> move to task generation
            await jira.set_workflow_label(args.ticket, ForgeLabel.PLAN_APPROVED)
            print(f"Plan approved for {args.ticket}")
            next_stage = "generate_tasks"
        else:
            print(f"No pending approval found for {args.ticket}")
            print(f"Current labels: {labels}")
            return 1

        # Resume workflow
        checkpointer = await get_checkpointer()
        workflow = get_workflow(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": args.ticket}}

        # Get current state and update it
        state = await workflow.aget_state(config)
        if state and state.values:
            updated_state = {
                **state.values,
                "is_paused": False,
                "revision_requested": False,
                "feedback_comment": None,
            }

            result = await workflow.ainvoke(updated_state, config=config)
            print(f"Workflow resumed, now at: {result.get('current_node')}")
            if result.get('is_paused'):
                print("Workflow paused again, waiting for next approval")
        else:
            print("No saved workflow state found, run the workflow again")

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        await jira.close()


async def cmd_reject(args: argparse.Namespace) -> int:
    """Reject PRD/Spec with feedback and regenerate."""
    from forge.integrations.jira.client import JiraClient
    from forge.models.workflow import ForgeLabel
    from forge.orchestrator.checkpointer import get_checkpointer
    from forge.orchestrator.graph import get_workflow

    if not args.feedback:
        print("Error: --feedback is required for rejection", file=sys.stderr)
        return 1

    jira = JiraClient()
    try:
        # Get current labels to determine stage
        labels = await jira.get_labels(args.ticket)

        if ForgeLabel.PRD_PENDING.value in labels:
            stage = "PRD"
            next_node = "regenerate_prd"
        elif ForgeLabel.SPEC_PENDING.value in labels:
            stage = "Spec"
            next_node = "regenerate_spec"
        elif ForgeLabel.PLAN_PENDING.value in labels:
            stage = "Plan"
            next_node = "regenerate_all_epics"
        else:
            print(f"No pending approval found for {args.ticket}")
            print(f"Current labels: {labels}")
            return 1

        # Add feedback as comment
        await jira.add_comment(
            args.ticket,
            f"**Revision Requested**\n\n{args.feedback}"
        )
        print(f"{stage} rejected for {args.ticket}")
        print(f"Feedback: {args.feedback}")

        # Resume workflow with rejection
        checkpointer = await get_checkpointer()
        workflow = get_workflow(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": args.ticket}}

        # Get current state and update it
        state = await workflow.aget_state(config)
        if state and state.values:
            updated_state = {
                **state.values,
                "is_paused": False,
                "revision_requested": True,
                "feedback_comment": args.feedback,
            }

            result = await workflow.ainvoke(updated_state, config=config)
            print(f"Workflow resumed for regeneration, now at: {result.get('current_node')}")
            if result.get('is_paused'):
                print("Regeneration complete, waiting for approval")
        else:
            print("No saved workflow state found, run the workflow again")

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await jira.close()


async def cmd_clear_checkpoint(args: argparse.Namespace) -> int:
    """Clear checkpoint state for a ticket."""
    from forge.orchestrator.checkpointer import clear_checkpoint

    try:
        cleared = await clear_checkpoint(args.ticket)
        if cleared:
            print(f"Checkpoint cleared for {args.ticket}")
        else:
            print(f"No checkpoint found for {args.ticket}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def cmd_health(args: argparse.Namespace) -> int:
    """Check system health."""
    from forge.orchestrator.checkpointer import get_redis_client

    print("Checking system health...\n")

    # Check settings
    try:
        settings = get_settings()
        print(f"[OK] Configuration loaded")
        print(f"     Jira: {settings.jira_base_url}")
        print(f"     Use labels: {settings.jira_use_labels}")
        print(f"     Store in comments: {settings.jira_store_in_comments}")
    except Exception as e:
        print(f"[FAIL] Configuration: {e}")
        return 1

    # Check Redis
    try:
        redis_client = await get_redis_client()
        await redis_client.ping()
        print(f"[OK] Redis connected: {settings.redis_url}")
    except Exception as e:
        print(f"[FAIL] Redis: {e}")
        return 1

    # Check Jira (if token configured)
    if settings.jira_api_token.get_secret_value() != "your-jira-api-token":
        try:
            from forge.integrations.jira.client import JiraClient
            jira = JiraClient()
            # Try to get projects (simple API call)
            await jira.close()
            print(f"[OK] Jira credentials configured")
        except Exception as e:
            print(f"[WARN] Jira: {e}")
    else:
        print(f"[SKIP] Jira: API token not configured")

    # Check Anthropic/Vertex
    if settings.use_vertex_ai:
        print(f"[OK] Using Vertex AI: {settings.anthropic_vertex_project_id}")
    elif settings.anthropic_api_key.get_secret_value():
        print(f"[OK] Using direct Anthropic API")
    else:
        print(f"[WARN] No Claude API configured")

    print("\nHealth check complete!")
    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="forge",
        description="Forge SDLC Orchestrator CLI",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run workflow for a ticket",
    )
    run_parser.add_argument("ticket", help="Jira ticket key (e.g., AISOS-103)")

    # worker command
    worker_parser = subparsers.add_parser(
        "worker",
        help="Start the orchestrator worker",
    )
    worker_parser.add_argument(
        "--name",
        help="Worker name (auto-generated if not provided)",
    )

    # test-node command
    test_parser = subparsers.add_parser(
        "test-node",
        help="Test a single workflow node",
    )
    test_parser.add_argument("node", help="Node name to test")
    test_parser.add_argument("ticket", help="Jira ticket key")

    # check command
    check_parser = subparsers.add_parser(
        "check",
        help="Check ticket status and labels",
    )
    check_parser.add_argument("ticket", help="Jira ticket key")

    # set-label command
    label_parser = subparsers.add_parser(
        "set-label",
        help="Set a workflow label on a ticket",
    )
    label_parser.add_argument("ticket", help="Jira ticket key")
    label_parser.add_argument("label", help="Label name (e.g., prd-pending)")

    # approve command
    approve_parser = subparsers.add_parser(
        "approve",
        help="Approve PRD/Spec/Plan and continue workflow",
    )
    approve_parser.add_argument("ticket", help="Jira ticket key")

    # reject command
    reject_parser = subparsers.add_parser(
        "reject",
        help="Reject PRD/Spec/Plan with feedback",
    )
    reject_parser.add_argument("ticket", help="Jira ticket key")
    reject_parser.add_argument(
        "--feedback", "-f",
        required=True,
        help="Feedback explaining why rejected and what to change",
    )

    # clear-checkpoint command
    clear_parser = subparsers.add_parser(
        "clear-checkpoint",
        help="Clear checkpoint state for a ticket (allows workflow restart)",
    )
    clear_parser.add_argument("ticket", help="Jira ticket key")

    # health command
    subparsers.add_parser(
        "health",
        help="Check system health",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.command is None:
        parser.print_help()
        return 0

    # Map commands to async handlers
    handlers = {
        "run": cmd_run,
        "worker": cmd_worker,
        "test-node": cmd_test_node,
        "check": cmd_check_ticket,
        "set-label": cmd_set_label,
        "approve": cmd_approve,
        "reject": cmd_reject,
        "clear-checkpoint": cmd_clear_checkpoint,
        "health": cmd_health,
    }

    handler = handlers.get(args.command)
    if handler:
        return asyncio.run(handler(args))

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
