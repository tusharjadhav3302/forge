"""Workflow state definitions - DEPRECATED, use forge.workflow.* instead.

This module is maintained for backward compatibility only.
New code should import directly from forge.workflow modules.
"""

import warnings

from forge.models.workflow import TicketType

# Re-export from workflow module for backward compatibility
from forge.workflow.base import BaseState
from forge.workflow.feature.state import FeatureState as WorkflowState
from forge.workflow.utils import (
    resume_state,
    set_error,
    set_paused,
    update_state_timestamp,
)

warnings.warn(
    "forge.orchestrator.state is deprecated. Use forge.workflow.feature.state or "
    "forge.workflow.bug.state directly.",
    DeprecationWarning,
    stacklevel=2,
)


def create_initial_state(
    thread_id: str,
    ticket_key: str,
    ticket_type: TicketType,
) -> WorkflowState:
    """Create initial workflow state for a new ticket.

    DEPRECATED: Use workflow-specific state creation functions instead.

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
        from forge.workflow.feature.state import create_initial_feature_state
        return create_initial_feature_state(ticket_key, thread_id=thread_id, ticket_type=ticket_type)


__all__ = [
    "BaseState",
    "WorkflowState",
    "create_initial_state",
    "update_state_timestamp",
    "set_paused",
    "resume_state",
    "set_error",
]
