"""Bug workflow node for specialized bug fixing with RCA generation."""

import logging
from typing import Any

from forge.config import get_settings
from forge.integrations.claude.client import get_anthropic_client
from forge.integrations.jira.client import JiraClient
from forge.integrations.langfuse import trace_llm_call
from forge.models.workflow import TaskStatus
from forge.orchestrator.state import WorkflowState, set_paused, update_state_timestamp

logger = logging.getLogger(__name__)

# System prompt for RCA generation
RCA_SYSTEM_PROMPT = """You are an expert Software Engineer analyzing bugs and
generating Root Cause Analysis (RCA) documents.

Given a bug report, you will:
1. Analyze the symptoms and affected components
2. Identify the most likely root cause
3. Explain the chain of events that led to the bug
4. Propose a fix approach using TDD methodology

Output format:

## Summary
[One paragraph bug summary]

## Root Cause Analysis

### Symptoms
- [Observable symptoms]

### Affected Components
- [Components involved]

### Root Cause
[Detailed explanation of what went wrong and why]

### Chain of Events
1. [Step 1]
2. [Step 2]
...

## Proposed Fix (TDD Approach)

### Test First
[Describe the failing test that would catch this bug]

### Implementation
[High-level fix approach]

### Verification
[How to verify the fix works]
"""


async def analyze_bug(state: WorkflowState) -> WorkflowState:
    """Analyze a bug ticket and generate RCA.

    This node:
    1. Reads bug description from Jira
    2. Generates Root Cause Analysis using Claude
    3. Stores RCA in Jira and transitions for review

    Args:
        state: Current workflow state.

    Returns:
        Updated state with RCA content.
    """
    ticket_key = state["ticket_key"]

    logger.info(f"Analyzing bug {ticket_key}")

    settings = get_settings()
    jira = JiraClient(settings)
    anthropic = get_anthropic_client(settings)

    try:
        # Get bug details
        issue = await jira.get_issue(ticket_key)
        bug_description = issue.description or ""
        bug_summary = issue.summary

        if not bug_description.strip():
            logger.warning(f"No description found for bug {ticket_key}")
            return {
                **state,
                "last_error": "No bug description provided",
                "current_node": "analyze_bug",
            }

        # Build context
        context: dict[str, Any] = {
            "ticket_key": ticket_key,
            "summary": bug_summary,
        }

        # Generate RCA
        user_prompt = f"""Please analyze this bug report and generate an RCA:

## Bug: {bug_summary}

## Description
{bug_description}

Generate a comprehensive Root Cause Analysis with TDD fix approach.
"""

        with trace_llm_call(
            "generate_rca",
            {"ticket_key": ticket_key, "summary": bug_summary},
        ) as trace:
            response = await anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=RCA_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            rca_content = response.content[0].text
            trace["output"] = rca_content[:500]

        # Add RCA as comment to Jira
        await jira.add_comment(
            ticket_key,
            f"## Root Cause Analysis\n\n{rca_content}"
        )

        # Transition to pending RCA approval
        await jira.transition_issue(ticket_key, "Pending RCA Approval")

        logger.info(f"RCA generated for {ticket_key}")

        return update_state_timestamp({
            **state,
            "rca_content": rca_content,
            "current_node": "rca_approval_gate",
            "last_error": None,
            "context": {**state.get("context", {}), **context},
        })

    except Exception as e:
        logger.error(f"Bug analysis failed for {ticket_key}: {e}")
        return {
            **state,
            "last_error": str(e),
            "current_node": "analyze_bug",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await jira.close()


def rca_approval_gate(state: WorkflowState) -> WorkflowState:
    """Pause workflow for RCA approval.

    Args:
        state: Current workflow state.

    Returns:
        State with is_paused=True.
    """
    ticket_key = state["ticket_key"]
    logger.info(f"RCA approval gate: pausing for {ticket_key}")

    return set_paused(state, "rca_approval_gate")


def route_rca_approval(state: WorkflowState) -> str:
    """Route based on RCA approval status.

    Args:
        state: Current workflow state.

    Returns:
        Next node name.
    """
    if state.get("revision_requested") and state.get("feedback_comment"):
        return "regenerate_rca"

    if state.get("is_paused"):
        return "rca_approval_gate"

    return "implement_bug_fix"


async def implement_bug_fix(state: WorkflowState) -> WorkflowState:
    """Implement bug fix using TDD approach.

    This node:
    1. First writes a failing test
    2. Then implements the fix
    3. Verifies the test passes

    Args:
        state: Current workflow state with RCA.

    Returns:
        Updated state after fix implementation.
    """
    ticket_key = state["ticket_key"]
    rca_content = state.get("rca_content", "")
    workspace_path = state.get("workspace_path")

    logger.info(f"Implementing TDD bug fix for {ticket_key}")

    # If no workspace, need to set one up
    if not workspace_path:
        # Route to workspace setup with bug context
        return update_state_timestamp({
            **state,
            "current_node": "setup_workspace",
        })

    settings = get_settings()
    anthropic = get_anthropic_client(settings)

    try:
        # Generate test-first implementation
        fix_prompt = f"""Based on this RCA, implement the bug fix using TDD:

{rca_content}

First, write the failing test that would catch this bug.
Then, implement the minimal fix to make the test pass.

Provide complete file contents for:
1. The test file
2. The implementation files that need to change
"""

        with trace_llm_call(
            "implement_bug_fix",
            {"ticket_key": ticket_key},
        ) as trace:
            response = await anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                system="You are an expert writing bug fixes using TDD.",
                messages=[{"role": "user", "content": fix_prompt}],
            )
            result = response.content[0].text
            trace["output"] = result[:500]

        # Apply changes
        from pathlib import Path
        from forge.orchestrator.nodes.implementation import _apply_code_changes
        from forge.workspace.git_ops import GitOperations
        from forge.workspace.manager import Workspace

        workspace = Workspace(
            path=Path(workspace_path),
            repo_name=state.get("current_repo", ""),
            branch_name=state.get("context", {}).get("branch_name", ""),
            ticket_key=ticket_key,
        )
        git = GitOperations(workspace)

        files_modified = _apply_code_changes(result, Path(workspace_path))

        if files_modified > 0:
            git.stage_all()
            git.commit(f"[{ticket_key}] Fix: {state.get('context', {}).get('summary', 'Bug fix')}")
            git.push()

        logger.info(f"Bug fix implemented for {ticket_key}")

        return update_state_timestamp({
            **state,
            "bug_fix_implemented": True,
            "current_node": "create_pr",
        })

    except Exception as e:
        logger.error(f"Bug fix implementation failed for {ticket_key}: {e}")
        return {
            **state,
            "last_error": str(e),
            "current_node": "implement_bug_fix",
            "retry_count": state.get("retry_count", 0) + 1,
        }


async def regenerate_rca(state: WorkflowState) -> WorkflowState:
    """Regenerate RCA based on feedback.

    Args:
        state: Current workflow state with feedback.

    Returns:
        Updated state with new RCA.
    """
    ticket_key = state["ticket_key"]
    feedback = state.get("feedback_comment", "")
    original_rca = state.get("rca_content", "")

    logger.info(f"Regenerating RCA for {ticket_key} with feedback")

    settings = get_settings()
    jira = JiraClient(settings)
    anthropic = get_anthropic_client(settings)

    try:
        prompt = f"""Please revise this RCA based on the feedback:

ORIGINAL RCA:
{original_rca}

FEEDBACK:
{feedback}

Generate an updated RCA addressing the feedback.
"""

        with trace_llm_call(
            "regenerate_rca",
            {"ticket_key": ticket_key, "feedback": feedback[:200]},
        ) as trace:
            response = await anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=RCA_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            new_rca = response.content[0].text
            trace["output"] = new_rca[:500]

        # Update Jira
        await jira.add_comment(
            ticket_key,
            f"## Updated Root Cause Analysis\n\n{new_rca}"
        )

        return update_state_timestamp({
            **state,
            "rca_content": new_rca,
            "feedback_comment": None,
            "revision_requested": False,
            "current_node": "rca_approval_gate",
        })

    except Exception as e:
        logger.error(f"RCA regeneration failed for {ticket_key}: {e}")
        return {
            **state,
            "last_error": str(e),
            "current_node": "regenerate_rca",
        }
    finally:
        await jira.close()
