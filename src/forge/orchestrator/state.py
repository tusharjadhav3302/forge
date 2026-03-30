"""Workflow state definitions for LangGraph orchestrator."""

from datetime import datetime
from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph.message import add_messages

from forge.models.workflow import TicketType


class WorkflowState(TypedDict, total=False):
    """State schema for LangGraph workflow execution.

    This TypedDict defines the structure of the state that flows
    through the LangGraph orchestrator. It tracks the current ticket,
    generated artifacts, and execution progress.
    """

    # Core identifiers
    thread_id: str
    ticket_key: str
    ticket_type: TicketType

    # Current execution state
    current_node: str
    is_paused: bool
    retry_count: int
    last_error: Optional[str]

    # Timestamps
    created_at: str
    updated_at: str

    # Feature artifacts
    prd_content: str
    spec_content: str

    # Epic tracking
    epic_keys: list[str]
    current_epic_key: Optional[str]

    # Task tracking
    task_keys: list[str]
    tasks_by_repo: dict[str, list[str]]  # repo_name -> task_keys

    # Execution state
    workspace_path: Optional[str]
    pr_urls: list[str]
    ci_status: Optional[str]

    # Feedback and comments
    feedback_comment: Optional[str]
    revision_requested: bool

    # Message history for LangGraph
    messages: Annotated[list[Any], add_messages]

    # Arbitrary context data
    context: dict[str, Any]


def create_initial_state(
    thread_id: str,
    ticket_key: str,
    ticket_type: TicketType,
) -> WorkflowState:
    """Create initial workflow state for a new ticket.

    Args:
        thread_id: Unique workflow thread identifier.
        ticket_key: Jira ticket key.
        ticket_type: Type of ticket (Feature, Epic, Task, Bug).

    Returns:
        Initialized WorkflowState.
    """
    now = datetime.utcnow().isoformat()
    return WorkflowState(
        thread_id=thread_id,
        ticket_key=ticket_key,
        ticket_type=ticket_type,
        current_node="start",
        is_paused=False,
        retry_count=0,
        last_error=None,
        created_at=now,
        updated_at=now,
        prd_content="",
        spec_content="",
        epic_keys=[],
        current_epic_key=None,
        task_keys=[],
        tasks_by_repo={},
        workspace_path=None,
        pr_urls=[],
        ci_status=None,
        feedback_comment=None,
        revision_requested=False,
        messages=[],
        context={},
    )


def update_state_timestamp(state: WorkflowState) -> WorkflowState:
    """Update the state timestamp.

    Args:
        state: Current workflow state.

    Returns:
        State with updated timestamp.
    """
    return {**state, "updated_at": datetime.utcnow().isoformat()}


def set_paused(state: WorkflowState, node_name: str) -> WorkflowState:
    """Set the state to paused at a specific node.

    Args:
        state: Current workflow state.
        node_name: Name of the node where paused.

    Returns:
        Updated state.
    """
    return {
        **state,
        "current_node": node_name,
        "is_paused": True,
        "updated_at": datetime.utcnow().isoformat(),
    }


def resume_state(state: WorkflowState) -> WorkflowState:
    """Resume a paused state.

    Args:
        state: Current workflow state.

    Returns:
        Updated state with is_paused=False.
    """
    return {
        **state,
        "is_paused": False,
        "updated_at": datetime.utcnow().isoformat(),
    }


def set_error(state: WorkflowState, error: str) -> WorkflowState:
    """Record an error in the state.

    Args:
        state: Current workflow state.
        error: Error message.

    Returns:
        Updated state with error recorded.
    """
    return {
        **state,
        "last_error": error,
        "retry_count": state.get("retry_count", 0) + 1,
        "updated_at": datetime.utcnow().isoformat(),
    }
