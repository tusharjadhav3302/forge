"""Specification approval gate for human-in-the-loop review."""

import logging
from typing import Literal

from langgraph.graph import END

from forge.models.workflow import FeatureStatus
from forge.orchestrator.state import WorkflowState, set_paused

logger = logging.getLogger(__name__)


def spec_approval_gate(state: WorkflowState) -> WorkflowState:
    """Pause workflow for PM to review and approve the specification.

    This gate pauses the workflow until a human approves or rejects
    the generated specification. The workflow resumes when:
    - Ticket transitions to "Approved: Spec" -> continue to epic decomposition
    - Ticket receives rejection comment -> regenerate spec with feedback

    Args:
        state: Current workflow state.

    Returns:
        State with is_paused=True.
    """
    ticket_key = state["ticket_key"]
    logger.info(f"Spec approval gate: pausing workflow for {ticket_key}")

    return set_paused(state, "spec_approval_gate")


def route_spec_approval(state: WorkflowState) -> str:
    """Route based on spec approval status.

    Args:
        state: Current workflow state.

    Returns:
        Next node name or END.
    """
    # Check if revision was requested
    if state.get("revision_requested") and state.get("feedback_comment"):
        logger.info(f"Spec revision requested for {state['ticket_key']}")
        return "regenerate_spec"

    # Check if still paused - END and wait for approval webhook
    if state.get("is_paused"):
        logger.info(f"Spec approval gate: workflow paused for {state['ticket_key']}, waiting for approval webhook")
        return END

    # Spec approved, proceed to epic decomposition
    logger.info(f"Spec approved for {state['ticket_key']}, proceeding to epic decomposition")
    return "decompose_epics"


def check_spec_approval_status(
    state: WorkflowState,
    current_status: str,
) -> tuple[bool, bool, str | None]:
    """Check if spec approval status indicates approval or rejection.

    Args:
        state: Current workflow state.
        current_status: Current Jira ticket status.

    Returns:
        Tuple of (is_approved, is_rejected, feedback_comment).
    """
    approved_status = FeatureStatus.PLANNING.value.lower()
    pending_status = FeatureStatus.PENDING_SPEC_APPROVAL.value.lower()
    current_lower = current_status.lower()

    is_approved = current_lower == approved_status

    is_rejected = (
        current_lower == pending_status
        and state.get("revision_requested", False)
    )

    feedback = state.get("feedback_comment") if is_rejected else None

    return is_approved, is_rejected, feedback
