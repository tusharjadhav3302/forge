# Data Model: AI-Integrated SDLC Orchestrator

**Feature**: 001-ai-sdlc-orchestrator
**Date**: 2026-03-30

## Overview

This data model defines the domain entities for the SDLC orchestrator. Note that **Jira is the primary persistence layer** for Feature/Epic/Task artifacts (per Zero-UI architecture). Redis stores workflow execution state. The models below represent the orchestrator's internal representation of these entities.

---

## Core Entities

### Feature

Represents a top-level business capability being developed. Maps to a Jira Feature ticket.

| Field | Type | Description |
|-------|------|-------------|
| `jira_key` | string | Jira ticket key (e.g., "PROJ-123") |
| `status` | FeatureStatus | Current workflow status |
| `prd_content` | string | Generated PRD (stored in Jira description) |
| `spec_content` | string | Generated Spec (stored in Jira custom field) |
| `epic_keys` | list[string] | Child Epic Jira keys |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

**Status Transitions**:
```
Drafting PRD → Pending PRD Approval → Drafting Spec → Pending Spec Approval →
Planning → In Progress → Ready for Breakdown → In Development → Done
```

**Validation Rules**:
- `jira_key` must match pattern `[A-Z]+-\d+`
- `prd_content` required before transitioning to "Pending PRD Approval"
- `spec_content` required before transitioning to "Pending Spec Approval"
- At least 1 Epic required before transitioning to "In Progress"

---

### Epic

Represents a logical work unit within a Feature. Maps to a Jira Epic ticket.

| Field | Type | Description |
|-------|------|-------------|
| `jira_key` | string | Jira ticket key |
| `feature_key` | string | Parent Feature Jira key |
| `status` | EpicStatus | Current workflow status |
| `summary` | string | Capability name |
| `plan_content` | string | Implementation plan (stored in Jira description) |
| `task_keys` | list[string] | Child Task Jira keys |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

**Status Transitions**:
```
Pending Plan Approval → Planning → Ready for Breakdown → In Progress → Done
```

**Validation Rules**:
- `feature_key` must reference existing Feature
- `plan_content` required before transitioning to "Ready for Breakdown"
- At least 1 Task required before transitioning to "In Progress"

---

### Task

Represents an implementation unit within an Epic. Maps to a Jira Task ticket.

| Field | Type | Description |
|-------|------|-------------|
| `jira_key` | string | Jira ticket key |
| `epic_key` | string | Parent Epic Jira key |
| `status` | TaskStatus | Current workflow status |
| `summary` | string | Task title |
| `description` | string | Implementation details (stored in Jira description) |
| `target_repo` | string | Target repository name |
| `acceptance_criteria` | list[string] | Testable acceptance criteria |
| `pr_url` | string | Associated Pull Request URL (when created) |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

**Status Transitions**:
```
Created → In Development → Pending CI/CD → Pending AI Review →
In Review → Done | Blocked
```

**Validation Rules**:
- `epic_key` must reference existing Epic
- `target_repo` required and must be non-empty
- `description` must contain implementation steps
- `acceptance_criteria` must have at least 1 item

---

## Workflow Entities

### WorkflowState

Represents the current state of a workflow execution thread. Persisted in Redis via LangGraph checkpointer.

| Field | Type | Description |
|-------|------|-------------|
| `thread_id` | string | Unique workflow thread identifier |
| `ticket_key` | string | Associated Jira ticket key |
| `ticket_type` | TicketType | Feature, Epic, Task, or Bug |
| `current_node` | string | Current LangGraph node name |
| `is_paused` | boolean | Whether waiting for HITL approval |
| `retry_count` | integer | Number of retry attempts (for CI fixes) |
| `last_error` | string | Last error message (if any) |
| `context` | dict | Node-specific context data |
| `created_at` | datetime | Thread creation timestamp |
| `updated_at` | datetime | Last state update timestamp |

**Validation Rules**:
- `thread_id` must be unique
- `retry_count` must not exceed configured max (default: 5)

---

### WebhookEvent

Represents an incoming webhook event from Jira or GitHub.

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | string | Unique event identifier (from webhook payload) |
| `source` | EventSource | "jira" or "github" |
| `event_type` | string | Event type (e.g., "issue_updated", "pull_request") |
| `ticket_key` | string | Associated ticket key |
| `payload` | dict | Raw webhook payload |
| `received_at` | datetime | Reception timestamp |
| `processed_at` | datetime | Processing completion timestamp |
| `status` | EventStatus | pending, processing, completed, failed, duplicate |

**Validation Rules**:
- `event_id` must be unique (deduplication key)
- `source` must be "jira" or "github"
- `payload` must be valid JSON

---

### Workspace

Represents an ephemeral execution environment for AI code generation.

| Field | Type | Description |
|-------|------|-------------|
| `workspace_id` | string | Unique workspace identifier |
| `task_key` | string | Associated Task Jira key |
| `repo_name` | string | Target repository name |
| `repo_url` | string | Repository clone URL |
| `branch_name` | string | Feature branch name |
| `local_path` | string | Local filesystem path |
| `status` | WorkspaceStatus | created, active, committed, destroyed |
| `guardrails_loaded` | boolean | Whether constitution.md/agents.md loaded |
| `created_at` | datetime | Creation timestamp |
| `destroyed_at` | datetime | Destruction timestamp |

**Validation Rules**:
- `local_path` must be a valid temporary directory path
- Workspace must be destroyed within 24 hours of creation
- `guardrails_loaded` must be true before code execution

---

## Enumerations

### FeatureStatus
```
DRAFTING_PRD | PENDING_PRD_APPROVAL | DRAFTING_SPEC | PENDING_SPEC_APPROVAL |
PLANNING | IN_PROGRESS | READY_FOR_BREAKDOWN | IN_DEVELOPMENT | DONE
```

### EpicStatus
```
PENDING_PLAN_APPROVAL | PLANNING | READY_FOR_BREAKDOWN | IN_PROGRESS | DONE
```

### TaskStatus
```
CREATED | IN_DEVELOPMENT | PENDING_CICD | PENDING_AI_REVIEW | IN_REVIEW | DONE | BLOCKED
```

### TicketType
```
FEATURE | EPIC | TASK | BUG
```

### EventSource
```
JIRA | GITHUB
```

### EventStatus
```
PENDING | PROCESSING | COMPLETED | FAILED | DUPLICATE
```

### WorkspaceStatus
```
CREATED | ACTIVE | COMMITTED | DESTROYED
```

---

## Relationships

```
Feature (1) ──────< Epic (many)
    │                  │
    │                  │
    └── contains ──────┘

Epic (1) ──────< Task (many)
    │                │
    │                │
    └── contains ────┘

Task (1) ────── Workspace (1)
    │                │
    │                │
    └── executes in ─┘

WorkflowState (1) ────── Ticket (1)
    │                        │
    │                        │
    └── tracks execution of ─┘

WebhookEvent (many) ────── Ticket (1)
    │                           │
    │                           │
    └── triggers workflow for ──┘
```

---

## Notes

- **Jira as Source of Truth**: Feature, Epic, Task content is stored in Jira. The orchestrator maintains lightweight references (`jira_key`) and caches content for processing.
- **Redis for State**: WorkflowState is persisted in Redis via LangGraph checkpointer. This enables pause/resume across process restarts.
- **Ephemeral Workspaces**: Workspace records track lifecycle but the actual filesystems are temporary directories destroyed after PR creation.
- **Event Deduplication**: WebhookEvent records enable idempotent processing by tracking `event_id`.
