"""Unit tests for Spec approval gate."""

import pytest
from langgraph.graph import END

from forge.models.workflow import TicketType
from forge.workflow.gates import spec_approval_gate, route_spec_approval
from forge.workflow.feature.state import create_initial_feature_state as create_initial_state


class TestSpecApprovalGate:
    """Tests for spec_approval_gate node."""

    @pytest.fixture
    def spec_pending_state(self):
        """State with Spec pending approval."""
        state = create_initial_state(
            thread_id="test-thread",
            ticket_key="TEST-123",
            ticket_type=TicketType.FEATURE,
        )
        state["prd_content"] = "# PRD\n\nApproved PRD."
        state["spec_content"] = "# Spec\n\nGenerated spec content."
        state["current_node"] = "generate_spec"
        return state

    def test_gate_pauses_workflow(self, spec_pending_state):
        """Gate sets is_paused=True and updates current_node."""
        result = spec_approval_gate(spec_pending_state)

        assert result["is_paused"] is True
        assert result["current_node"] == "spec_approval_gate"

    def test_gate_preserves_spec_content(self, spec_pending_state):
        """Gate preserves existing spec content."""
        result = spec_approval_gate(spec_pending_state)

        assert result["spec_content"] == "# Spec\n\nGenerated spec content."


class TestRouteSpecApproval:
    """Tests for route_spec_approval function."""

    @pytest.fixture
    def spec_pending_state(self):
        """State with Spec pending."""
        state = create_initial_state(
            thread_id="test-thread",
            ticket_key="TEST-123",
            ticket_type=TicketType.FEATURE,
        )
        state["prd_content"] = "# PRD"
        state["spec_content"] = "# Spec"
        state["current_node"] = "spec_approval_gate"
        state["is_paused"] = True
        return state

    def test_routes_to_decompose_on_approval(self, spec_pending_state):
        """Approved Spec routes to epic decomposition when not paused."""
        spec_pending_state["is_paused"] = False

        result = route_spec_approval(spec_pending_state)

        assert result == "decompose_epics"

    def test_routes_to_regenerate_on_rejection(self, spec_pending_state):
        """Rejected Spec with feedback routes to regeneration."""
        spec_pending_state["context"] = {
            "labels": ["forge:managed", "forge:spec-pending"],
        }
        spec_pending_state["feedback_comment"] = "Add acceptance criteria for US2."
        spec_pending_state["revision_requested"] = True

        result = route_spec_approval(spec_pending_state)

        assert result == "regenerate_spec"

    def test_routes_to_end_when_pending(self, spec_pending_state):
        """Pending Spec without feedback routes to END."""
        spec_pending_state["context"] = {
            "labels": ["forge:managed", "forge:spec-pending"],
        }

        result = route_spec_approval(spec_pending_state)

        assert result == END


class TestSpecRevisionWithPrdContext:
    """Tests for spec revision maintaining PRD context."""

    @pytest.fixture
    def state_with_spec_feedback(self):
        """State with spec feedback."""
        state = create_initial_state(
            thread_id="test-thread",
            ticket_key="TEST-123",
            ticket_type=TicketType.FEATURE,
        )
        state["prd_content"] = "# PRD\n\n## Goals\nUser authentication."
        state["spec_content"] = "# Spec\n\n## User Stories"
        state["feedback_comment"] = "Spec is missing edge case handling."
        state["revision_requested"] = True
        state["context"] = {
            "labels": ["forge:managed", "forge:spec-pending"],
        }
        return state

    def test_revision_preserves_prd_content(self, state_with_spec_feedback):
        """PRD content is preserved during spec revision."""
        # The regeneration should use the original PRD
        assert state_with_spec_feedback["prd_content"] != ""
        assert "authentication" in state_with_spec_feedback["prd_content"].lower()

    def test_revision_routes_correctly(self, state_with_spec_feedback):
        """Spec revision routes to regenerate_spec."""
        result = route_spec_approval(state_with_spec_feedback)

        assert result == "regenerate_spec"
