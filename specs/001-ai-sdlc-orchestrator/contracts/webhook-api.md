# API Contract: Webhook Gateway

**Service**: Forge Orchestrator Webhook Gateway
**Version**: 1.0.0
**Base URL**: `/api/v1`

## Overview

The Webhook Gateway receives events from external systems (Jira, GitHub) and acknowledges them immediately before queueing for asynchronous processing. All endpoints must respond within 500ms.

---

## Endpoints

### POST /api/v1/webhooks/jira

Receives Jira webhook events for ticket status transitions and comments.

**Request Headers**:
| Header | Required | Description |
|--------|----------|-------------|
| `Content-Type` | Yes | Must be `application/json` |
| `X-Atlassian-Webhook-Identifier` | Yes | Unique event identifier for deduplication |
| `X-Atlassian-Token` | No | Webhook secret for signature validation |

**Request Body** (Jira Webhook Payload):
```json
{
  "timestamp": 1711814400000,
  "webhookEvent": "jira:issue_updated",
  "issue_event_type_name": "issue_generic",
  "user": {
    "accountId": "user-account-id",
    "displayName": "John Doe"
  },
  "issue": {
    "id": "10001",
    "key": "PROJ-123",
    "fields": {
      "issuetype": {
        "name": "Feature"
      },
      "status": {
        "name": "Drafting PRD"
      },
      "summary": "Feature title",
      "description": "Feature description content"
    }
  },
  "changelog": {
    "items": [
      {
        "field": "status",
        "fromString": "Open",
        "toString": "Drafting PRD"
      }
    ]
  },
  "comment": null
}
```

**Response** (Success):
```json
{
  "status": "accepted",
  "event_id": "evt_abc123",
  "message": "Event queued for processing"
}
```
- **Status Code**: `202 Accepted`

**Response** (Duplicate Event):
```json
{
  "status": "duplicate",
  "event_id": "evt_abc123",
  "message": "Event already processed"
}
```
- **Status Code**: `200 OK`

**Response** (Validation Error):
```json
{
  "status": "error",
  "error": "Invalid payload: missing required field 'issue.key'"
}
```
- **Status Code**: `400 Bad Request`

---

### POST /api/v1/webhooks/github

Receives GitHub webhook events for PR status, reviews, and merge events.

**Request Headers**:
| Header | Required | Description |
|--------|----------|-------------|
| `Content-Type` | Yes | Must be `application/json` |
| `X-GitHub-Event` | Yes | Event type (e.g., "pull_request", "check_run") |
| `X-GitHub-Delivery` | Yes | Unique event identifier for deduplication |
| `X-Hub-Signature-256` | No | HMAC signature for payload validation |

**Request Body** (Pull Request Event):
```json
{
  "action": "synchronize",
  "number": 42,
  "pull_request": {
    "id": 12345,
    "number": 42,
    "state": "open",
    "title": "PROJ-456: Implement feature X",
    "head": {
      "ref": "feature/PROJ-456",
      "sha": "abc123def456"
    },
    "base": {
      "ref": "main"
    },
    "html_url": "https://github.com/org/repo/pull/42"
  },
  "repository": {
    "full_name": "org/repo"
  }
}
```

**Request Body** (Check Run Event):
```json
{
  "action": "completed",
  "check_run": {
    "id": 789,
    "name": "CI Tests",
    "status": "completed",
    "conclusion": "failure",
    "output": {
      "title": "Test failures",
      "summary": "3 tests failed"
    }
  },
  "pull_request": {
    "number": 42
  },
  "repository": {
    "full_name": "org/repo"
  }
}
```

**Response** (Success):
```json
{
  "status": "accepted",
  "event_id": "evt_def456",
  "message": "Event queued for processing"
}
```
- **Status Code**: `202 Accepted`

---

### GET /api/v1/health

Health check endpoint for load balancers and monitoring.

**Response** (Healthy):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "redis": "connected",
  "queue_depth": 5
}
```
- **Status Code**: `200 OK`

**Response** (Unhealthy):
```json
{
  "status": "unhealthy",
  "version": "1.0.0",
  "redis": "disconnected",
  "error": "Redis connection timeout"
}
```
- **Status Code**: `503 Service Unavailable`

---

### GET /api/v1/workflows/{ticket_key}

Retrieves the current workflow state for a ticket (for debugging/monitoring).

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `ticket_key` | string | Jira ticket key (e.g., "PROJ-123") |

**Response** (Found):
```json
{
  "ticket_key": "PROJ-123",
  "ticket_type": "FEATURE",
  "current_node": "spec_generation",
  "is_paused": false,
  "retry_count": 0,
  "last_error": null,
  "created_at": "2026-03-30T10:00:00Z",
  "updated_at": "2026-03-30T10:05:00Z"
}
```
- **Status Code**: `200 OK`

**Response** (Not Found):
```json
{
  "status": "error",
  "error": "No workflow found for ticket PROJ-123"
}
```
- **Status Code**: `404 Not Found`

---

## Error Responses

All error responses follow this format:

```json
{
  "status": "error",
  "error": "Human-readable error message",
  "details": {
    "field": "Additional context if available"
  }
}
```

| Status Code | Meaning |
|-------------|---------|
| `400` | Invalid request payload |
| `401` | Authentication failed (invalid webhook signature) |
| `404` | Resource not found |
| `429` | Rate limit exceeded |
| `500` | Internal server error |
| `503` | Service unavailable (dependency failure) |

---

## Rate Limiting

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/webhooks/*` | 1000 requests | per minute |
| `/workflows/*` | 100 requests | per minute |
| `/health` | No limit | - |

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when window resets

---

## Webhook Signature Validation

### Jira Webhooks
Jira webhooks may include `X-Atlassian-Token` header. Validate by comparing against configured secret.

### GitHub Webhooks
GitHub webhooks include `X-Hub-Signature-256` header containing HMAC-SHA256 of payload:
```
X-Hub-Signature-256: sha256=<hex-digest>
```
Validate by computing HMAC of raw body with configured secret and comparing.
