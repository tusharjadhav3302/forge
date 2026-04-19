"""CI/CD evaluator node for monitoring and responding to CI results."""

import logging
from typing import Any

from forge.config import get_settings
from forge.integrations.github.client import GitHubClient
from forge.integrations.jira.client import JiraClient
from forge.models.workflow import ForgeLabel
from forge.prompts import load_prompt
from forge.workflow.feature.state import FeatureState as WorkflowState
from forge.workflow.utils import update_state_timestamp

logger = logging.getLogger(__name__)


async def evaluate_ci_status(state: WorkflowState) -> WorkflowState:
    """Evaluate CI status for the current PR.

    This node:
    1. Checks CI status from GitHub
    2. Routes based on pass/fail
    3. On failure, attempts autonomous fix if retries remain

    Args:
        state: Current workflow state.

    Returns:
        Updated state with ci_status.
    """
    ticket_key = state["ticket_key"]
    pr_urls = state.get("pr_urls", [])
    ci_fix_attempts = state.get("ci_fix_attempts", 0)
    settings = get_settings()

    if not pr_urls:
        logger.info(f"No PRs to evaluate for {ticket_key}")
        return update_state_timestamp({
            **state,
            "ci_status": "no_prs",
            "current_node": "complete",
        })

    logger.info(f"Evaluating CI status for {ticket_key}")

    github = GitHubClient()

    try:
        # Check each PR's CI status
        all_passed = True
        failed_checks = []

        for pr_url in pr_urls:
            # Parse PR URL to get owner/repo/number
            parts = pr_url.rstrip("/").split("/")
            owner, repo = parts[-4], parts[-3]
            pr_number = int(parts[-1])

            # Get PR details for head SHA
            pr_data = await github.get_pull_request(owner, repo, pr_number)
            head_sha = pr_data.get("head", {}).get("sha", "")

            if not head_sha:
                continue

            # Get check runs for the commit
            check_runs = await github.get_check_runs(owner, repo, head_sha)

            # If no check runs exist yet, CI is still pending
            if not check_runs:
                logger.info(f"No CI checks registered yet for {pr_url}, waiting for webhook")
                return update_state_timestamp({
                    **state,
                    "ci_status": "pending",
                    "current_node": "ci_evaluator",  # Stay here, wait for webhook
                })

            for check in check_runs:
                status = check.get("status")
                conclusion = check.get("conclusion")

                if status != "completed":
                    # Still running
                    all_passed = False
                    logger.info(f"CI still running for {pr_url}")
                elif conclusion not in ("success", "skipped", "neutral"):
                    # Failed
                    all_passed = False
                    failed_checks.append({
                        "pr_url": pr_url,
                        "name": check.get("name"),
                        "conclusion": conclusion,
                        "output": check.get("output", {}),
                        "log_url": check.get("html_url", ""),
                    })

        if all_passed:
            logger.info(f"All CI checks passed for {ticket_key}")
            return update_state_timestamp({
                **state,
                "ci_status": "passed",
                "current_node": "ai_review",
                "last_error": None,
            })

        # CI failed - check if we can retry
        max_retries = settings.ci_fix_max_retries
        if ci_fix_attempts >= max_retries:
            logger.warning(
                f"CI fix retry limit ({max_retries}) reached for {ticket_key}"
            )
            return update_state_timestamp({
                **state,
                "ci_status": "failed",
                "ci_failed_checks": failed_checks,
                "current_node": "escalate_blocked",
                "last_error": "CI fix retry limit reached",
            })

        # Attempt autonomous fix
        logger.info(
            f"CI failed for {ticket_key}, attempt "
            f"{ci_fix_attempts + 1}/{max_retries}"
        )
        return update_state_timestamp({
            **state,
            "ci_status": "fixing",
            "ci_failed_checks": failed_checks,
            "ci_fix_attempts": ci_fix_attempts + 1,
            "current_node": "attempt_ci_fix",
        })

    except Exception as e:
        logger.error(f"CI evaluation failed for {ticket_key}: {e}")
        from forge.workflow.nodes.error_handler import notify_error
        await notify_error(state, str(e), "ci_evaluator")
        return {
            **state,
            "last_error": str(e),
            "current_node": "ci_evaluator",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await github.close()


async def attempt_ci_fix(state: WorkflowState) -> WorkflowState:
    """Attempt to autonomously fix CI failures.

    This node:
    1. Extracts error information from failed checks
    2. Invokes Claude to generate a fix
    3. Applies the fix and pushes
    4. Routes back to CI evaluation

    Args:
        state: Current workflow state with ci_failed_checks.

    Returns:
        Updated state after fix attempt.
    """
    ticket_key = state["ticket_key"]
    failed_checks = state.get("ci_failed_checks", [])
    workspace_path = state.get("workspace_path")

    if not failed_checks:
        return update_state_timestamp({
            **state,
            "current_node": "ci_evaluator",
        })

    logger.info(f"Attempting CI fix for {ticket_key}")

    settings = get_settings()
    fork_owner = state.get("fork_owner", "")
    fork_repo = state.get("fork_repo", "")
    attempt = state.get("ci_fix_attempts", 1)

    try:
        from pathlib import Path

        from forge.integrations.agents import ForgeAgent
        from forge.sandbox import ContainerRunner
        from forge.workspace.git_ops import GitOperations
        from forge.workspace.manager import Workspace, WorkspaceManager

        # If workspace was lost (e.g. restart), recreate it by cloning upstream,
        # adding the fork as a remote, and checking out the PR branch.
        if not workspace_path:
            logger.info(
                f"No workspace for {ticket_key} — recreating from fork branch"
            )
            branch_name = state.get("context", {}).get("branch_name", "")
            current_repo = state.get("current_repo", "")

            if not branch_name or not current_repo or not fork_owner or not fork_repo:
                logger.error(
                    f"Cannot recreate workspace for {ticket_key}: missing "
                    f"branch_name={branch_name!r}, current_repo={current_repo!r}, "
                    f"fork_owner={fork_owner!r}"
                )
                return update_state_timestamp({
                    **state,
                    "last_error": "Cannot recreate workspace: missing branch/repo info",
                    "current_node": "escalate_blocked",
                })

            manager = WorkspaceManager()
            workspace_obj = manager.create_workspace(
                repo_name=current_repo, ticket_key=ticket_key
            )
            git_tmp = GitOperations(workspace_obj)
            git_tmp.clone()
            git_tmp.add_fork_remote(fork_owner, fork_repo)
            git_tmp.checkout_branch(branch_name, remote="fork")

            workspace_path = str(workspace_obj.path)
            logger.info(f"Workspace recreated at {workspace_path}")

            # Persist workspace_path so teardown can clean it up later
            state = {**state, "workspace_path": workspace_path}

    except Exception as _setup_err:
        logger.error(f"Workspace recreation failed for {ticket_key}: {_setup_err}")
        from forge.workflow.nodes.error_handler import notify_error
        await notify_error(state, str(_setup_err), "attempt_ci_fix")
        return {
            **state,
            "last_error": str(_setup_err),
            "current_node": "escalate_blocked",
        }

    try:
        # ── Phase 1: Analysis ────────────────────────────────────────────────
        # ForgeAgent with MCP access fetches the Prow logs and produces a
        # structured fix plan. No workspace access needed here.
        logger.info(f"Phase 1: Analyzing CI failures for {ticket_key} (attempt {attempt})")
        error_info = _collect_error_info(failed_checks)
        analysis_prompt = load_prompt("analyze-ci", error_info=error_info)

        agent = ForgeAgent(settings)
        try:
            fix_plan = await agent.run_task(
                task="analyze-ci",
                prompt=analysis_prompt,
                context={"ticket_key": ticket_key, "attempt": attempt},
            )
        finally:
            await agent.close()

        logger.info(f"Phase 1 complete: fix plan generated ({len(fix_plan)} chars)")

        # ── Phase 2: Fix ─────────────────────────────────────────────────────
        # Container with full workspace access applies the fix plan mechanically.
        logger.info(f"Phase 2: Applying fixes for {ticket_key}")
        fix_prompt = load_prompt("fix-ci", fix_plan=fix_plan)

        runner = ContainerRunner(settings)
        await runner.run(
            workspace_path=Path(workspace_path),
            task_summary=f"Apply CI fix plan (attempt {attempt})",
            task_description=fix_prompt,
            ticket_key=ticket_key,
            task_key=f"{ticket_key}-ci-fix",
            repo_name=state.get("current_repo", ""),
        )

        workspace = Workspace(
            path=Path(workspace_path),
            repo_name=state.get("current_repo", ""),
            branch_name=state.get("context", {}).get("branch_name", ""),
            ticket_key=ticket_key,
        )
        git = GitOperations(workspace)

        if git.has_uncommitted_changes():
            git.stage_all()
            git.commit(f"[{ticket_key}] fix: address CI failures (attempt {attempt})")

            if fork_owner and fork_repo:
                git.add_fork_remote(fork_owner, fork_repo)
                git.push_to_fork(force=False)
            else:
                logger.warning("Fork info not in state — pushing to origin instead")
                git.push(force=False)

            logger.info(f"CI fix applied and pushed for {ticket_key}")
        else:
            logger.warning(f"Container made no changes for {ticket_key} (attempt {attempt})")

        return update_state_timestamp({
            **state,
            "current_node": "wait_for_ci_gate",
            "last_error": None,
        })

    except Exception as e:
        logger.error(f"CI fix failed for {ticket_key}: {e}")
        from forge.workflow.nodes.error_handler import notify_error
        await notify_error(state, str(e), "attempt_ci_fix")
        return {
            **state,
            "last_error": str(e),
            "current_node": "escalate_blocked",
        }


async def wait_for_ci_gate(state: WorkflowState) -> WorkflowState:
    """Pause the workflow until a GitHub CI webhook arrives.

    Inserted after PR creation and after each CI fix push. The workflow
    resumes when GitHub sends a check_run or check_suite webhook, at which
    point ci_evaluator re-checks the actual CI results without any
    polling delay.

    Args:
        state: Current workflow state.

    Returns:
        Updated state with is_paused=True.
    """
    ticket_key = state["ticket_key"]
    ci_fix_attempts = state.get("ci_fix_attempts", 0)

    if ci_fix_attempts > 0:
        logger.info(
            f"Pausing {ticket_key} after CI fix attempt {ci_fix_attempts}, "
            "waiting for GitHub CI webhook"
        )
    else:
        logger.info(
            f"Pausing {ticket_key} after PR creation, waiting for GitHub CI webhook"
        )

    return update_state_timestamp({
        **state,
        "is_paused": True,
        "current_node": "wait_for_ci_gate",
    })


async def escalate_to_blocked(state: WorkflowState) -> WorkflowState:
    """Escalate ticket to Blocked status after workflow failure.

    This handles various failure scenarios:
    - CI fix exhaustion
    - Workspace setup failures (invalid repo, clone failures)
    - Other workflow errors

    Args:
        state: Current workflow state.

    Returns:
        Updated state with ticket transitioned to Blocked.
    """
    ticket_key = state["ticket_key"]
    ci_fix_attempts = state.get("ci_fix_attempts", 0)
    failed_checks = state.get("ci_failed_checks", [])
    last_error = state.get("last_error", "")
    current_node = state.get("current_node", "")

    logger.info(f"Escalating {ticket_key} to Blocked status")

    jira = JiraClient()

    try:
        # Build escalation error message based on failure type
        if failed_checks:
            # CI failure scenario
            check_names = [c.get("name", "Unknown") for c in failed_checks]
            error_msg = (
                f"CI fixes exhausted after {ci_fix_attempts} attempts. "
                f"Failed checks: {', '.join(check_names)}. "
                "Manual intervention required."
            )
        elif last_error and ("repository" in last_error.lower() or "workspace" in last_error.lower()):
            # Workspace/repository setup failure
            error_msg = (
                f"Repository configuration error: {last_error}. "
                "Ensure tasks have valid repo assignments (owner/repo format)."
            )
        else:
            # Generic failure
            error_msg = f"{last_error}. Manual intervention required."

        # Post error with @mentions for reporter and assignee
        from forge.workflow.nodes.error_handler import notify_error
        await notify_error(state, error_msg, f"escalate_blocked ({current_node})")
        # Set blocked label instead of transitioning to custom status
        await jira.set_workflow_label(ticket_key, ForgeLabel.BLOCKED)

        logger.info(f"Ticket {ticket_key} escalated to Blocked")

        return update_state_timestamp({
            **state,
            "ci_status": "blocked",
            "current_node": "complete",
            "generation_context": {},  # Clear - no longer needed
            "qa_history": [],  # Clear - workflow ending
        })

    except Exception as e:
        logger.error(f"Escalation failed for {ticket_key}: {e}")
        return {
            **state,
            "last_error": str(e),
        }
    finally:
        await jira.close()


def _collect_error_info(failed_checks: list[dict[str, Any]]) -> str:
    """Collect and format error information from failed checks.

    Args:
        failed_checks: List of failed check data.

    Returns:
        Formatted error information.
    """
    parts = []

    for check in failed_checks:
        parts.append(f"## {check.get('name', 'Unknown Check')}")
        parts.append(f"Result: {check.get('conclusion', 'failed')}")

        log_url = check.get("log_url", "")
        if log_url:
            parts.append(f"Log URL: {log_url}")

        output = check.get("output", {})
        if output:
            title = output.get("title", "")
            summary = output.get("summary", "")
            text = output.get("text", "")

            if title:
                parts.append(f"Title: {title}")
            if summary:
                parts.append(f"Summary: {summary}")
            if text:
                parts.append(f"Details:\n{text[:2000]}")

        parts.append("")

    return "\n".join(parts)


def _build_fix_prompt(error_info: str) -> str:
    """Build the prompt for generating a CI fix.

    Args:
        error_info: Formatted error information.

    Returns:
        Prompt for Claude.
    """
    return load_prompt("fix-ci", error_info=error_info)
