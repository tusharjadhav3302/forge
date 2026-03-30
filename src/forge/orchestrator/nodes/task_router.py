"""Task router node for grouping Tasks by repository."""

import logging
from typing import Literal

from forge.orchestrator.state import WorkflowState, update_state_timestamp

logger = logging.getLogger(__name__)


async def route_tasks_by_repo(state: WorkflowState) -> WorkflowState:
    """Route Tasks by grouping them by target repository.

    This node analyzes the tasks_by_repo mapping and prepares
    for sequential or parallel execution based on repository count.

    Args:
        state: Current workflow state with tasks_by_repo.

    Returns:
        Updated state ready for workspace setup.
    """
    ticket_key = state["ticket_key"]
    tasks_by_repo = state.get("tasks_by_repo", {})

    if not tasks_by_repo:
        logger.warning(f"No tasks grouped by repo for {ticket_key}")
        return {
            **state,
            "last_error": "No tasks available for routing",
            "current_node": "route_tasks",
        }

    repo_count = len(tasks_by_repo)
    total_tasks = sum(len(tasks) for tasks in tasks_by_repo.values())

    logger.info(
        f"Routing {total_tasks} tasks across {repo_count} repos "
        f"for {ticket_key}"
    )

    # Initialize tracking state
    repos_to_process = list(tasks_by_repo.keys())

    return update_state_timestamp({
        **state,
        "repos_to_process": repos_to_process,
        "current_repo": repos_to_process[0] if repos_to_process else None,
        "repos_completed": [],
        "implemented_tasks": [],
        "current_node": "setup_workspace",
        "last_error": None,
    })


def route_after_pr(
    state: WorkflowState,
) -> Literal["setup_workspace", "complete", "task_router"]:
    """Route after PR creation to handle next repository or complete.

    Args:
        state: Current workflow state.

    Returns:
        Next node name.
    """
    repos_to_process = state.get("repos_to_process", [])
    repos_completed = state.get("repos_completed", [])
    current_repo = state.get("current_repo")

    # Mark current repo as completed
    if current_repo and current_repo not in repos_completed:
        repos_completed.append(current_repo)

    # Find next unprocessed repo
    remaining = [r for r in repos_to_process if r not in repos_completed]

    if remaining:
        logger.info(f"Moving to next repository: {remaining[0]}")
        return "setup_workspace"

    logger.info(f"All repositories processed for {state['ticket_key']}")
    return "complete"


def get_repo_execution_plan(state: WorkflowState) -> list[dict]:
    """Get the execution plan for all repositories.

    Args:
        state: Current workflow state.

    Returns:
        List of execution plans per repo.
    """
    tasks_by_repo = state.get("tasks_by_repo", {})
    repos_completed = state.get("repos_completed", [])

    plan = []
    for repo, tasks in tasks_by_repo.items():
        plan.append({
            "repo": repo,
            "task_count": len(tasks),
            "tasks": tasks,
            "status": "completed" if repo in repos_completed else "pending",
        })

    return plan
