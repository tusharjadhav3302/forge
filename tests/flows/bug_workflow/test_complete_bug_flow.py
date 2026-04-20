"""Tests for complete bug workflow flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langgraph.graph import END

from forge.models.workflow import ForgeLabel, TicketType
from forge.workflow.bug.state import create_initial_bug_state
from forge.workflow.bug.graph import route_entry, _route_after_implementation
from forge.workflow.nodes.bug_workflow import route_rca_approval

from tests.fixtures.workflow_states import (
    STATE_BUG_NEW,
    STATE_RCA_PENDING,
    STATE_RCA_APPROVED,
    make_workflow_state,
)


class TestBugWorkflowEntry:
    """Bug workflow entry routing."""

    def test_new_bug_routes_to_analyze_bug(self):
        """A fresh bug ticket starts at analyze_bug."""
        state = create_initial_bug_state(
            thread_id="test-thread",
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
        )

        assert route_entry(state) == "analyze_bug"

    def test_bug_skips_prd_spec_epic_phases(self):
        """Bug workflow never routes to PRD, spec, or epic nodes."""
        state = create_initial_bug_state(
            thread_id="test-thread",
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
        )

        next_node = route_entry(state)

        assert next_node == "analyze_bug"
        assert next_node != "generate_prd"
        assert next_node != "generate_spec"
        assert next_node != "decompose_epics"

    def test_resume_at_rca_gate_routes_back_to_gate(self):
        """Resuming a bug at rca_approval_gate returns to that gate."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            current_node="rca_approval_gate",
            ticket_type=TicketType.BUG,
        )

        assert route_entry(state) == "rca_approval_gate"

    def test_resume_at_implement_routes_there(self):
        """Resuming at implement_bug_fix returns to that node."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            current_node="implement_bug_fix",
            ticket_type=TicketType.BUG,
        )

        assert route_entry(state) == "implement_bug_fix"

    def test_terminal_state_routes_to_end(self):
        """A completed bug workflow returns END on resume attempt."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            current_node="complete",
            ticket_type=TicketType.BUG,
        )

        assert route_entry(state) == END


class TestRCAGenerationState:
    """State correctness after RCA generation."""

    def test_rca_pending_state_is_paused(self):
        """RCA pending state has is_paused=True."""
        assert STATE_RCA_PENDING["is_paused"] is True
        assert STATE_RCA_PENDING["current_node"] == "rca_approval_gate"

    def test_rca_content_is_populated(self):
        """Generated RCA is stored in state."""
        assert STATE_RCA_PENDING["rca_content"] is not None
        assert len(STATE_RCA_PENDING["rca_content"]) > 0

    def test_rca_contains_root_cause_section(self):
        """RCA content includes a Root Cause section."""
        assert "Root Cause" in STATE_RCA_PENDING["rca_content"]

    def test_rca_contains_fix_options(self):
        """RCA content includes fix options."""
        assert "Fix" in STATE_RCA_PENDING["rca_content"]


class TestRCAApprovalRouting:
    """route_rca_approval routing logic."""

    def test_approved_rca_routes_to_implement(self):
        """Approved RCA (is_paused=False, no revision) routes to implement_bug_fix."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="rca_approval_gate",
            is_paused=False,
            rca_content="# RCA\n\n## Root Cause\nTest cause.",
        )

        assert route_rca_approval(state) == "implement_bug_fix"

    def test_paused_rca_routes_to_end(self):
        """Waiting for approval (is_paused=True) returns END."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="rca_approval_gate",
            is_paused=True,
        )

        assert route_rca_approval(state) == END

    def test_rejected_rca_routes_to_regenerate(self):
        """Feedback comment + revision_requested routes to regenerate_rca."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="rca_approval_gate",
            is_paused=False,
            feedback_comment="Wrong root cause — the bug is in the auth module.",
            revision_requested=True,
        )

        assert route_rca_approval(state) == "regenerate_rca"

    def test_question_in_rca_routes_to_answer(self):
        """Q&A question (is_question=True) routes to answer_question before revision."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="rca_approval_gate",
            is_paused=False,
            is_question=True,
            feedback_comment="?Can you explain why you chose Option 1?",
            revision_requested=False,
        )

        assert route_rca_approval(state) == "answer_question"

    def test_question_takes_priority_over_revision(self):
        """Q&A question is processed before revision even if both flags are set."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="rca_approval_gate",
            is_paused=False,
            is_question=True,
            feedback_comment="?Why not option 2?",
            revision_requested=True,
        )

        assert route_rca_approval(state) == "answer_question"


class TestRCARevisionCycle:
    """RCA can be revised multiple times before approval."""

    def test_first_revision_preserves_original_rca(self):
        """State tracks the original RCA content through the revision cycle."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="rca_approval_gate",
            rca_content="# RCA - First Attempt",
            feedback_comment="Wrong module identified.",
            revision_requested=True,
            is_paused=False,
        )

        # feedback_comment is available for the regeneration node
        assert state["feedback_comment"] == "Wrong module identified."

    def test_revision_routes_to_regenerate(self):
        """Rejected RCA with feedback routes to regenerate_rca."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="rca_approval_gate",
            is_paused=False,
            feedback_comment="Wrong root cause.",
            revision_requested=True,
        )

        assert route_rca_approval(state) == "regenerate_rca"

    def test_second_rca_can_be_approved(self):
        """After a revision, the second RCA can be approved normally."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="rca_approval_gate",
            rca_content="# RCA - Revised",
            is_paused=False,
            revision_requested=False,
            feedback_comment=None,
        )

        assert route_rca_approval(state) == "implement_bug_fix"


class TestBugImplementationRouting:
    """_route_after_implementation routes based on success/failure."""

    def test_successful_fix_routes_to_local_review(self):
        """Successful implementation routes to local_review (pre-PR code review)."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="implement_bug_fix",
            bug_fix_implemented=True,
            last_error=None,
        )

        assert _route_after_implementation(state) == "local_review"

    def test_failed_fix_below_retry_cap_escalates(self):
        """Implementation failure below retry cap still escalates (retry handled by worker)."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="implement_bug_fix",
            bug_fix_implemented=False,
            last_error="Container timed out",
            retry_count=0,
        )

        result = _route_after_implementation(state)

        # Either escalates or routes to create_pr (never implemented=False creates PR)
        assert result == "escalate_blocked"

    def test_fix_not_implemented_escalates(self):
        """bug_fix_implemented=False means implementation did not succeed."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="implement_bug_fix",
            bug_fix_implemented=False,
        )

        assert _route_after_implementation(state) == "escalate_blocked"


class TestBugWorkflowResumeRouting:
    """route_entry correctly resumes a bug workflow at any node."""

    @pytest.mark.parametrize("node,expected", [
        ("analyze_bug", "analyze_bug"),
        ("regenerate_rca", "analyze_bug"),
        ("rca_approval_gate", "rca_approval_gate"),
        ("setup_workspace", "setup_workspace"),
        ("implement_bug_fix", "implement_bug_fix"),
        ("create_pr", "create_pr"),
        ("teardown_workspace", "teardown_workspace"),
        ("ci_evaluator", "ci_evaluator"),
        ("attempt_ci_fix", "ci_evaluator"),
        ("local_review", "local_review"),
        ("ai_review", "human_review_gate"),
        ("human_review_gate", "human_review_gate"),
        ("escalate_blocked", "escalate_blocked"),
    ])
    def test_resume_routing(self, node, expected):
        """route_entry maps each node to the correct resume target."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            current_node=node,
            ticket_type=TicketType.BUG,
        )

        result = route_entry(state)

        assert result == expected, (
            f"route_entry with current_node='{node}' returned '{result}', "
            f"expected '{expected}'"
        )
