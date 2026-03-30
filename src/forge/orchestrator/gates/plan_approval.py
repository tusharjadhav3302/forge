"""Plan approval gate for human-in-the-loop review of Epic decomposition."""

import logging
from typing import Literal

from forge.models.workflow import FeatureStatus
from forge.orchestrator.state import WorkflowState, set_paused

logger = logging.getLogger(__name__)


def plan_approval_gate(state: WorkflowState) -> WorkflowState:
    """Pause workflow for Tech Lead to review Epic decomposition and plans.

    This gate pauses the workflow until a human approves or rejects
    the generated Epics and their implementation plans. The workflow resumes when:
    - All Epics approved -> proceed to task generation
    - Feature-level rejection -> delete all Epics and regenerate
    - Epic-level rejection -> update single Epic plan

    Args:
        state: Current workflow state.

    Returns:
        State with is_paused=True.
    """
    ticket_key = state["ticket_key"]
    epic_count = len(state.get("epic_keys", []))
    logger.info(f"Plan approval gate: pausing workflow for {ticket_key} ({epic_count} Epics)")

    return set_paused(state, "plan_approval_gate")


def route_plan_approval(
    state: WorkflowState,
) -> Literal["generate_tasks", "regenerate_all_epics", "update_single_epic", "plan_approval_gate"]:
    """Route based on plan approval status.

    Args:
        state: Current workflow state.

    Returns:
        Next node name.
    """
    # Check if Feature-level revision requested (regenerate all)
    if state.get("revision_requested"):
        feedback = state.get("feedback_comment", "")
        current_epic = state.get("current_epic_key")

        if current_epic:
            # Single Epic update
            logger.info(f"Single Epic revision requested for {current_epic}")
            return "update_single_epic"
        elif feedback:
            # Feature-level regeneration
            logger.info(f"Full Epic regeneration requested for {state['ticket_key']}")
            return "regenerate_all_epics"

    # Check if still paused
    if state.get("is_paused"):
        return "plan_approval_gate"

    # All Epics approved, proceed to task generation
    logger.info(f"Epics approved for {state['ticket_key']}, proceeding to task generation")
    return "generate_tasks"


def check_plan_approval_status(
    state: WorkflowState,
    current_status: str,
) -> tuple[bool, bool, str | None, str | None]:
    """Check if plan approval status indicates approval or rejection.

    Args:
        state: Current workflow state.
        current_status: Current Jira Feature status.

    Returns:
        Tuple of (is_approved, is_rejected, feedback_comment, target_epic_key).
    """
    approved_status = FeatureStatus.EXECUTING.value.lower()
    pending_status = FeatureStatus.PENDING_PLAN_APPROVAL.value.lower()
    current_lower = current_status.lower()

    is_approved = current_lower == approved_status

    is_rejected = (
        current_lower == pending_status
        and state.get("revision_requested", False)
    )

    feedback = state.get("feedback_comment") if is_rejected else None
    target_epic = state.get("current_epic_key") if is_rejected else None

    return is_approved, is_rejected, feedback, target_epic
