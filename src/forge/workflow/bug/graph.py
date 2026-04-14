"""Bug workflow graph construction.

This module builds the LangGraph StateGraph for the Bug workflow.
"""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from forge.workflow.bug.state import BugState
from forge.workflow.nodes import (
    analyze_bug,
    attempt_ci_fix,
    create_pull_request,
    escalate_to_blocked,
    evaluate_ci_status,
    human_review_gate,
    implement_bug_fix,
    rca_approval_gate,
    regenerate_rca,
    route_human_review,
    route_rca_approval,
    setup_workspace,
    teardown_and_route,
)
from forge.workflow.nodes.ai_reviewer import review_code

logger = logging.getLogger(__name__)


def route_entry(state: BugState) -> str:
    """Route workflow based on current progress for resume/retry.

    If the workflow is being resumed (current_node is set), route to the
    appropriate node based on where the workflow was.

    Args:
        state: Current workflow state.

    Returns:
        Next node name based on current progress.
    """
    current_node = state.get("current_node", "")

    # If we have a current_node from a previous run, route based on progress
    if current_node and current_node not in ("entry", "route_entry", "__end__", ""):
        logger.info(f"Resuming bug workflow at node: {current_node}")

        # Map current_node to the appropriate starting point
        # RCA stage
        if current_node in ("analyze_bug", "regenerate_rca"):
            return "analyze_bug"
        elif current_node == "rca_approval_gate":
            return "rca_approval_gate"
        # Fix implementation stage
        elif current_node == "setup_workspace":
            return "setup_workspace"
        elif current_node == "implement_bug_fix":
            return "implement_bug_fix"
        elif current_node == "create_pr":
            return "create_pr"
        elif current_node == "teardown_workspace":
            return "teardown_workspace"
        # CI stage
        elif current_node in ("ci_evaluator", "attempt_ci_fix"):
            return "ci_evaluator"
        # Review stage
        elif current_node in ("ai_review", "human_review_gate"):
            return "ai_review"
        # Blocked state
        elif current_node == "escalate_blocked":
            return "escalate_blocked"
        # Terminal states
        elif current_node == "complete":
            logger.info(f"Workflow at terminal state '{current_node}', returning END")
            return END
        else:
            logger.warning(f"Unrecognized current_node '{current_node}', starting from beginning")

    # Start at bug analysis for new workflows
    return "analyze_bug"


def _route_after_workspace_setup(
    state: BugState,
) -> Literal["implement_bug_fix", "escalate_blocked"]:
    """Route based on workspace setup success."""
    workspace_path = state.get("workspace_path")
    last_error = state.get("last_error")

    if workspace_path and not last_error:
        return "implement_bug_fix"

    logger.error(f"Workspace setup failed: {last_error}")
    return "escalate_blocked"


def _route_after_implementation(
    state: BugState,
) -> Literal["create_pr", "escalate_blocked"]:
    """Route based on bug fix implementation status.

    Checks for:
    - Implementation succeeded -> create_pr
    - Retry limit exceeded -> escalate_blocked
    """
    # Check retry limit to prevent infinite loops
    retry_count = state.get("retry_count", 0)
    max_retries = 3  # Max retries per implementation
    last_error = state.get("last_error")

    if last_error and retry_count >= max_retries:
        logger.error(f"Implementation retry limit ({max_retries}) exceeded: {last_error}")
        return "escalate_blocked"

    bug_fix_implemented = state.get("bug_fix_implemented", False)
    if bug_fix_implemented:
        return "create_pr"

    return "escalate_blocked"


def _route_after_pr_creation(
    state: BugState,
) -> Literal["teardown_workspace", "escalate_blocked"]:
    """Route after PR creation attempt.

    On success: proceed to teardown workspace
    On failure: escalate to blocked status

    Args:
        state: Current workflow state.

    Returns:
        Next node name.
    """
    last_error = state.get("last_error")
    pr_urls = state.get("pr_urls", [])

    # If there's an error and no PR was created, escalate
    if last_error and not pr_urls:
        return "escalate_blocked"

    # Success - proceed to teardown
    return "teardown_workspace"


def _route_after_teardown(_state: BugState) -> Literal["ci_evaluator"]:
    """Route after workspace teardown.

    For bug workflow, we always proceed to CI evaluation after teardown.
    """
    return "ci_evaluator"


def _route_ci_evaluation(
    state: BugState,
) -> Literal["ai_review", "attempt_ci_fix", "escalate_blocked", "__end__"]:
    """Route based on CI evaluation results."""
    ci_status = state.get("ci_status", "")

    routes = {
        "passed": "ai_review",
        "fixing": "attempt_ci_fix",
        "pending": "__end__",  # Pause workflow until CI webhook
    }
    return routes.get(ci_status, "escalate_blocked")


def _route_ai_review(state: BugState) -> Literal["human_review_gate", "implement_bug_fix"]:
    """Route based on AI review results."""
    ai_status = state.get("ai_review_status", "")

    if ai_status == "changes_requested":
        return "implement_bug_fix"
    return "human_review_gate"


def build_bug_graph() -> StateGraph:
    """Create the Bug workflow graph.

    The graph implements the following flow:
    1. Start -> route_entry
    2. analyze_bug -> rca_approval_gate (pause)
    3. On RCA approval: rca_approval_gate -> setup_workspace
    4. On RCA rejection: rca_approval_gate -> regenerate_rca -> rca_approval_gate
    5. setup_workspace -> implement_bug_fix
    6. implement_bug_fix -> create_pr
    7. create_pr -> teardown_workspace
    8. teardown_workspace -> ci_evaluator
    9. ci_evaluator -> ai_review (or attempt_ci_fix)
    10. ai_review -> human_review_gate
    11. human_review_gate -> END (or back to implement_bug_fix for changes)

    Returns:
        Configured StateGraph ready for compilation.
    """
    # Create graph with bug state schema
    graph = StateGraph(BugState)

    # Add entry point that routes by current progress
    graph.add_node("route_entry", lambda state: state)

    # RCA nodes
    graph.add_node("analyze_bug", analyze_bug)
    graph.add_node("rca_approval_gate", rca_approval_gate)
    graph.add_node("regenerate_rca", regenerate_rca)

    # Implementation nodes
    graph.add_node("setup_workspace", setup_workspace)
    graph.add_node("implement_bug_fix", implement_bug_fix)
    graph.add_node("create_pr", create_pull_request)
    graph.add_node("teardown_workspace", teardown_and_route)

    # CI/CD nodes
    graph.add_node("ci_evaluator", evaluate_ci_status)
    graph.add_node("attempt_ci_fix", attempt_ci_fix)
    graph.add_node("escalate_blocked", escalate_to_blocked)

    # Review nodes
    graph.add_node("ai_review", review_code)
    graph.add_node("human_review_gate", human_review_gate)

    # Set entry point
    graph.set_entry_point("route_entry")

    # Route from entry based on resume state
    graph.add_conditional_edges(
        "route_entry",
        route_entry,
        {
            "analyze_bug": "analyze_bug",
            "rca_approval_gate": "rca_approval_gate",
            "setup_workspace": "setup_workspace",
            "implement_bug_fix": "implement_bug_fix",
            "create_pr": "create_pr",
            "teardown_workspace": "teardown_workspace",
            "ci_evaluator": "ci_evaluator",
            "ai_review": "ai_review",
            "escalate_blocked": "escalate_blocked",
            END: END,
        },
    )

    # RCA flow
    graph.add_edge("analyze_bug", "rca_approval_gate")
    graph.add_conditional_edges(
        "rca_approval_gate",
        route_rca_approval,
        {
            "implement_bug_fix": "setup_workspace",  # RCA approved, setup workspace
            "regenerate_rca": "regenerate_rca",
            END: END,  # Pause workflow until approval webhook
        },
    )
    graph.add_edge("regenerate_rca", "rca_approval_gate")

    # Implementation flow
    graph.add_conditional_edges(
        "setup_workspace",
        _route_after_workspace_setup,
        {
            "implement_bug_fix": "implement_bug_fix",
            "escalate_blocked": "escalate_blocked",
        },
    )
    graph.add_conditional_edges(
        "implement_bug_fix",
        _route_after_implementation,
        {
            "create_pr": "create_pr",
            "escalate_blocked": "escalate_blocked",
        },
    )
    graph.add_conditional_edges(
        "create_pr",
        _route_after_pr_creation,
        {
            "teardown_workspace": "teardown_workspace",
            "escalate_blocked": "escalate_blocked",
        },
    )
    graph.add_conditional_edges(
        "teardown_workspace",
        _route_after_teardown,
        {
            "ci_evaluator": "ci_evaluator",
        },
    )

    # CI/CD flow
    graph.add_conditional_edges(
        "ci_evaluator",
        _route_ci_evaluation,
        {
            "ai_review": "ai_review",
            "attempt_ci_fix": "attempt_ci_fix",
            "escalate_blocked": "escalate_blocked",
            END: END,  # Pause workflow until CI webhook
        },
    )
    graph.add_edge("attempt_ci_fix", "ci_evaluator")
    graph.add_edge("escalate_blocked", END)

    # Review flow
    graph.add_conditional_edges(
        "ai_review",
        _route_ai_review,
        {
            "human_review_gate": "human_review_gate",
            "implement_bug_fix": "implement_bug_fix",
        },
    )
    graph.add_conditional_edges(
        "human_review_gate",
        route_human_review,
        {
            "implement_bug_fix": "implement_bug_fix",
            END: END,  # Complete or paused for review
        },
    )

    return graph
