"""Workflow state models and status enums."""

from enum import Enum


class JiraStatus(str, Enum):
    """Standard Jira statuses available in the AISOS project."""

    NEW = "New"
    REFINEMENT = "Refinement"
    IN_PROGRESS = "In Progress"
    CLOSED = "Closed"


class ForgeLabel(str, Enum):
    """Labels used to track Forge workflow state.

    These labels are added/removed to track progress through the
    SDLC workflow without requiring custom Jira statuses.
    """

    # PRD workflow
    PRD_DRAFTING = "forge:prd-drafting"
    PRD_PENDING = "forge:prd-pending"
    PRD_APPROVED = "forge:prd-approved"
    PRD_REJECTED = "forge:prd-rejected"

    # Spec workflow
    SPEC_DRAFTING = "forge:spec-drafting"
    SPEC_PENDING = "forge:spec-pending"
    SPEC_APPROVED = "forge:spec-approved"
    SPEC_REJECTED = "forge:spec-rejected"

    # Epic/Plan workflow
    PLAN_DRAFTING = "forge:plan-drafting"
    PLAN_PENDING = "forge:plan-pending"
    PLAN_APPROVED = "forge:plan-approved"
    PLAN_REJECTED = "forge:plan-rejected"

    # Task workflow
    TASK_GENERATED = "forge:task-generated"
    TASK_IMPLEMENTING = "forge:implementing"
    TASK_PR_CREATED = "forge:pr-created"
    TASK_CI_PENDING = "forge:ci-pending"
    TASK_CI_FAILED = "forge:ci-failed"
    TASK_REVIEW_PENDING = "forge:review-pending"
    TASK_REVIEW_APPROVED = "forge:review-approved"

    # Bug workflow
    RCA_DRAFTING = "forge:rca-drafting"
    RCA_PENDING = "forge:rca-pending"
    RCA_APPROVED = "forge:rca-approved"

    # General
    FORGE_MANAGED = "forge:managed"
    BLOCKED = "forge:blocked"


# Legacy status enums - kept for backward compatibility
class FeatureStatus(str, Enum):
    """Status values for Feature tickets in the SDLC workflow.

    DEPRECATED: Use JiraStatus + ForgeLabel instead.
    """

    DRAFTING_PRD = "Drafting PRD"
    PENDING_PRD_APPROVAL = "Pending PRD Approval"
    DRAFTING_SPEC = "Drafting Spec"
    PENDING_SPEC_APPROVAL = "Pending Spec Approval"
    PLANNING = "Planning"
    IN_PROGRESS = "In Progress"
    READY_FOR_BREAKDOWN = "Ready for Breakdown"
    IN_DEVELOPMENT = "In Development"
    DONE = "Done"


class EpicStatus(str, Enum):
    """Status values for Epic tickets in the SDLC workflow.

    DEPRECATED: Use JiraStatus + ForgeLabel instead.
    """

    PENDING_PLAN_APPROVAL = "Pending Plan Approval"
    PLANNING = "Planning"
    READY_FOR_BREAKDOWN = "Ready for Breakdown"
    IN_PROGRESS = "In Progress"
    DONE = "Done"


class TaskStatus(str, Enum):
    """Status values for Task tickets in the SDLC workflow.

    DEPRECATED: Use JiraStatus + ForgeLabel instead.
    """

    CREATED = "Created"
    IN_DEVELOPMENT = "In Development"
    PENDING_CICD = "Pending CI/CD"
    PENDING_AI_REVIEW = "Pending AI Review"
    IN_REVIEW = "In Review"
    DONE = "Done"
    BLOCKED = "Blocked"


class TicketType(str, Enum):
    """Jira issue types supported by the orchestrator."""

    FEATURE = "Feature"
    EPIC = "Epic"
    TASK = "Task"
    BUG = "Bug"
    # Also support Story as an alias for Feature
    STORY = "Story"


class WorkspaceStatus(str, Enum):
    """Status values for ephemeral workspaces."""

    CREATED = "created"
    ACTIVE = "active"
    COMMITTED = "committed"
    DESTROYED = "destroyed"


def get_workflow_phase(labels: list[str]) -> str | None:
    """Determine workflow phase from Forge labels.

    Args:
        labels: List of Jira labels on the issue.

    Returns:
        Current workflow phase or None if not Forge-managed.
    """
    forge_labels = [l for l in labels if l.startswith("forge:")]

    if not forge_labels:
        return None

    # Priority order for phase detection
    phase_priority = [
        (ForgeLabel.PRD_PENDING.value, "prd_approval"),
        (ForgeLabel.PRD_DRAFTING.value, "prd_generation"),
        (ForgeLabel.SPEC_PENDING.value, "spec_approval"),
        (ForgeLabel.SPEC_DRAFTING.value, "spec_generation"),
        (ForgeLabel.PLAN_PENDING.value, "plan_approval"),
        (ForgeLabel.PLAN_DRAFTING.value, "epic_decomposition"),
        (ForgeLabel.RCA_PENDING.value, "rca_approval"),
        (ForgeLabel.RCA_DRAFTING.value, "rca_generation"),
        (ForgeLabel.TASK_REVIEW_PENDING.value, "human_review"),
        (ForgeLabel.TASK_CI_PENDING.value, "ci_evaluation"),
        (ForgeLabel.TASK_IMPLEMENTING.value, "implementation"),
    ]

    for label, phase in phase_priority:
        if label in forge_labels:
            return phase

    return "unknown"
