"""PRD approval gate for human-in-the-loop review."""

import logging
from typing import Literal

from forge.models.workflow import FeatureStatus
from forge.orchestrator.state import WorkflowState, set_paused

logger = logging.getLogger(__name__)


def prd_approval_gate(state: WorkflowState) -> WorkflowState:
    """Pause workflow for PM to review and approve the PRD.

    This gate pauses the workflow until a human approves or rejects
    the generated PRD. The workflow resumes when:
    - Ticket transitions to "Approved: PRD" -> continue to spec generation
    - Ticket receives rejection comment -> regenerate PRD with feedback

    Args:
        state: Current workflow state.

    Returns:
        State with is_paused=True.
    """
    ticket_key = state["ticket_key"]
    logger.info(f"PRD approval gate: pausing workflow for {ticket_key}")

    return set_paused(state, "prd_approval_gate")


def route_prd_approval(state: WorkflowState) -> Literal["generate_spec", "regenerate_prd", "prd_approval_gate"]:
    """Route based on PRD approval status.

    This routing function determines the next node after PRD approval gate:
    - If PRD is approved (status changed) -> proceed to spec generation
    - If feedback provided (revision requested) -> regenerate PRD
    - Otherwise -> stay at gate (remain paused)

    Args:
        state: Current workflow state.

    Returns:
        Next node name.
    """
    # Check if revision was requested via comment
    if state.get("revision_requested") and state.get("feedback_comment"):
        logger.info(f"PRD revision requested for {state['ticket_key']}")
        return "regenerate_prd"

    # Check if we should stay paused
    if state.get("is_paused"):
        return "prd_approval_gate"

    # PRD was approved, proceed to spec generation
    logger.info(f"PRD approved for {state['ticket_key']}, proceeding to spec generation")
    return "generate_spec"


def check_prd_approval_status(
    state: WorkflowState,
    current_status: str,
) -> tuple[bool, bool, str | None]:
    """Check if PRD approval status indicates approval or rejection.

    Args:
        state: Current workflow state.
        current_status: Current Jira ticket status.

    Returns:
        Tuple of (is_approved, is_rejected, feedback_comment).
    """
    approved_status = FeatureStatus.DRAFTING_SPEC.value.lower()
    pending_status = FeatureStatus.PENDING_PRD_APPROVAL.value.lower()
    current_lower = current_status.lower()

    # Approved if status moved past pending
    is_approved = current_lower == approved_status

    # Rejected if still pending but has revision request
    is_rejected = (
        current_lower == pending_status
        and state.get("revision_requested", False)
    )

    feedback = state.get("feedback_comment") if is_rejected else None

    return is_approved, is_rejected, feedback
