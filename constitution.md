# Forge Orchestrator - Constitution

This document defines the technical constraints, patterns, and architectural decisions for the Forge orchestrator project. All code contributions must comply with these rules.

**Version**: 1.0
**Last Updated**: 2026-03-26
**Status**: Active

---

## Core Principles

### Architecture

1. **Stateless Components**: API Gateway and Celery Workers must be stateless
2. **Single Source of Truth**: Jira is the authoritative source for ticket data (never cache)
3. **State Managed by Checkpointer**: LangGraph checkpointer handles all workflow state persistence
4. **Declarative Routing**: Workflow routing via LangGraph conditional edges, not imperative code
5. **Fast Acknowledgment**: Webhook responses < 100ms (background processing for heavy work)

### Responsibilities

- **API Gateway**: Validate, deduplicate, queue ticket_id (NO business logic)
- **Celery Worker**: Fetch fresh data from Jira, invoke workflow (NO state management)
- **LangGraph Workflow**: Load state, route, execute nodes, save state (ALL workflow logic)
- **Redis Checkpointer**: Automatic state persistence and recovery

---

## Technology Mandates

### Core Stack

- **Python**: 3.11 or higher (required)
- **Web Framework**: FastAPI 0.110+
- **Task Queue**: Celery 5.3+ with Redis broker
- **State Management**: Redis 7.0+ with persistence (AOF + RDB)
- **Workflow Engine**: LangGraph 0.2+ with RedisSaver checkpointer
- **LLM**: Claude API via Anthropic SDK (claude-sonnet-4 or newer)

### Data Storage

- **Redis only**: No SQL databases in Phase 1
- **No file-based state**: Always use Redis for distributed systems
- **Database separation**: Dedicated Redis DB per use case (broker, locks, dedup, state)

### Dependencies

- **All dependencies** pinned in `pyproject.toml`
- **Security updates** via Dependabot (if available)
- **No GPL-licensed dependencies** (MIT, Apache 2.0, BSD only)

---

## Forbidden Patterns

### Architecture

- ❌ **No synchronous blocking calls in async routes**
- ❌ **No file-based state persistence**
- ❌ **No hardcoded credentials** (env vars or secrets manager only)
- ❌ **No SQL databases** in Phase 1
- ❌ **No direct Jira API calls** (use Jira MCP only)
- ❌ **No caching of Jira ticket data** (always fetch current state)
- ❌ **No imperative routing logic in workers** (use LangGraph conditional edges)

### Code Quality

- ❌ **No print() statements** (use structlog)
- ❌ **No bare except clauses** (specify exception types)
- ❌ **No mutable default arguments**
- ❌ **No string concatenation for paths** (use pathlib)
- ❌ **No f-strings in logging** (use lazy evaluation)

### Security

- ❌ **No secrets in code**
- ❌ **No PII in logs**
- ❌ **No unauthenticated endpoints** (except /health and /metrics)
- ❌ **No HMAC signature bypass**

---

## Security Requirements

### Authentication

- **Webhook HMAC validation**: All Jira webhooks must validate HMAC signature
- **API authentication**: Phase 2 requirement
- **Secrets management**: Environment variables (Phase 1), Vault (Phase 2)

### Data Protection

- **No PII in logs**: Sanitize ticket descriptions, comments, user emails
- **Audit logging**: All Jira operations logged with ticket_id
- **Redis security**: Use Redis AUTH in production

### Input Validation

- **All webhook payloads**: Validate using Pydantic schemas
- **HMAC verification**: Reject invalid/missing signatures
- **Rate limiting**: Phase 2 requirement

---

## Testing Requirements

### Coverage

- **Minimum 80% code coverage** for core modules
- **60% acceptable** for API routes (integration tests preferred)
- **100% required** for critical paths (HMAC, state management, routing)

### Test Organization

- **Unit tests**: `tests/unit/` - isolated function/class tests
- **Integration tests**: `tests/integration/` - component interaction tests
- **Fixtures**: Reusable fixtures in `tests/conftest.py`

### Test Frameworks

- **pytest**: Primary test framework
- **pytest-asyncio**: Async tests
- **pytest-mock**: Mocking external services
- **fakeredis**: Redis mocking in unit tests

---

## Code Organization

### Module Responsibilities

- **api/**: FastAPI application (endpoints, middleware) - NO business logic
- **workers/**: Celery workers (fetch data, invoke workflow) - NO state management
- **nodes/**: LangGraph nodes (workflow logic, Jira updates)
- **core/**: Core services (config, logging, clients, workflow definition)
- **prompts/**: LLM prompt templates
- **schemas/**: Pydantic models (validation, serialization)

### Naming Conventions

- **Python modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`

---

## API Design Standards

### FastAPI Routes

- **Async handlers**: All route handlers must be async
- **Pydantic validation**: Use Pydantic models for request/response
- **Dependency injection**: Use FastAPI `Depends()`
- **Error handling**: Raise `HTTPException` with appropriate status codes
- **Fast response**: < 100ms to acknowledge webhook

### HTTP Status Codes (Jira Webhooks)

- `200 OK`: Successful processing (Jira won't retry)
- `400 Bad Request`: Invalid payload/signature (Jira won't retry)
- `500 Internal Server Error`: Temporary error (Jira may retry)

**Note**: Jira only checks HTTP status code, not response body

---

## Workflow Standards

### LangGraph Nodes

- **Stateless functions**: Nodes don't maintain internal state
- **Idempotent**: Same input produces same result
- **State updates**: Modify WorkflowState, return updated state
- **Error handling**: Catch exceptions, update state.error_count, raise for retry

### State Management

- **Thread ID format**: `ticket_{ticket_id}`
- **State schema**: Use `WorkflowState` Pydantic model
- **Checkpointer handles all state**: Load, merge, save automatic
- **Worker provides minimal input**: Only fresh Jira data (ticket_id, current_status, feedback)

### Routing

- **Conditional edges**: Route based on `state.current_status`
- **Declarative**: Defined in workflow graph, not worker code
- **Feedback loops**: Backward status transitions trigger regeneration

---

## Celery Task Standards

### Task Configuration

- **Max retries**: 3 attempts with exponential backoff (1s, 2s, 4s)
- **Timeout**: 5 minutes per task
- **Serialization**: JSON only (no pickle)
- **Result backend**: Redis

### Task Responsibilities

- **Fetch current ticket** from Jira (always fresh, never cached)
- **Invoke workflow** with minimal input
- **Acquire/release lock** per ticket_id
- **Handle errors** (retry transient, DLQ permanent)

### Error Handling

- **Transient errors**: Retry (network timeout, rate limit)
- **Permanent errors**: Fail fast, send to DLQ
- **Dead Letter Queue**: `dlq:workflow_failures` Redis list

---

## Logging Standards

### Structured Logging

- **Library**: structlog for JSON logs
- **Log level**: INFO in production, DEBUG in development
- **Format**: JSON in production, colored console in development

### Required Log Fields

```python
logger.info(
    "event_name",
    ticket_id="Forge-123",
    node="node_1_ideation_agent",
    duration_ms=2340,
    status="success"
)
```

### What to Log

- ✅ Webhook events (received, validated, queued)
- ✅ Node execution (start, end, duration)
- ✅ State transitions
- ✅ Errors (with sanitized context)
- ❌ Full Jira payloads
- ❌ Secrets or tokens
- ❌ PII (email, names)

---

## Redis Database Allocation

- **DB 0**: Celery broker and result backend
- **DB 1**: Distributed locks (Redlock)
- **DB 2**: Webhook deduplication cache (5-minute TTL)
- **DB 3**: LangGraph state persistence (RedisSaver)

**Never mix databases** - each use case has dedicated DB number

---

## Jira Integration Standards

### MCP Tools Only

- **Always use Jira MCP tools**: `mcp__atlassian__jira_*`
- **Never call Jira REST API directly**
- **Always fetch current state**: No caching

### Ticket Operations

- **Fetch**: Always get current state before processing
- **Create**: Always set parent field for hierarchy
- **Update**: Convert Markdown to Jira markup
- **Comments**: Filter bot comments when reading feedback

---

## Prompt Engineering Standards

### Prompt Templates

- **Location**: `src/aisos/prompts/`
- **Format**: LangChain `ChatPromptTemplate`
- **Versioning**: Track in Git, tag major changes
- **Few-shot examples**: Include 2-3 real examples

### LLM Configuration

- **Model**: Claude Sonnet 4 (default), configurable via env var
- **Temperature**: 0.7 for generation tasks
- **Max tokens**: 4096 for PRD/spec/plan generation

---

## Monitoring & Observability

### Metrics (Prometheus)

Required metrics:
- `webhook_requests_total{status, event_type}`
- `webhook_errors_total{error_type}`
- `workflow_duration_seconds{node}` (histogram)
- `celery_tasks_total{status, task_name}`

### Health Checks

- **Endpoint**: `GET /health`
- **Check**: Redis connectivity
- **Response**: `{"status": "healthy", "redis": "connected"}`

---

## Performance Requirements

### Response Times

- **Webhook acknowledgment**: < 100ms p95
- **PRD generation**: < 30 seconds
- **Epic generation**: < 20 seconds
- **Spec generation**: < 45 seconds per Epic
- **Plan generation**: < 60 seconds

### Throughput

- **Webhook gateway**: 100 requests/sec sustained
- **Availability**: 99.9% uptime (Phase 1 shadow mode)

---

## Development Standards

### Commit Messages

```
<type>: <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

### Code Review

- **Required**: All code reviewed before merge
- **Checklist**: Constitution compliance, test coverage, security
- **Automated checks**: Ruff, MyPy, pytest

---

## Versioning

- **Breaking changes**: Major version bump (1.0.0 → 2.0.0)
- **New features**: Minor version bump (1.0.0 → 1.1.0)
- **Bug fixes**: Patch version bump (1.0.0 → 1.0.1)

---

## Questions & Updates

- **Questions**: GitHub Issues with label `constitution-question`
- **Discussions**: Slack #aisos-orchestrator
- **Propose changes**: PR to this file

---

## Changelog

### Version 1.0 (2026-03-26)
- Initial constitution for Phase 1 (Planning-Only Shadow Mode)
- Defined technology stack, forbidden patterns, security requirements
- Established principles: stateless components, checkpointer state management
- Code organization, testing, and logging standards
