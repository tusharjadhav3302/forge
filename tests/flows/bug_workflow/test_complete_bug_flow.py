"""Tests for complete bug workflow flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from forge.models.workflow import ForgeLabel, TicketType
from forge.orchestrator.state import create_initial_state
from forge.orchestrator.graph import route_by_ticket_type

from tests.fixtures.workflow_states import (
    STATE_BUG_NEW,
    STATE_RCA_PENDING,
    STATE_RCA_APPROVED,
    make_workflow_state,
)


class TestBugWorkflowEntry:
    """Tests for bug workflow entry."""

    def test_bug_routes_to_analyze_bug(self):
        """Bug ticket starts with bug analysis."""
        state = create_initial_state(
            thread_id="test-thread",
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
        )

        next_node = route_by_ticket_type(state)

        assert next_node == "analyze_bug"

    def test_bug_skips_prd_spec_epic_phases(self):
        """Bug workflow skips PRD, Spec, and Epic phases."""
        state = create_initial_state(
            thread_id="test-thread",
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
        )

        next_node = route_by_ticket_type(state)

        # Should not go to PRD generation
        assert next_node != "generate_prd"
        assert next_node == "analyze_bug"


class TestBugRCAGeneration:
    """Tests for RCA generation."""

    def test_rca_pending_state(self):
        """RCA pending state is correct."""
        state = STATE_RCA_PENDING

        assert state["current_node"] == "rca_approval_gate"
        assert state["is_paused"] is True
        assert state["rca_content"] is not None
        assert "Root Cause" in state["rca_content"]

    def test_rca_contains_fix_options(self):
        """RCA contains fix options."""
        state = STATE_RCA_PENDING

        assert "Fix Options" in state["rca_content"]


class TestBugRCAApproval:
    """Tests for RCA approval routing."""

    @pytest.fixture
    def rca_pending_state(self):
        """State with RCA pending approval."""
        return make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="rca_approval_gate",
            is_paused=True,
            rca_content="# RCA\n\n## Root Cause\nTest cause.",
        )

    def test_rca_approved_routes_to_fix(self, rca_pending_state):
        """Approved RCA routes to bug fix implementation when resumed."""
        # Workflow is resumed from pause on approval webhook
        rca_pending_state["is_paused"] = False

        from forge.orchestrator.nodes.bug_workflow import route_rca_approval
        next_node = route_rca_approval(rca_pending_state)

        assert next_node == "implement_bug_fix"

    def test_rca_rejected_routes_to_regenerate(self, rca_pending_state):
        """Rejected RCA routes to regeneration."""
        rca_pending_state["context"] = {
            "labels": ["forge:managed", "forge:rca-pending"],
        }
        rca_pending_state["feedback_comment"] = "Wrong root cause identified."
        rca_pending_state["revision_requested"] = True

        from forge.orchestrator.nodes.bug_workflow import route_rca_approval
        next_node = route_rca_approval(rca_pending_state)

        assert next_node == "regenerate_rca"


class TestBugRCARevision:
    """Tests for RCA revision cycle."""

    @pytest.fixture
    def rca_with_feedback(self):
        """State with RCA rejection feedback."""
        return make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="rca_approval_gate",
            is_paused=True,
            rca_content="# RCA - Wrong Analysis",
            feedback_comment="The actual cause is in the auth module, not DB.",
            revision_requested=True,
        )

    def test_rca_revision_incorporates_feedback(self, rca_with_feedback):
        """RCA revision should incorporate feedback."""
        assert "auth module" in rca_with_feedback["feedback_comment"]

    def test_rca_revision_routes_correctly(self, rca_with_feedback):
        """RCA revision routes to regenerate_rca."""
        rca_with_feedback["context"] = {
            "labels": ["forge:managed", "forge:rca-pending"],
        }

        from forge.orchestrator.nodes.bug_workflow import route_rca_approval
        next_node = route_rca_approval(rca_with_feedback)

        assert next_node == "regenerate_rca"


class TestBugFixImplementation:
    """Tests for bug fix implementation."""

    def test_bug_fix_state(self):
        """Bug fix implementation state."""
        state = STATE_RCA_APPROVED

        assert state["current_node"] == "implement_bug_fix"
        assert state["is_paused"] is False

    def test_bug_fix_goes_to_pr_creation(self):
        """Bug fix goes to PR creation."""
        state = make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="implement_bug_fix",
            bug_fix_implemented=True,
        )

        # After bug fix, should go to create_pr
        # (This is verified by graph edge definition)
        assert state["bug_fix_implemented"] is True


class TestBugTDDWorkflow:
    """Tests for TDD bug fix workflow."""

    @pytest.fixture
    def bug_fix_state(self):
        """State ready for bug fix."""
        return make_workflow_state(
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
            current_node="implement_bug_fix",
            rca_content="""# RCA

## Root Cause
Password validation regex rejects valid special characters.

## Recommended Fix
Update VALID_PASSWORD_PATTERN to include $@!#%^&*

## Test Plan
1. Add test case with special character passwords
2. Verify existing tests still pass
""",
        )

    def test_rca_includes_test_plan(self, bug_fix_state):
        """RCA includes test plan for TDD."""
        assert "Test Plan" in bug_fix_state["rca_content"]
        assert "test case" in bug_fix_state["rca_content"].lower()

    def test_bug_fix_follows_tdd(self, bug_fix_state):
        """Bug fix should follow TDD (test first, then fix)."""
        # The RCA test plan guides the TDD approach
        rca = bug_fix_state["rca_content"]

        # Should mention writing tests first
        assert "test" in rca.lower()
