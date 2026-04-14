"""Tests for BugWorkflow."""

import pytest

from forge.models.workflow import TicketType


class TestBugWorkflow:
    """Tests for BugWorkflow class."""

    def test_workflow_has_name(self):
        """BugWorkflow has name attribute."""
        from forge.workflow.bug import BugWorkflow

        workflow = BugWorkflow()
        assert workflow.name == "bug"

    def test_matches_bug_type(self):
        """Matches Bug ticket type."""
        from forge.workflow.bug import BugWorkflow

        workflow = BugWorkflow()

        assert workflow.matches(TicketType.BUG, [], {}) is True

    def test_does_not_match_feature(self):
        """Does not match Feature ticket type."""
        from forge.workflow.bug import BugWorkflow

        workflow = BugWorkflow()

        assert workflow.matches(TicketType.FEATURE, [], {}) is False

    def test_state_schema_returns_bug_state(self):
        """state_schema returns BugState."""
        from forge.workflow.bug import BugWorkflow
        from forge.workflow.bug.state import BugState

        workflow = BugWorkflow()

        assert workflow.state_schema is BugState

    def test_build_graph_returns_state_graph(self):
        """build_graph returns a StateGraph."""
        from langgraph.graph import StateGraph
        from forge.workflow.bug import BugWorkflow

        workflow = BugWorkflow()
        graph = workflow.build_graph()

        assert isinstance(graph, StateGraph)
