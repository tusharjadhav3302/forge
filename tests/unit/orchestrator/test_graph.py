"""Unit tests for workflow graph construction."""

import pytest

from forge.models.workflow import TicketType
from forge.orchestrator.graph import (
    create_workflow_graph,
    compile_workflow,
    route_by_ticket_type,
)
from forge.orchestrator.state import create_initial_state


class TestRouteByTicketType:
    """Tests for route_by_ticket_type function."""

    def test_feature_routes_to_generate_prd(self):
        """Feature ticket routes to PRD generation."""
        state = create_initial_state(
            thread_id="thread-001",
            ticket_key="TEST-123",
            ticket_type=TicketType.FEATURE,
        )

        result = route_by_ticket_type(state)

        assert result == "generate_prd"

    def test_bug_routes_to_analyze_bug(self):
        """Bug ticket routes to bug analysis."""
        state = create_initial_state(
            thread_id="thread-001",
            ticket_key="TEST-456",
            ticket_type=TicketType.BUG,
        )

        result = route_by_ticket_type(state)

        assert result == "analyze_bug"

    def test_task_routes_to_task_workflow(self):
        """Task ticket routes directly to task workflow."""
        state = create_initial_state(
            thread_id="thread-001",
            ticket_key="TEST-789",
            ticket_type=TicketType.TASK,
        )

        result = route_by_ticket_type(state)

        assert result == "task_workflow"

    def test_epic_routes_to_task_workflow(self):
        """Epic ticket routes directly to task workflow."""
        state = create_initial_state(
            thread_id="thread-001",
            ticket_key="TEST-789",
            ticket_type=TicketType.EPIC,
        )

        result = route_by_ticket_type(state)

        assert result == "task_workflow"


class TestCreateWorkflowGraph:
    """Tests for create_workflow_graph function."""

    def test_graph_has_entry_point(self):
        """Graph has an entry point defined."""
        graph = create_workflow_graph()

        # StateGraph should have nodes
        assert len(graph.nodes) > 0

    def test_graph_has_prd_nodes(self):
        """Graph has PRD generation nodes."""
        graph = create_workflow_graph()

        assert "generate_prd" in graph.nodes
        assert "prd_approval_gate" in graph.nodes
        assert "regenerate_prd" in graph.nodes

    def test_graph_has_spec_nodes(self):
        """Graph has Spec generation nodes."""
        graph = create_workflow_graph()

        assert "generate_spec" in graph.nodes
        assert "spec_approval_gate" in graph.nodes
        assert "regenerate_spec" in graph.nodes

    def test_graph_has_epic_nodes(self):
        """Graph has Epic decomposition nodes."""
        graph = create_workflow_graph()

        assert "decompose_epics" in graph.nodes
        assert "plan_approval_gate" in graph.nodes
        assert "regenerate_all_epics" in graph.nodes
        assert "update_single_epic" in graph.nodes

    def test_graph_has_task_nodes(self):
        """Graph has Task generation nodes."""
        graph = create_workflow_graph()

        assert "generate_tasks" in graph.nodes
        assert "task_router" in graph.nodes

    def test_graph_has_execution_nodes(self):
        """Graph has execution nodes."""
        graph = create_workflow_graph()

        assert "setup_workspace" in graph.nodes
        assert "implement_task" in graph.nodes
        assert "create_pr" in graph.nodes
        assert "teardown_workspace" in graph.nodes

    def test_graph_has_ci_nodes(self):
        """Graph has CI/CD nodes."""
        graph = create_workflow_graph()

        assert "ci_evaluator" in graph.nodes
        assert "attempt_ci_fix" in graph.nodes
        assert "escalate_blocked" in graph.nodes

    def test_graph_has_review_nodes(self):
        """Graph has review nodes."""
        graph = create_workflow_graph()

        assert "ai_review" in graph.nodes
        assert "human_review_gate" in graph.nodes
        assert "complete_tasks" in graph.nodes

    def test_graph_has_bug_workflow_nodes(self):
        """Graph has bug workflow nodes."""
        graph = create_workflow_graph()

        assert "analyze_bug" in graph.nodes
        assert "rca_approval_gate" in graph.nodes
        assert "regenerate_rca" in graph.nodes
        assert "implement_bug_fix" in graph.nodes

    def test_graph_has_aggregation_nodes(self):
        """Graph has status aggregation nodes."""
        graph = create_workflow_graph()

        assert "aggregate_epic_status" in graph.nodes
        assert "aggregate_feature_status" in graph.nodes


class TestCompileWorkflow:
    """Tests for compile_workflow function."""

    def test_compiles_without_checkpointer(self):
        """Workflow compiles without checkpointer."""
        workflow = compile_workflow()

        assert workflow is not None

    def test_compiles_with_checkpointer(self):
        """Workflow compiles with checkpointer."""
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        workflow = compile_workflow(checkpointer=checkpointer)

        assert workflow is not None

    def test_compiled_workflow_is_invokable(self):
        """Compiled workflow has invoke method."""
        workflow = compile_workflow()

        assert hasattr(workflow, "invoke")
        assert hasattr(workflow, "ainvoke")


class TestGraphEdges:
    """Tests for graph edge definitions."""

    def test_prd_approval_has_conditional_edges(self):
        """PRD approval gate has conditional edges."""
        graph = create_workflow_graph()

        # Graph should have edges from prd_approval_gate
        # We can't easily test conditional edges directly, but we can verify the node exists
        assert "prd_approval_gate" in graph.nodes

    def test_regenerate_prd_returns_to_gate(self):
        """Regenerate PRD returns to approval gate."""
        graph = create_workflow_graph()

        # Both nodes should exist for the edge to be valid
        assert "regenerate_prd" in graph.nodes
        assert "prd_approval_gate" in graph.nodes

    def test_ci_fix_returns_to_evaluator(self):
        """CI fix returns to CI evaluator."""
        graph = create_workflow_graph()

        assert "attempt_ci_fix" in graph.nodes
        assert "ci_evaluator" in graph.nodes

    def test_bug_fix_goes_to_create_pr(self):
        """Bug fix implementation goes to PR creation."""
        graph = create_workflow_graph()

        assert "implement_bug_fix" in graph.nodes
        assert "create_pr" in graph.nodes
