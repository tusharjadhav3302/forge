"""Tests for removal of ai_review and replacement with local_review.

All tests here should FAIL before the implementation is done.
"""

import pytest
from langgraph.graph import END

from tests.fixtures.workflow_states import make_workflow_state


# ── Bug graph: CI pass routes to human_review_gate, not ai_review ────────────


class TestBugCIRoutingSkipsAIReview:

    def test_ci_passed_routes_to_human_review_gate(self):
        """Bug: CI pass goes straight to human_review_gate, not ai_review."""
        from forge.workflow.bug.graph import _route_ci_evaluation

        state = make_workflow_state(ci_status="passed")
        assert _route_ci_evaluation(state) == "human_review_gate"

    def test_ci_fixing_still_routes_to_attempt_ci_fix(self):
        """`fixing` status is unchanged."""
        from forge.workflow.bug.graph import _route_ci_evaluation

        state = make_workflow_state(ci_status="fixing")
        assert _route_ci_evaluation(state) == "attempt_ci_fix"

    def test_ci_pending_still_routes_to_end(self):
        """`pending` status is unchanged."""
        from forge.workflow.bug.graph import _route_ci_evaluation

        state = make_workflow_state(ci_status="pending")
        assert _route_ci_evaluation(state) == END


# ── Bug graph: implement_bug_fix routes to local_review, not create_pr ────────


class TestBugImplementationRoutesToLocalReview:

    def test_successful_fix_routes_to_local_review(self):
        """Bug fix routes to local_review before PR creation."""
        from forge.workflow.bug.graph import _route_after_implementation

        state = make_workflow_state(bug_fix_implemented=True, last_error=None)
        assert _route_after_implementation(state) == "local_review"

    def test_failed_fix_still_escalates(self):
        """Failures still escalate to blocked."""
        from forge.workflow.bug.graph import _route_after_implementation

        state = make_workflow_state(bug_fix_implemented=False)
        assert _route_after_implementation(state) == "escalate_blocked"


# ── Bug graph: resume routing handles local_review and drops ai_review ────────


class TestBugResumeRoutingAfterChange:

    @pytest.mark.parametrize("node,expected", [
        ("local_review", "local_review"),        # new: must resume at local_review
        ("ai_review", "human_review_gate"),      # compat: old checkpoints resume at human_review
        ("human_review_gate", "human_review_gate"),
    ])
    def test_resume_routing(self, node, expected):
        from forge.workflow.bug.graph import route_entry

        state = make_workflow_state(current_node=node, ticket_type="Bug")
        assert route_entry(state) == expected


# ── Bug graph: ai_review node not in graph ───────────────────────────────────


class TestAIReviewRemovedFromBugGraph:

    def test_ai_review_not_a_node_in_bug_graph(self):
        """ai_review must not exist as a node in the compiled bug graph."""
        from forge.workflow.bug.graph import build_bug_graph
        from forge.workflow.bug.state import BugState

        graph = build_bug_graph()
        compiled = graph.compile()
        node_names = list(compiled.get_graph().nodes.keys())
        assert "ai_review" not in node_names

    def test_local_review_is_a_node_in_bug_graph(self):
        """local_review must exist as a node in the bug graph."""
        from forge.workflow.bug.graph import build_bug_graph

        graph = build_bug_graph()
        compiled = graph.compile()
        node_names = list(compiled.get_graph().nodes.keys())
        assert "local_review" in node_names


# ── Feature graph: dead _route_ai_review removed ─────────────────────────────


class TestFeatureAIReviewDeadCodeRemoved:

    def test_route_ai_review_not_in_feature_graph(self):
        """_route_ai_review must not exist in the feature graph module."""
        import forge.workflow.feature.graph as fg
        assert not hasattr(fg, "_route_ai_review")


# ── Feature ci_evaluator: CI pass sets human_review_gate, not ai_review ──────


class TestFeatureCIPassSetsCorrectNode:

    def test_ci_pass_current_node_is_human_review_gate(self):
        """evaluate_ci_status sets current_node=human_review_gate when CI passes."""
        from forge.workflow.feature.graph import _route_ci_evaluation

        state = make_workflow_state(ci_status="passed")
        assert _route_ci_evaluation(state) == "human_review_gate"


# ── ai_reviewer module removed or has no graph-facing exports ─────────────────


class TestAIReviewerModuleCleanup:

    def test_review_code_not_exported_from_nodes(self):
        """review_code must not be in forge.workflow.nodes public API."""
        import forge.workflow.nodes as nodes
        assert not hasattr(nodes, "review_code")

    def test_check_spec_alignment_not_exported_from_nodes(self):
        """check_spec_alignment must not be in forge.workflow.nodes."""
        import forge.workflow.nodes as nodes
        assert not hasattr(nodes, "check_spec_alignment")

    def test_check_constitution_compliance_not_exported_from_nodes(self):
        """check_constitution_compliance must not be in forge.workflow.nodes."""
        import forge.workflow.nodes as nodes
        assert not hasattr(nodes, "check_constitution_compliance")
