"""Implementation node for executing Tasks using container sandbox.

This node runs AI-powered code implementation inside a podman container
for security isolation. The agent has full tool access (read, write, bash)
within the container but cannot access host systems.

Architecture:
- Container runs Deep Agents with FilesystemBackend
- Workspace is mounted at /workspace
- Agent commits changes locally
- Orchestrator (this node) handles git push after container exits
"""

import logging
from pathlib import Path

from forge.config import get_settings
from forge.integrations.jira.client import JiraClient
from forge.orchestrator.state import WorkflowState, update_state_timestamp
from forge.sandbox import ContainerRunner
from forge.sandbox.runner import ContainerConfig

logger = logging.getLogger(__name__)


async def implement_task(state: WorkflowState) -> WorkflowState:
    """Implement a single Task using container sandbox.

    This node:
    1. Gets the current Task to implement
    2. Spawns a container with the workspace mounted
    3. Container runs Deep Agents with full tool access
    4. Container runs local tests and commits changes
    5. Orchestrator (here) handles git push after success

    Args:
        state: Current workflow state.

    Returns:
        Updated state after implementation.
    """
    ticket_key = state["ticket_key"]
    workspace_path = state.get("workspace_path")
    current_task = state.get("current_task_key")
    task_keys = state.get("task_keys", [])

    if not workspace_path:
        logger.error(f"No workspace for implementation on {ticket_key}")
        return {
            **state,
            "last_error": "Workspace not set up",
            "current_node": "implement_task",
        }

    # Get next task to implement if not set
    if not current_task and task_keys:
        # Get tasks for current repo
        current_repo = state.get("current_repo", "")
        repo_tasks = state.get("tasks_by_repo", {}).get(current_repo, [])
        # Find first unimplemented task
        implemented = state.get("implemented_tasks", [])
        for task_key in repo_tasks:
            if task_key not in implemented:
                current_task = task_key
                break

    if not current_task:
        logger.info(f"All tasks implemented for {ticket_key}")
        return update_state_timestamp({
            **state,
            "current_node": "create_pr",
            "last_error": None,
        })

    logger.info(f"Implementing Task {current_task} for {ticket_key}")

    settings = get_settings()
    jira = JiraClient(settings)

    try:
        # Get Task details from Jira
        task_issue = await jira.get_issue(current_task)
        task_description = task_issue.description or ""
        task_summary = task_issue.summary

        # Get guardrails context
        guardrails = state.get("context", {}).get("guardrails", "")

        # Build full task description with context
        full_description = _build_task_description(
            task_summary=task_summary,
            task_description=task_description,
            guardrails=guardrails,
        )

        # Run implementation in container sandbox
        runner = ContainerRunner(settings)
        config = ContainerConfig(
            timeout_seconds=1800,  # 30 minutes
            max_retries=settings.ci_fix_max_retries,
        )

        result = await runner.run(
            workspace_path=Path(workspace_path),
            task_summary=task_summary,
            task_description=full_description,
            config=config,
        )

        if result.success:
            logger.info(f"Container completed successfully for {current_task}")

            # Track implemented tasks
            implemented = state.get("implemented_tasks", [])
            implemented.append(current_task)

            return update_state_timestamp({
                **state,
                "current_task_key": None,
                "implemented_tasks": implemented,
                "current_node": "implement_task",  # Loop back for next task
                "last_error": None,
                "retry_count": 0,  # Reset retry count on success
            })
        else:
            # Container failed - treat all failures the same
            # The container agent is responsible for running tests and only
            # committing when they pass. If we get here, implementation failed.
            error_msg = result.error_message or "Unknown container error"
            logger.error(f"Implementation failed for {current_task}: {error_msg}")
            raise RuntimeError(error_msg)

    except Exception as e:
        logger.error(f"Implementation failed for {current_task}: {e}")
        from forge.orchestrator.nodes.error_handler import notify_error
        await notify_error(state, str(e), "implement_task")
        return {
            **state,
            "last_error": str(e),
            "current_node": "implement_task",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await jira.close()


def _build_task_description(
    task_summary: str,
    task_description: str,
    guardrails: str,
) -> str:
    """Build the full task description for the container.

    Args:
        task_summary: Task title.
        task_description: Task details.
        guardrails: Project guardrails context.

    Returns:
        Full task description with all context.
    """
    parts = [
        f"# Task: {task_summary}",
        "",
        "## Description",
        task_description,
    ]

    if guardrails:
        parts.extend([
            "",
            "## Project Guidelines",
            guardrails,
        ])

    parts.extend([
        "",
        "## Instructions",
        "1. Read and understand the existing codebase",
        "2. Implement the task following the repository's coding standards",
        "3. Write clean, well-documented code",
        "4. Run tests to verify your changes work",
        "5. Commit your changes with a descriptive message",
    ])

    return "\n".join(parts)
