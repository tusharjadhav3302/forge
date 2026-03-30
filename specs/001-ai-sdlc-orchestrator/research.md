# Research: AI-Integrated SDLC Orchestrator

**Feature**: 001-ai-sdlc-orchestrator
**Date**: 2026-03-30

## Technology Decisions

### 1. Orchestration Framework: LangGraph

**Decision**: Use LangGraph (Python) for state machine orchestration

**Rationale**:
- Native support for cyclical graphs (essential for HITL feedback loops)
- Built-in checkpointer for workflow state persistence
- Fan-out/fan-in patterns for concurrent repository execution
- Integrates with LangChain ecosystem for LLM interactions

**Alternatives Considered**:
- **Temporal.io**: More mature, but heavier infrastructure; overkill for initial pilot
- **Prefect/Airflow**: DAG-focused, not ideal for cyclical workflows with pause gates
- **Custom state machine**: Higher maintenance burden; LangGraph provides battle-tested primitives

**Reference**: LLD Section 1 (Technology Stack), ADR 1 (Cyclical State Machine)

---

### 2. Webhook Gateway: FastAPI

**Decision**: Use FastAPI for HTTP webhook ingestion

**Rationale**:
- Async-first design for high-throughput webhook handling
- Sub-500ms response time requirement easily achievable
- Built-in request validation with Pydantic
- Excellent documentation and developer experience

**Alternatives Considered**:
- **Flask**: Synchronous by default; async support less mature
- **Starlette**: Lower-level; FastAPI provides better DX with same performance
- **Go/Rust service**: Overkill for webhook gateway; Python ecosystem preferred for LangGraph integration

**Reference**: LLD Section 7A (API Listener)

---

### 3. Message Broker: Redis Streams

**Decision**: Use Redis Streams for event buffering and FIFO ordering

**Rationale**:
- Already using Redis for LangGraph checkpointer; reduces infrastructure complexity
- Consumer groups provide exactly-once semantics with acknowledgment
- FIFO ordering per ticket achievable with consumer group keying
- Low latency for event delivery

**Alternatives Considered**:
- **RabbitMQ**: More feature-rich but additional infrastructure dependency
- **Kafka**: Overkill for expected event volume; higher operational complexity
- **AWS SQS**: Cloud-specific; Redis works in any environment

**Reference**: LLD Section 7B (Message Broker), ADR 3 (Event-Driven Webhook Ingestion)

---

### 4. State Persistence: LangGraph Redis Checkpointer

**Decision**: Use LangGraph's built-in Redis checkpointer for workflow state

**Rationale**:
- Native integration with LangGraph state management
- Automatic serialization/deserialization of workflow state
- Supports workflow pause/resume across process restarts
- Redis provides distributed locking for concurrent access control

**Alternatives Considered**:
- **PostgreSQL checkpointer**: More durable but higher latency for state operations
- **Custom file-based**: Not suitable for distributed workers
- **SQLite**: Single-node only; doesn't support distributed locking

**Reference**: LLD Section 7D (State & Persistence Layer)

---

### 5. AI Coding Engine: Claude Code (Anthropic SDK)

**Decision**: Use Claude Code via Anthropic Python SDK for code generation

**Rationale**:
- LLD explicitly specifies Claude Code as the coding engine
- Anthropic SDK provides async support for non-blocking operations
- Computer use capabilities for complex workspace interactions
- Best-in-class performance for code generation tasks

**Alternatives Considered**:
- **OpenAI Codex/GPT-4**: Comparable quality but Claude preferred per LLD
- **Local models (CodeLlama)**: Lower quality; not suitable for production code gen
- **GitHub Copilot**: IDE-focused; not suitable for autonomous execution

**Reference**: LLD Section 1 (Coding Engine)

---

### 6. Ephemeral Workspace Management: Python tempfile + GitPython

**Decision**: Use Python tempfile for workspace creation, GitPython for repository operations

**Rationale**:
- tempfile provides secure temporary directory creation with automatic cleanup options
- GitPython provides Pythonic interface to git operations (clone, branch, commit, push)
- No additional infrastructure needed beyond Python stdlib + one dependency
- Workspace destruction guarantees pristine state per constitution

**Alternatives Considered**:
- **Docker containers per workspace**: Higher isolation but slower startup; overkill for initial pilot
- **subprocess git calls**: Lower-level; GitPython provides better error handling
- **dulwich (pure Python git)**: Less mature than GitPython; git CLI dependency acceptable

**Reference**: LLD Section 7E (Ephemeral Execution Workspaces), ADR 7

---

### 7. Jira Integration: REST API + Webhooks

**Decision**: Use Jira REST API v3 for CRUD operations, webhooks for event triggers

**Rationale**:
- Zero-UI architecture requires all artifact storage in Jira
- REST API provides full CRUD for tickets, comments, attachments, custom fields
- Webhooks trigger workflow transitions without polling
- Well-documented API with Python client libraries available

**Implementation Notes**:
- Use `jira` Python package or `httpx` for REST calls
- Configure webhooks in Jira admin for status transitions
- Handle rate limiting with exponential backoff
- Implement freshness check before processing stale events

**Reference**: LLD Section 1, ADR 2 (Zero-UI Architecture)

---

### 8. Observability: Langfuse + Python Logging

**Decision**: Use Langfuse for LLM tracing, Python logging for application telemetry

**Rationale**:
- Langfuse provides LLM-specific tracing (token usage, latency, prompt/completion logging)
- Python logging integrates with standard observability stacks (ELK, CloudWatch, etc.)
- Separation of concerns: LLM traces vs application logs
- Langfuse supports async tracing for non-blocking operation

**Alternatives Considered**:
- **LangSmith**: LangChain ecosystem lock-in; Langfuse more vendor-neutral
- **OpenTelemetry only**: Generic tracing; lacks LLM-specific insights
- **Custom tracing**: Higher maintenance burden

**Reference**: LLD Section 1 (Traceability tool)

---

## Integration Patterns

### Jira Webhook Event Flow

```
Jira Status Change → Webhook POST → FastAPI Gateway → Redis Stream →
Orchestrator Worker → LangGraph Node Execution → Jira API Update
```

### GitHub Webhook Event Flow

```
PR Event (CI status, review, merge) → Webhook POST → FastAPI Gateway →
Redis Stream → Orchestrator Worker → LangGraph Node Execution
```

### Workspace Execution Flow

```
Task Ready → Create tempdir → Clone repo → Read guardrails →
Execute Claude Code → Commit changes → Push branch → Open PR →
Destroy workspace
```

---

## Rate Limiting Strategy

| Service | Limit | Strategy |
|---------|-------|----------|
| Jira REST API | 100 req/min (standard) | Exponential backoff; queue overflow handling |
| GitHub API | 5000 req/hour (authenticated) | Token bucket; batch operations where possible |
| Claude API | Token-per-minute varies | Semaphore-based concurrency control |
| Redis | N/A (self-hosted) | Connection pooling |

---

## Security Considerations

1. **Secrets Management**: Store Jira/GitHub tokens in Vault; inject at runtime
2. **Webhook Validation**: Verify Jira/GitHub webhook signatures
3. **Workspace Isolation**: tempfile directories with restricted permissions
4. **Token Scoping**: Minimum required permissions for each integration
5. **Audit Logging**: Log all state transitions and API calls to external systems

---

## Phased Implementation Alignment

Per LLD Section 5, implementation follows "Crawl, Walk, Run":

| Phase | Scope | This Plan Covers |
|-------|-------|------------------|
| Phase 0 (Week 1) | Exploratory - validate concepts | N/A (manual validation) |
| Phase 1 (Weeks 2-4) | Planning Only - PRD/Spec/Plan generation | User Stories 1-4 |
| Phase 2 (Weeks 4-6) | Single-Repo Execution | User Stories 5-6 |
| Phase 3 (Weeks 7-8) | CI/CD Feedback Loop | User Stories 7-9 |
| Phase 4 (Weeks 9+) | Multi-Repo Concurrency | User Stories 10-11 |

**Initial implementation targets Phase 1-2**, with architecture designed to support Phase 3-4.
