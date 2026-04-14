"""Workflow state definitions - re-exported from workflow module for backward compatibility."""

from forge.models.workflow import TicketType

# Re-export everything from workflow.base for backward compatibility
from forge.workflow.base import BaseState

# Re-export FeatureState as WorkflowState for backward compatibility
from forge.workflow.feature.state import FeatureState as WorkflowState

# Re-export utility functions from workflow.utils for backward compatibility
from forge.workflow.utils import (
    resume_state,
    set_error,
    set_paused,
    update_state_timestamp,
)


def create_initial_state(
    thread_id: str,
    ticket_key: str,
    ticket_type: TicketType,
) -> WorkflowState:
    """Create initial workflow state for a new ticket.

    DEPRECATED: Use workflow-specific state creation functions instead.
    For backward compatibility, this routes to the appropriate workflow state creator.

    Args:
        thread_id: Unique workflow thread identifier.
        ticket_key: Jira ticket key.
        ticket_type: Type of ticket (Feature, Epic, Task, Bug).

    Returns:
        Initialized WorkflowState (FeatureState or BugState).
    """
    if ticket_type == TicketType.BUG:
        from forge.workflow.bug.state import create_initial_bug_state
        return create_initial_bug_state(ticket_key, thread_id=thread_id)
    else:
        # Default to Feature workflow for FEATURE, STORY, EPIC, TASK
        from forge.workflow.feature.state import create_initial_feature_state
        return create_initial_feature_state(ticket_key, thread_id=thread_id, ticket_type=ticket_type)


__all__ = [
    "WorkflowState",
    "create_initial_state",
    "update_state_timestamp",
    "set_paused",
    "resume_state",
    "set_error",
]
