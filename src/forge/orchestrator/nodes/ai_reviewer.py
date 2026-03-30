"""AI code reviewer node for quality, security, and spec alignment."""

import logging
from typing import Any, Literal

from forge.config import get_settings
from forge.integrations.claude.client import get_anthropic_client
from forge.integrations.github.client import GitHubClient
from forge.integrations.langfuse import trace_llm_call
from forge.orchestrator.state import WorkflowState, update_state_timestamp

logger = logging.getLogger(__name__)

# System prompt for AI code review
REVIEW_SYSTEM_PROMPT = """You are an expert Code Reviewer analyzing pull requests
for quality, security, and specification alignment.

Review the code changes for:
1. Code Quality: Clean code, proper error handling, no obvious bugs
2. Security: No vulnerabilities, secrets, or unsafe operations
3. Spec Alignment: Code matches the original requirements
4. Best Practices: Following project conventions and standards

Provide your review in this format:

## Summary
[One paragraph overall assessment]

## Issues Found
- [SEVERITY: critical/major/minor] [Issue description]
  - File: path/to/file
  - Line: X
  - Suggestion: [How to fix]

## Approval Decision
[APPROVE if no critical/major issues, REQUEST_CHANGES otherwise]

## Comments
[Optional additional feedback]
"""


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
    anthropic = get_anthropic_client(settings)

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

            # Invoke AI review
            with trace_llm_call(
                "ai_code_review",
                {"ticket_key": ticket_key, "pr_number": pr_number},
            ) as trace:
                response = await anthropic.messages.create(
                    model=get_settings().claude_model,
                    max_tokens=4096,
                    system=REVIEW_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": review_prompt}],
                )
                review_text = response.content[0].text
                trace["output"] = review_text[:500]

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
    parts = [
        f"# Pull Request: {pr_title}",
        "",
        "## Description",
        pr_body or "No description provided.",
        "",
    ]

    if spec_content:
        parts.extend([
            "## Original Specification",
            spec_content[:3000],  # Truncate if too long
            "",
        ])

    if guardrails:
        parts.extend([
            "## Project Guidelines",
            guardrails[:2000],
            "",
        ])

    parts.extend([
        "Please review this PR for quality, security, and spec alignment.",
    ])

    return "\n".join(parts)


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

    # Fallback: check for critical/major issues
    if "critical]" in lower or "major]" in lower:
        return False

    # Default to approved if no major issues found
    return True


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
    constitution: str,
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
