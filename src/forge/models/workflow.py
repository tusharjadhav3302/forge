"""Workflow state models and status enums."""

from enum import Enum


class FeatureStatus(str, Enum):
    """Status values for Feature tickets in the SDLC workflow."""

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
    """Status values for Epic tickets in the SDLC workflow."""

    PENDING_PLAN_APPROVAL = "Pending Plan Approval"
    PLANNING = "Planning"
    READY_FOR_BREAKDOWN = "Ready for Breakdown"
    IN_PROGRESS = "In Progress"
    DONE = "Done"


class TaskStatus(str, Enum):
    """Status values for Task tickets in the SDLC workflow."""

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


class WorkspaceStatus(str, Enum):
    """Status values for ephemeral workspaces."""

    CREATED = "created"
    ACTIVE = "active"
    COMMITTED = "committed"
    DESTROYED = "destroyed"
