"""Bug workflow state definition."""

from datetime import datetime
from typing import Any

from forge.models.workflow import TicketType
from forge.workflow.base import (
    BaseState,
    CIIntegrationState,
    PRIntegrationState,
    ReviewIntegrationState,
)


class BugState(
    BaseState, PRIntegrationState, CIIntegrationState, ReviewIntegrationState, total=False
):
    """State specific to Bug workflow."""

    ticket_type: TicketType

    # Bug-specific
    rca_content: str | None
    bug_fix_implemented: bool


def create_initial_bug_state(ticket_key: str, **kwargs: Any) -> BugState:
    """Create initial state for a new Bug workflow run."""
    now = datetime.utcnow().isoformat()
    return BugState(
        thread_id=ticket_key,
        ticket_key=ticket_key,
        ticket_type=TicketType.BUG,
        current_node="start",
        is_paused=False,
        retry_count=0,
        last_error=None,
        created_at=now,
        updated_at=now,
        rca_content=None,
        bug_fix_implemented=False,
        workspace_path=None,
        pr_urls=[],
        ci_status=None,
        current_pr_url=None,
        current_pr_number=None,
        current_repo=None,
        repos_to_process=[],
        repos_completed=[],
        implemented_tasks=[],
        current_task_key=None,
        ci_failed_checks=[],
        ci_fix_attempts=0,
        ai_review_status=None,
        ai_review_results=[],
        human_review_status=None,
        pr_merged=False,
        feedback_comment=None,
        revision_requested=False,
        messages=[],
        context={},
        **kwargs,
    )
