"""Implementation node for executing Tasks using Deep Agents."""

import logging
from pathlib import Path

from forge.config import get_settings
from forge.integrations.agents import ForgeAgent
from forge.integrations.jira.client import JiraClient
from forge.orchestrator.state import WorkflowState, update_state_timestamp
from forge.prompts import load_prompt
from forge.workspace.git_ops import GitOperations
from forge.workspace.manager import Workspace

logger = logging.getLogger(__name__)


async def implement_task(state: WorkflowState) -> WorkflowState:
    """Implement a single Task using Claude.

    This node:
    1. Gets the current Task to implement
    2. Invokes Claude with Task details and guardrails
    3. Applies code changes to the workspace
    4. Commits changes

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
    agent = ForgeAgent(settings)

    try:
        # Get Task details from Jira
        task_issue = await jira.get_issue(current_task)
        task_description = task_issue.description or ""
        task_summary = task_issue.summary

        # Get guardrails context
        guardrails = state.get("context", {}).get("guardrails", "")

        # Build implementation prompt
        user_prompt = _build_implementation_prompt(
            task_summary=task_summary,
            task_description=task_description,
            guardrails=guardrails,
            workspace_path=workspace_path,
        )

        # Invoke Deep Agents for implementation
        result = await agent.run_task(
            task="implement-task",
            prompt=user_prompt,
            context={
                "task_key": current_task,
                "task_summary": task_summary,
                "workspace_path": workspace_path,
            },
        )

        # Parse and apply code changes
        changes_applied = _apply_code_changes(
            result, Path(workspace_path)
        )

        # Commit changes
        workspace = Workspace(
            path=Path(workspace_path),
            repo_name=state.get("current_repo", ""),
            branch_name=state.get("context", {}).get("branch_name", ""),
            ticket_key=ticket_key,
        )
        git = GitOperations(workspace)
        git.stage_all()

        commit_msg = f"[{current_task}] {task_summary}"
        committed = git.commit(commit_msg)

        if committed:
            logger.info(f"Committed changes for {current_task}")
        else:
            logger.warning(f"No changes to commit for {current_task}")

        # Track implemented tasks
        implemented = state.get("implemented_tasks", [])
        implemented.append(current_task)

        return update_state_timestamp({
            **state,
            "current_task_key": None,
            "implemented_tasks": implemented,
            "current_node": "implement_task",  # Loop back for next task
            "last_error": None,
        })

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


def _build_implementation_prompt(
    task_summary: str,
    task_description: str,
    guardrails: str,
    workspace_path: str,
) -> str:
    """Build the implementation prompt for Claude.

    Args:
        task_summary: Task title.
        task_description: Task details.
        guardrails: Project guardrails context.
        workspace_path: Path to workspace.

    Returns:
        Formatted prompt.
    """
    guardrails_section = ""
    if guardrails:
        guardrails_section = f"## Project Guidelines\n{guardrails}\n"

    return load_prompt(
        "implement-task",
        task_summary=task_summary,
        task_description=task_description,
        guardrails_section=guardrails_section,
        workspace_path=workspace_path,
    )


def _apply_code_changes(
    response: str,
    workspace_path: Path,
) -> int:
    """Apply code changes from Claude's response.

    Args:
        response: Claude's response with code blocks.
        workspace_path: Path to apply changes.

    Returns:
        Number of files modified.
    """
    import re

    # Parse code blocks with file paths
    pattern = r"```([^\n]+)\n(.*?)```"
    matches = re.findall(pattern, response, re.DOTALL)

    files_modified = 0

    for file_path, content in matches:
        file_path = file_path.strip()

        # Skip non-file code blocks
        if file_path in ("", "python", "javascript", "bash", "shell"):
            continue
        if not file_path or "/" not in file_path:
            continue

        target_path = workspace_path / file_path

        try:
            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file content
            target_path.write_text(content.strip() + "\n")
            logger.info(f"Applied changes to {file_path}")
            files_modified += 1

        except Exception as e:
            logger.warning(f"Failed to apply changes to {file_path}: {e}")

    return files_modified
