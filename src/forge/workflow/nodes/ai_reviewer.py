"""AI code reviewer node for quality, security, and spec alignment."""

import logging

from forge.config import get_settings
from forge.integrations.agents import ForgeAgent
from forge.integrations.github.client import GitHubClient
from forge.prompts import load_prompt
from forge.workflow.feature.state import FeatureState as WorkflowState
from forge.workflow.utils import update_state_timestamp

logger = logging.getLogger(__name__)


async def review_code(state: WorkflowState) -> WorkflowState:
    """Perform AI code review on the PR.

    This node:
    1. Fetches the PR diff
    2. Reviews code against spec and standards
    3. Posts review comments
    4. Routes based on review outcome

    Args:
        state: Current workflow state.

    Returns:
        Updated state with review results.
    """
    ticket_key = state["ticket_key"]
    pr_urls = state.get("pr_urls", [])
    spec_content = state.get("spec_content", "")
    guardrails = state.get("context", {}).get("guardrails", "")

    if not pr_urls:
        logger.info(f"No PRs to review for {ticket_key}")
        return update_state_timestamp({
            **state,
            "ai_review_status": "skipped",
            "current_node": "human_review_gate",
        })

    logger.info(f"Performing AI code review for {ticket_key}")

    settings = get_settings()
    github = GitHubClient()
    agent = ForgeAgent(settings)

    all_approved = True
    review_results = []

    try:
        for pr_url in pr_urls:
            # Parse PR URL
            parts = pr_url.rstrip("/").split("/")
            owner, repo = parts[-4], parts[-3]
            pr_number = int(parts[-1])

            # Get PR details and diff
            pr_data = await github.get_pull_request(owner, repo, pr_number)
            pr_title = pr_data.get("title", "")
            pr_body = pr_data.get("body", "")

            # Build review prompt
            review_prompt = _build_review_prompt(
                pr_title=pr_title,
                pr_body=pr_body,
                spec_content=spec_content,
                guardrails=guardrails,
            )

            # Invoke AI review using Deep Agents
            review_text = await agent.run_task(
                task="review-code",
                prompt=review_prompt,
                context={
                    "ticket_key": ticket_key,
                    "pr_number": pr_number,
                    "owner": owner,
                    "repo": repo,
                },
            )

            # Parse review result
            is_approved = _parse_review_decision(review_text)
            review_results.append({
                "pr_url": pr_url,
                "pr_number": pr_number,
                "approved": is_approved,
                "review_text": review_text,
            })

            if not is_approved:
                all_approved = False

            # Post review as PR comment
            await github.create_issue_comment(
                owner, repo, pr_number,
                f"## AI Code Review\n\n{review_text}"
            )
            logger.info(
                f"Posted AI review for PR #{pr_number}: "
                f"{'approved' if is_approved else 'changes requested'}"
            )

        # Determine next step
        if all_approved:
            return update_state_timestamp({
                **state,
                "ai_review_status": "approved",
                "ai_review_results": review_results,
                "current_node": "human_review_gate",
            })
        else:
            # Route back to implementation for fixes
            return update_state_timestamp({
                **state,
                "ai_review_status": "changes_requested",
                "ai_review_results": review_results,
                "revision_requested": True,
                "current_node": "implement_task",
            })

    except Exception as e:
        logger.error(f"AI review failed for {ticket_key}: {e}")
        return {
            **state,
            "last_error": str(e),
            "current_node": "ai_review",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await github.close()


def _build_review_prompt(
    pr_title: str,
    pr_body: str,
    spec_content: str,
    guardrails: str,
) -> str:
    """Build the review prompt.

    Args:
        pr_title: PR title.
        pr_body: PR description.
        spec_content: Original specification.
        guardrails: Project guardrails.

    Returns:
        Formatted review prompt.
    """
    spec_section = ""
    if spec_content:
        spec_section = f"## Original Specification\n{spec_content[:3000]}\n"

    guardrails_section = ""
    if guardrails:
        guardrails_section = f"## Project Guidelines\n{guardrails[:2000]}\n"

    return load_prompt(
        "review-code",
        pr_title=pr_title,
        pr_body=pr_body or "No description provided.",
        spec_section=spec_section,
        guardrails_section=guardrails_section,
    )


def _parse_review_decision(review_text: str) -> bool:
    """Parse the review decision from AI review text.

    Args:
        review_text: Full review text.

    Returns:
        True if approved, False if changes requested.
    """
    lower = review_text.lower()

    # Check for explicit approval decision
    if "approval decision" in lower:
        if "approve" in lower and "request_changes" not in lower:
            return True
        elif "request_changes" in lower:
            return False

    # Default to approved if no critical/major issues found
    return "critical]" not in lower and "major]" not in lower


def check_spec_alignment(
    code_changes: str,
    spec_content: str,
) -> tuple[bool, list[str]]:
    """Check if code changes align with specification.

    Args:
        code_changes: Code changes to check.
        spec_content: Original specification.

    Returns:
        Tuple of (is_aligned, misalignment_notes).
    """
    # This is a simplified check - in practice, would use more
    # sophisticated analysis or AI
    misalignments = []

    # Extract requirements from spec
    if "Given" in spec_content and "Then" not in code_changes:
        misalignments.append("Spec has Given/When/Then criteria not tested")

    return len(misalignments) == 0, misalignments


def check_constitution_compliance(
    code_changes: str,
    _constitution: str,
) -> tuple[bool, list[str]]:
    """Check if code changes comply with project constitution.

    Args:
        code_changes: Code changes to check.
        constitution: Project constitution.

    Returns:
        Tuple of (is_compliant, violations).
    """
    violations = []

    # Simple keyword checks - would be more sophisticated in practice
    prohibited_patterns = [
        ("eval(", "Direct eval() usage"),
        ("exec(", "Direct exec() usage"),
        ("shell=True", "Shell injection risk"),
    ]

    for pattern, description in prohibited_patterns:
        if pattern in code_changes:
            violations.append(description)

    return len(violations) == 0, violations
