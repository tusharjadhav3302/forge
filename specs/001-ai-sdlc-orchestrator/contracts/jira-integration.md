# Integration Contract: Jira

**Service**: Forge Orchestrator ↔ Jira
**API Version**: REST API v3
**Direction**: Bidirectional (webhooks inbound, API calls outbound)

## Overview

Jira serves as the **Single Source of Truth** for all SDLC artifacts. The orchestrator:
1. **Receives** webhook events when ticket status changes or comments are added
2. **Updates** ticket fields with generated artifacts (PRD, Spec, Plan, Tasks)
3. **Creates** child tickets (Epics under Features, Tasks under Epics)
4. **Transitions** ticket status as workflow phases complete

---

## Ticket Type Mapping

| Jira Issue Type | Orchestrator Entity | Artifact Location |
|-----------------|---------------------|-------------------|
| Feature | Feature | PRD → description, Spec → custom field "Specification" |
| Epic | Epic | Plan → description |
| Task | Task | Implementation details → description |
| Bug | Bug (special workflow) | RCA → comment, Fix details → description |

---

## Workflow Status Mapping

### Feature Statuses

| Jira Status | Orchestrator Action |
|-------------|---------------------|
| `Drafting PRD` | Trigger PRD generation (node_1) |
| `Pending PRD Approval` | Pause for PM review |
| `Drafting Spec` | Trigger Spec generation (node_2) |
| `Pending Spec Approval` | Pause for PM review |
| `Planning` | Trigger Epic decomposition (node_3) |
| `In Progress` | Epics created, awaiting approval |
| `Ready for Breakdown` | Trigger Task generation (node_4) |
| `In Development` | Tasks being executed |
| `Done` | All work complete |

### Epic Statuses

| Jira Status | Orchestrator Action |
|-------------|---------------------|
| `Pending Plan Approval` | Pause for Tech Lead review |
| `Planning` | Regenerate plan (on feedback) |
| `Ready for Breakdown` | Ready for task generation |
| `In Progress` | Tasks being executed |
| `Done` | All child Tasks complete |

### Task Statuses

| Jira Status | Orchestrator Action |
|-------------|---------------------|
| `Created` | Queued for execution |
| `In Development` | Code being written |
| `Pending CI/CD` | PR opened, waiting for CI |
| `Pending AI Review` | CI passed, AI reviewing |
| `In Review` | Human review in progress |
| `Done` | PR merged |
| `Blocked` | Requires human intervention |

---

## API Operations

### Read Operations

#### Get Issue Details
```
GET /rest/api/3/issue/{issueKey}
```

**Used When**: Reading ticket content for generation context

**Response Fields Used**:
- `fields.summary` - Ticket title
- `fields.description` - Main content (PRD for Features, Plan for Epics)
- `fields.status.name` - Current status
- `fields.issuetype.name` - Issue type
- `fields.parent.key` - Parent ticket key
- `fields.customfield_XXXXX` - Specification field (for Features)
- `fields.labels` - Target repository (for Tasks)

---

### Write Operations

#### Update Issue Description
```
PUT /rest/api/3/issue/{issueKey}
```

**Used When**: Writing generated PRD, Spec, Plan, or Task details

**Request Body**:
```json
{
  "fields": {
    "description": {
      "type": "doc",
      "version": 1,
      "content": [
        {
          "type": "paragraph",
          "content": [
            {
              "type": "text",
              "text": "Generated content here..."
            }
          ]
        }
      ]
    }
  }
}
```

**Note**: Jira v3 uses Atlassian Document Format (ADF) for rich text fields.

---

#### Update Custom Field (Specification)
```
PUT /rest/api/3/issue/{issueKey}
```

**Used When**: Writing generated Spec to Feature ticket

**Request Body**:
```json
{
  "fields": {
    "customfield_XXXXX": "Full specification content as plain text or ADF..."
  }
}
```

---

#### Create Epic
```
POST /rest/api/3/issue
```

**Used When**: Creating Epics during Planning phase

**Request Body**:
```json
{
  "fields": {
    "project": {
      "key": "PROJ"
    },
    "summary": "Epic: Payment Gateway Integration",
    "description": {
      "type": "doc",
      "version": 1,
      "content": [...]
    },
    "issuetype": {
      "name": "Epic"
    },
    "parent": {
      "key": "PROJ-123"
    }
  }
}
```

---

#### Create Task
```
POST /rest/api/3/issue
```

**Used When**: Creating Tasks during Breakdown phase

**Request Body**:
```json
{
  "fields": {
    "project": {
      "key": "PROJ"
    },
    "summary": "Configure Stripe SDK in backend",
    "description": {
      "type": "doc",
      "version": 1,
      "content": [...]
    },
    "issuetype": {
      "name": "Task"
    },
    "parent": {
      "key": "PROJ-124"
    },
    "labels": ["backend-api"]
  }
}
```

**Note**: `labels` field contains target repository for execution grouping.

---

#### Transition Issue Status
```
POST /rest/api/3/issue/{issueKey}/transitions
```

**Used When**: Advancing ticket through workflow

**Request Body**:
```json
{
  "transition": {
    "id": "31"
  }
}
```

**Note**: Transition IDs are workflow-specific. Query available transitions first:
```
GET /rest/api/3/issue/{issueKey}/transitions
```

---

#### Add Comment
```
POST /rest/api/3/issue/{issueKey}/comment
```

**Used When**:
- Posting RCA for Bug tickets
- Posting AI review feedback
- Posting error/escalation notifications

**Request Body**:
```json
{
  "body": {
    "type": "doc",
    "version": 1,
    "content": [
      {
        "type": "paragraph",
        "content": [
          {
            "type": "text",
            "text": "Root Cause Analysis:\n\n..."
          }
        ]
      }
    ]
  }
}
```

---

#### Delete Issue (Epic Regeneration)
```
DELETE /rest/api/3/issue/{issueKey}
```

**Used When**: Feature-level feedback requires deleting and regenerating all Epics

**Parameters**:
- `deleteSubtasks=true` - Also delete child Tasks

---

## Webhook Events

### Events to Subscribe

| Event | Trigger |
|-------|---------|
| `jira:issue_updated` | Status change, field update |
| `comment_created` | New comment (feedback) |
| `comment_updated` | Edited comment |

### Webhook Payload Processing

1. **Extract Event Type**: Check `webhookEvent` field
2. **Extract Ticket Key**: Get from `issue.key`
3. **Check Changelog**: Look for status transitions in `changelog.items`
4. **Check Comments**: Look for new feedback in `comment` field
5. **Route to Node**: Map status to appropriate LangGraph node

---

## Error Handling

| Jira Error | Orchestrator Response |
|------------|----------------------|
| 401 Unauthorized | Refresh token, retry once, then escalate |
| 403 Forbidden | Log error, mark ticket as Blocked |
| 404 Not Found | Ticket deleted externally, terminate workflow |
| 429 Rate Limited | Exponential backoff (1s, 2s, 4s, 8s, 16s) |
| 5xx Server Error | Retry with backoff, escalate after 3 failures |

---

## Configuration Requirements

| Setting | Description |
|---------|-------------|
| `JIRA_BASE_URL` | Jira instance URL (e.g., `https://company.atlassian.net`) |
| `JIRA_API_TOKEN` | API token for authentication |
| `JIRA_USER_EMAIL` | Email associated with API token |
| `JIRA_SPEC_CUSTOM_FIELD` | Custom field ID for Specification (e.g., `customfield_10050`) |
| `JIRA_WEBHOOK_SECRET` | Shared secret for webhook validation |

---

## Field Mapping Reference

| Orchestrator Field | Jira Field | Notes |
|--------------------|------------|-------|
| Feature.prd_content | description | ADF format |
| Feature.spec_content | customfield_XXXXX | Plain text or ADF |
| Epic.plan_content | description | ADF format |
| Task.description | description | ADF format |
| Task.target_repo | labels[0] | First label = repo name |
| Task.acceptance_criteria | description | Embedded in description |
