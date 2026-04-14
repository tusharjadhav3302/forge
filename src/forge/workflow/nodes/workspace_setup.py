"""Workspace setup node for LangGraph workflow."""

import logging
from typing import Any

from forge.orchestrator.state import WorkflowState, update_state_timestamp
from forge.workspace.git_ops import GitOperations
from forge.workspace.guardrails import GuardrailsLoader
from forge.workspace.manager import WorkspaceManager

logger = logging.getLogger(__name__)

# Global workspace manager instance
_workspace_manager: WorkspaceManager | None = None


def get_workspace_manager() -> WorkspaceManager:
    """Get the global workspace manager."""
    global _workspace_manager
    if _workspace_manager is None:
        _workspace_manager = WorkspaceManager()
    return _workspace_manager


async def setup_workspace(state: WorkflowState) -> WorkflowState:
    """Set up an ephemeral workspace for code execution.

    This node:
    1. Creates a temporary workspace directory
    2. Clones the target repository
    3. Creates a feature branch
    4. Loads guardrails (constitution/agents.md)
    5. Stores workspace path in state

    Args:
        state: Current workflow state with tasks_by_repo.

    Returns:
        Updated state with workspace_path set.
    """
    ticket_key = state["ticket_key"]
    current_repo = state.get("current_repo")
    tasks_by_repo = state.get("tasks_by_repo", {})

    # Determine which repo to set up
    if not current_repo:
        # Pick the first repository with tasks
        repos = list(tasks_by_repo.keys())
        if not repos:
            logger.error(f"No repositories found for {ticket_key}")
            return {
                **state,
                "last_error": "No repositories to process",
                "current_node": "setup_workspace",
            }
        current_repo = repos[0]

    # Validate repository name
    if current_repo == "unknown" or "/" not in current_repo:
        logger.error(
            f"Invalid repository name '{current_repo}' for {ticket_key}. "
            "Repository must be in 'owner/repo' format."
        )
        return {
            **state,
            "last_error": f"Invalid repository '{current_repo}'. Tasks must specify a valid 'owner/repo' format.",
            "current_node": "setup_workspace",
        }

    logger.info(f"Setting up workspace for {current_repo} ({ticket_key})")

    manager = get_workspace_manager()

    try:
        # Create workspace
        logger.info(f"Creating workspace directory for {current_repo}...")
        workspace = manager.create_workspace(
            repo_name=current_repo,
            ticket_key=ticket_key,
        )
        logger.info(f"Workspace directory created: {workspace.path}")

        # Initialize git operations
        logger.info(f"Initializing git operations for {workspace}")
        git = GitOperations(workspace)

        # Clone repository (600s timeout)
        logger.info(f"Starting clone of {current_repo} (this may take several minutes for large repos)...")
        git.clone()
        logger.info(f"Clone completed successfully for {current_repo}")

        # Create feature branch
        git.create_branch()

        # Create .forge directory for task handoff
        forge_dir = workspace.path / ".forge"
        forge_dir.mkdir(exist_ok=True)
        (forge_dir / "history").mkdir(exist_ok=True)

        # Ensure .forge/ is in .gitignore to prevent accidental commits
        gitignore_path = workspace.path / ".gitignore"
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            if ".forge" not in content:
                if not content.endswith("\n"):
                    content += "\n"
                content += "\n# Forge workflow state (do not commit)\n.forge/\n"
                gitignore_path.write_text(content)
        else:
            gitignore_path.write_text("# Forge workflow state (do not commit)\n.forge/\n")

        logger.info("Created .forge directory for task handoff")

        # Load guardrails
        loader = GuardrailsLoader(workspace.path)
        guardrails = loader.load()

        # Store guardrails context in state
        context: dict[str, Any] = state.get("context", {})
        context["guardrails"] = guardrails.get_system_context()
        context["current_repo"] = current_repo
        context["branch_name"] = workspace.branch_name

        logger.info(f"Workspace ready: {workspace}")

        return update_state_timestamp({
            **state,
            "workspace_path": str(workspace.path),
            "current_repo": current_repo,
            "context": context,
            "current_node": "implementation",
            "last_error": None,
        })

    except Exception as e:
        logger.error(f"Workspace setup failed for {ticket_key}: {e}")
        # Post error notification to Jira
        from forge.workflow.nodes.error_handler import notify_error
        await notify_error(state, str(e), "setup_workspace")
        return {
            **state,
            "last_error": str(e),
            "current_node": "setup_workspace",
            "retry_count": state.get("retry_count", 0) + 1,
        }


async def teardown_workspace(state: WorkflowState) -> WorkflowState:
    """Tear down the workspace after PR creation.

    Args:
        state: Current workflow state with workspace_path.

    Returns:
        Updated state with workspace_path cleared.
    """
    ticket_key = state["ticket_key"]
    workspace_path = state.get("workspace_path")

    if not workspace_path:
        logger.debug(f"No workspace to tear down for {ticket_key}")
        return state

    logger.info(f"Tearing down workspace for {ticket_key}")

    manager = get_workspace_manager()

    try:
        current_repo = state.get("current_repo", "")
        workspace = manager.get_workspace(ticket_key, current_repo)

        if workspace:
            manager.destroy_workspace(workspace)
            logger.info(f"Workspace destroyed: {workspace}")

        return update_state_timestamp({
            **state,
            "workspace_path": None,
            "current_node": "workspace_complete",
            "last_error": None,
        })

    except Exception as e:
        logger.error(f"Workspace teardown failed for {ticket_key}: {e}")
        # Don't fail the workflow on teardown errors
        return {
            **state,
            "workspace_path": None,
            "last_error": f"Teardown warning: {e}",
        }
