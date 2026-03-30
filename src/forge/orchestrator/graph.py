"""LangGraph workflow definition for SDLC orchestration."""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from forge.models.workflow import TicketType
from forge.orchestrator.gates.prd_approval import (
    prd_approval_gate,
    route_prd_approval,
)
from forge.orchestrator.gates.spec_approval import (
    route_spec_approval,
    spec_approval_gate,
)
from forge.orchestrator.gates.plan_approval import (
    plan_approval_gate,
    route_plan_approval,
)
from forge.orchestrator.nodes.prd_generation import (
    generate_prd,
    regenerate_prd_with_feedback,
)
from forge.orchestrator.nodes.spec_generation import (
    generate_spec,
    regenerate_spec_with_feedback,
)
from forge.orchestrator.nodes.epic_decomposition import (
    decompose_epics,
    regenerate_all_epics,
    update_single_epic,
)
from forge.orchestrator.nodes.task_generation import generate_tasks
from forge.orchestrator.state import WorkflowState

logger = logging.getLogger(__name__)


def route_by_ticket_type(state: WorkflowState) -> Literal["generate_prd", "bug_workflow", "task_workflow"]:
    """Route workflow based on ticket type.

    Args:
        state: Current workflow state.

    Returns:
        Next node name based on ticket type.
    """
    ticket_type = state.get("ticket_type")

    if ticket_type == TicketType.FEATURE:
        return "generate_prd"
    elif ticket_type == TicketType.BUG:
        return "bug_workflow"
    else:
        # Tasks and Epics go directly to task workflow
        return "task_workflow"


def create_workflow_graph() -> StateGraph:
    """Create the main SDLC orchestration workflow graph.

    The graph implements the following flow for Features:
    1. Start -> Route by ticket type
    2. generate_prd -> prd_approval_gate (pause)
    3. On PRD approval: prd_approval_gate -> generate_spec
    4. On PRD rejection: prd_approval_gate -> regenerate_prd -> prd_approval_gate
    5. generate_spec -> spec_approval_gate (pause)
    6. On Spec approval: spec_approval_gate -> decompose_epics
    7. On Spec rejection: spec_approval_gate -> regenerate_spec -> spec_approval_gate
    8. decompose_epics -> plan_approval_gate (pause)
    9. On Plan approval: plan_approval_gate -> generate_tasks
    10. On Feature-level rejection: plan_approval_gate -> regenerate_all_epics
    11. On Epic-level rejection: plan_approval_gate -> update_single_epic

    Returns:
        Configured StateGraph ready for compilation.
    """
    # Create graph with workflow state schema
    graph = StateGraph(WorkflowState)

    # Add entry point that routes by ticket type
    graph.add_node("route_entry", lambda state: state)

    # PRD Generation nodes (US1)
    graph.add_node("generate_prd", generate_prd)
    graph.add_node("prd_approval_gate", prd_approval_gate)
    graph.add_node("regenerate_prd", regenerate_prd_with_feedback)

    # Spec Generation nodes (US2)
    graph.add_node("generate_spec", generate_spec)
    graph.add_node("spec_approval_gate", spec_approval_gate)
    graph.add_node("regenerate_spec", regenerate_spec_with_feedback)

    # Epic Decomposition nodes (US3)
    graph.add_node("decompose_epics", decompose_epics)
    graph.add_node("plan_approval_gate", plan_approval_gate)
    graph.add_node("regenerate_all_epics", regenerate_all_epics)
    graph.add_node("update_single_epic", update_single_epic)

    # Task Generation nodes (US4)
    graph.add_node("generate_tasks", generate_tasks)

    # Placeholder nodes for future phases
    graph.add_node("task_router", _placeholder_node("task_router"))
    graph.add_node("bug_workflow", _placeholder_node("bug_workflow"))
    graph.add_node("task_workflow", _placeholder_node("task_workflow"))

    # Set entry point
    graph.set_entry_point("route_entry")

    # Route from entry based on ticket type
    graph.add_conditional_edges(
        "route_entry",
        route_by_ticket_type,
        {
            "generate_prd": "generate_prd",
            "bug_workflow": "bug_workflow",
            "task_workflow": "task_workflow",
        },
    )

    # PRD generation flow (US1)
    graph.add_edge("generate_prd", "prd_approval_gate")
    graph.add_conditional_edges(
        "prd_approval_gate",
        route_prd_approval,
        {
            "generate_spec": "generate_spec",
            "regenerate_prd": "regenerate_prd",
            "prd_approval_gate": "prd_approval_gate",
        },
    )
    graph.add_edge("regenerate_prd", "prd_approval_gate")

    # Spec generation flow (US2)
    graph.add_edge("generate_spec", "spec_approval_gate")
    graph.add_conditional_edges(
        "spec_approval_gate",
        route_spec_approval,
        {
            "decompose_epics": "decompose_epics",
            "regenerate_spec": "regenerate_spec",
            "spec_approval_gate": "spec_approval_gate",
        },
    )
    graph.add_edge("regenerate_spec", "spec_approval_gate")

    # Epic decomposition flow (US3)
    graph.add_edge("decompose_epics", "plan_approval_gate")
    graph.add_conditional_edges(
        "plan_approval_gate",
        route_plan_approval,
        {
            "generate_tasks": "generate_tasks",
            "regenerate_all_epics": "regenerate_all_epics",
            "update_single_epic": "update_single_epic",
            "plan_approval_gate": "plan_approval_gate",
        },
    )
    graph.add_edge("regenerate_all_epics", "plan_approval_gate")
    graph.add_edge("update_single_epic", "plan_approval_gate")

    # Task generation flow (US4)
    graph.add_edge("generate_tasks", "task_router")

    # Placeholder endpoints (will be connected in future phases)
    graph.add_edge("task_router", END)
    graph.add_edge("bug_workflow", END)
    graph.add_edge("task_workflow", END)

    return graph


def _placeholder_node(name: str):
    """Create a placeholder node for future implementation.

    Args:
        name: Node name for logging.

    Returns:
        Async function that logs and passes state through.
    """
    async def placeholder(state: WorkflowState) -> WorkflowState:
        logger.warning(f"Placeholder node '{name}' reached - not yet implemented")
        return {**state, "current_node": name}
    return placeholder


def compile_workflow(checkpointer=None):
    """Compile the workflow graph with optional checkpointing.

    Args:
        checkpointer: Optional LangGraph checkpointer for state persistence.

    Returns:
        Compiled workflow ready for invocation.
    """
    graph = create_workflow_graph()
    return graph.compile(checkpointer=checkpointer)


# Convenience function to get a compiled workflow
def get_workflow(checkpointer=None):
    """Get a compiled workflow instance.

    Args:
        checkpointer: Optional checkpointer for persistence.

    Returns:
        Compiled workflow.
    """
    return compile_workflow(checkpointer)
