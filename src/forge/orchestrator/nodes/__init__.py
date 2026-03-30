"""LangGraph node implementations for workflow phases."""

from forge.orchestrator.nodes.prd_generation import (
    generate_prd,
    regenerate_prd_with_feedback,
)
from forge.orchestrator.nodes.spec_generation import (
    generate_spec,
    regenerate_spec_with_feedback,
)
from forge.orchestrator.nodes.epic_decomposition import (
    check_all_epics_approved,
    decompose_epics,
    regenerate_all_epics,
    update_single_epic,
)
from forge.orchestrator.nodes.task_generation import (
    extract_repo_from_labels,
    generate_tasks,
)
from forge.orchestrator.nodes.task_router import (
    get_repo_execution_plan,
    route_tasks_by_repo,
)
from forge.orchestrator.nodes.workspace_setup import (
    get_workspace_manager,
    setup_workspace,
    teardown_workspace,
)
from forge.orchestrator.nodes.implementation import implement_task
from forge.orchestrator.nodes.pr_creation import (
    create_pull_request,
    teardown_and_route,
)
from forge.orchestrator.nodes.ci_evaluator import (
    attempt_ci_fix,
    escalate_to_blocked,
    evaluate_ci_status,
)
from forge.orchestrator.nodes.ai_reviewer import (
    check_constitution_compliance,
    check_spec_alignment,
    review_code,
)
from forge.orchestrator.nodes.human_review import (
    aggregate_epic_status,
    aggregate_feature_status,
    complete_tasks,
    handle_review_feedback,
    human_review_gate,
    route_human_review,
)
from forge.orchestrator.nodes.bug_workflow import (
    analyze_bug,
    implement_bug_fix,
    rca_approval_gate,
    regenerate_rca,
    route_rca_approval,
)

__all__ = [
    # PRD generation
    "generate_prd",
    "regenerate_prd_with_feedback",
    # Spec generation
    "generate_spec",
    "regenerate_spec_with_feedback",
    # Epic decomposition
    "check_all_epics_approved",
    "decompose_epics",
    "regenerate_all_epics",
    "update_single_epic",
    # Task generation
    "extract_repo_from_labels",
    "generate_tasks",
    # Task routing
    "get_repo_execution_plan",
    "route_tasks_by_repo",
    # Workspace management
    "get_workspace_manager",
    "setup_workspace",
    "teardown_workspace",
    # Implementation
    "implement_task",
    # PR creation
    "create_pull_request",
    "teardown_and_route",
    # CI/CD evaluation
    "attempt_ci_fix",
    "escalate_to_blocked",
    "evaluate_ci_status",
    # AI review
    "check_constitution_compliance",
    "check_spec_alignment",
    "review_code",
    # Human review
    "aggregate_epic_status",
    "aggregate_feature_status",
    "complete_tasks",
    "handle_review_feedback",
    "human_review_gate",
    "route_human_review",
    # Bug workflow
    "analyze_bug",
    "implement_bug_fix",
    "rca_approval_gate",
    "regenerate_rca",
    "route_rca_approval",
]
