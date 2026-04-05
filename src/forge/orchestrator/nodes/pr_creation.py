"""PR creation node for opening pull requests."""

import logging
from pathlib import Path

from forge.integrations.github.client import GitHubClient
from forge.integrations.jira.client import JiraClient
from forge.models.workflow import ForgeLabel
from forge.orchestrator.state import WorkflowState, update_state_timestamp
from forge.workspace.git_ops import GitError, GitOperations
from forge.workspace.manager import Workspace

logger = logging.getLogger(__name__)


async def check_merge_conflicts(
    git: GitOperations,
    target_branch: str = "main",
) -> tuple[bool, list[str]]:
    """Check if the branch would have merge conflicts with target.

    Simulates a merge to detect conflicts before PR creation.

    Args:
        git: GitOperations instance.
        target_branch: Target branch to merge into.

    Returns:
        Tuple of (has_conflicts, conflicting_files).
    """
    try:
        # Fetch latest target branch
        git._run_git("fetch", "origin", target_branch, check=False)

        # Try merge in dry-run mode
        result = git._run_git(
            "merge-tree",
            f"origin/{target_branch}",
            "HEAD",
            check=False,
        )

        # merge-tree outputs conflict markers if there would be conflicts
        output = result.stdout or ""

        if "CONFLICT" in output or "<<<<<<< " in output:
            # Parse conflicting files from output
            conflicting_files: list[str] = []
            for line in output.split("\n"):
                if line.startswith("CONFLICT"):
                    # Extract filename from "CONFLICT (content): Merge conflict in file.py"
                    if " in " in line:
                        filename = line.split(" in ")[-1].strip()
                        conflicting_files.append(filename)

            return True, conflicting_files

        return False, []

    except Exception as e:
        logger.warning(f"Could not check merge conflicts: {e}")
        # On error, proceed without blocking
        return False, []


async def create_pull_request(state: WorkflowState) -> WorkflowState:
    """Create a pull request from the workspace changes.

    This node:
    1. Pushes the feature branch
    2. Creates a PR with Task summaries
    3. Links PR to Jira tickets
    4. Stores PR URL in state

    Args:
        state: Current workflow state.

    Returns:
        Updated state with PR URL.
    """
    ticket_key = state["ticket_key"]
    workspace_path = state.get("workspace_path")
    current_repo = state.get("current_repo", "")
    implemented_tasks = state.get("implemented_tasks", [])

    if not workspace_path:
        logger.error(f"No workspace for PR creation on {ticket_key}")
        return {
            **state,
            "last_error": "Workspace not available",
            "current_node": "create_pr",
        }

    if not implemented_tasks:
        logger.warning(f"No tasks implemented for {ticket_key}")
        return update_state_timestamp({
            **state,
            "current_node": "teardown_workspace",
            "last_error": None,
        })

    logger.info(f"Creating PR for {ticket_key} ({len(implemented_tasks)} tasks)")

    github = GitHubClient()
    jira = JiraClient()

    try:
        # Set up workspace reference
        branch_name = state.get("context", {}).get("branch_name", "")
        workspace = Workspace(
            path=Path(workspace_path),
            repo_name=current_repo,
            branch_name=branch_name,
            ticket_key=ticket_key,
        )
        git = GitOperations(workspace)

        # Check for merge conflicts before pushing
        has_conflicts, conflicting_files = await check_merge_conflicts(git, "main")

        if has_conflicts:
            logger.warning(
                f"Merge conflicts detected for {ticket_key}: {conflicting_files}"
            )

            # Transition to blocked status
            await jira.set_workflow_label(ticket_key, ForgeLabel.BLOCKED)
            await jira.add_comment(
                ticket_key,
                f"**Merge Conflicts Detected**\n\n"
                f"Cannot create PR due to merge conflicts with main branch.\n\n"
                f"**Conflicting files:**\n"
                + "\n".join(f"- `{f}`" for f in conflicting_files)
                + "\n\n*Human intervention required to resolve conflicts.*"
            )

            return update_state_timestamp({
                **state,
                "current_node": "blocked",
                "last_error": f"Merge conflicts: {conflicting_files}",
                "merge_conflicts": conflicting_files,
            })

        # Push branch to remote
        git.push()

        # Build PR title and body
        pr_title = f"[{ticket_key}] {_get_pr_title(state)}"
        pr_body = _build_pr_body(state, implemented_tasks)

        # Parse owner/repo
        owner, repo = current_repo.split("/")

        # Create PR
        pr_data = await github.create_pull_request(
            owner=owner,
            repo=repo,
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base="main",
        )

        pr_url = pr_data.get("html_url", "")
        pr_number = pr_data.get("number")

        # Store PR URL
        pr_urls = state.get("pr_urls", [])
        pr_urls.append(pr_url)

        # Add comment to Jira with PR link
        await jira.add_comment(
            ticket_key,
            f"Pull request created: {pr_url}\n\n"
            f"Implements {len(implemented_tasks)} tasks.",
        )

        logger.info(f"Created PR #{pr_number}: {pr_url}")

        return update_state_timestamp({
            **state,
            "pr_urls": pr_urls,
            "current_pr_url": pr_url,
            "current_pr_number": pr_number,
            "current_node": "teardown_workspace",
            "last_error": None,
        })

    except Exception as e:
        logger.error(f"PR creation failed for {ticket_key}: {e}")
        return {
            **state,
            "last_error": str(e),
            "current_node": "create_pr",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await github.close()
        await jira.close()


def _get_pr_title(state: WorkflowState) -> str:
    """Generate PR title from state.

    Args:
        state: Current workflow state.

    Returns:
        PR title string.
    """
    # Try to get Feature summary from context
    context = state.get("context", {})
    if "feature_summary" in context:
        return context["feature_summary"]

    # Fall back to ticket key
    return f"Implementation for {state.get('ticket_key', 'Unknown')}"


def _build_pr_body(
    state: WorkflowState,
    implemented_tasks: list[str],
) -> str:
    """Build PR body with task list and context.

    Args:
        state: Current workflow state.
        implemented_tasks: List of implemented task keys.

    Returns:
        Formatted PR body.
    """
    ticket_key = state["ticket_key"]
    current_repo = state.get("current_repo", "")

    body_parts = [
        "## Summary",
        "",
        f"This PR implements tasks for [{ticket_key}].",
        "",
        "## Tasks Implemented",
        "",
    ]

    for task_key in implemented_tasks:
        body_parts.append(f"- [x] {task_key}")

    body_parts.extend([
        "",
        "## Repository",
        f"- {current_repo}",
        "",
        "---",
        "*Generated by Forge SDLC Orchestrator*",
    ])

    return "\n".join(body_parts)


async def teardown_and_route(state: WorkflowState) -> WorkflowState:
    """Teardown workspace and route to next repo or completion.

    Args:
        state: Current workflow state.

    Returns:
        Updated state.
    """
    from forge.orchestrator.nodes.workspace_setup import teardown_workspace

    # Teardown current workspace
    state = await teardown_workspace(state)

    # Mark current repo as completed
    repos_completed = state.get("repos_completed", [])
    current_repo = state.get("current_repo")

    if current_repo and current_repo not in repos_completed:
        repos_completed.append(current_repo)

    # Check for remaining repos
    repos_to_process = state.get("repos_to_process", [])
    remaining = [r for r in repos_to_process if r not in repos_completed]

    if remaining:
        # Move to next repo
        return update_state_timestamp({
            **state,
            "repos_completed": repos_completed,
            "current_repo": remaining[0],
            "implemented_tasks": [],
            "current_node": "setup_workspace",
        })

    # All repos done
    return update_state_timestamp({
        **state,
        "repos_completed": repos_completed,
        "current_node": "ci_evaluator",
    })
