"""LangGraph node implementations for workflow phases."""

from forge.workflow.nodes.ai_reviewer import (
    check_constitution_compliance,
    check_spec_alignment,
    review_code,
)
from forge.workflow.nodes.bug_workflow import (
    analyze_bug,
    implement_bug_fix,
    rca_approval_gate,
    regenerate_rca,
    route_rca_approval,
)
from forge.workflow.nodes.ci_evaluator import (
    attempt_ci_fix,
    escalate_to_blocked,
    evaluate_ci_status,
)
from forge.workflow.nodes.epic_decomposition import (
    check_all_epics_approved,
    decompose_epics,
    regenerate_all_epics,
    update_single_epic,
)
from forge.workflow.nodes.error_handler import notify_error
from forge.workflow.nodes.human_review import (
    aggregate_epic_status,
    aggregate_feature_status,
    complete_tasks,
    handle_review_feedback,
    human_review_gate,
    route_human_review,
)
from forge.workflow.nodes.implementation import implement_task
from forge.workflow.nodes.pr_creation import (
    create_pull_request,
    teardown_and_route,
)
from forge.workflow.nodes.prd_generation import (
    generate_prd,
    regenerate_prd_with_feedback,
)
from forge.workflow.nodes.spec_generation import (
    generate_spec,
    regenerate_spec_with_feedback,
)
from forge.workflow.nodes.task_generation import (
    extract_repo_from_labels,
    generate_tasks,
)
from forge.workflow.nodes.task_router import (
    ParallelExecutionTracker,
    aggregate_parallel_results,
    get_repo_execution_plan,
    route_tasks_by_repo,
    route_tasks_parallel,
    should_use_parallel_execution,
)
from forge.workflow.nodes.workspace_setup import (
    get_workspace_manager,
    setup_workspace,
    teardown_workspace,
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
    # Task routing and parallel execution
    "ParallelExecutionTracker",
    "aggregate_parallel_results",
    "get_repo_execution_plan",
    "route_tasks_by_repo",
    "route_tasks_parallel",
    "should_use_parallel_execution",
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
    # Error handling
    "notify_error",
]
