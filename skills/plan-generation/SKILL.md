---
name: plan-generation
description: Use when converting approved specs into implementation plans, designing cross-repo architectural changes, or responding to Tech Lead feedback on plans. Ensures technically sound plans that respect repository constraints and include quality attributes.
---

# Plan Generation Skill

## Purpose

Generate comprehensive, technically sound architectural plans (plan.md) that detail implementation approach across multiple repositories while respecting constitution.md constraints and technical guardrails.

## When to Use

Use this skill when:
- Converting approved specs into implementation plans
- Designing cross-repo architectural changes
- Responding to Tech Lead feedback on plans
- Validating technical feasibility against repository constraints

## Core Principles

### 1. Clarity and Precision
Use unambiguous language. Clearly define technical terms. Reference exact standards and requirements.

### 2. Constitution.md is Law
Repository constitution.md files define guardrails (e.g., "Always use PostgreSQL, never MySQL"). Plans MUST comply. Violations should be impossible.

### 3. Documentation as Code
Plans are living documents that evolve with the system. Include rationale for decisions so future readers understand "why", not just "what".

### 4. Visual First
Each component interaction should have a diagram description. Architecture diagrams are not optional—they're the foundation for understanding.

### 5. Quality Attributes Matter
Non-functional requirements (scalability, reliability, security, testability) are as important as functional requirements.

## Plan Template Structure

```markdown
# [Story Title] - Implementation Plan

## Overview

### Context
[What problem does this solve? Why now?]

### Scope
[What's in scope? What's explicitly out of scope?]

### Success Criteria
[How do we know this is done and works?]

---

## Architectural Approach

### High-Level Design
[Text description of the approach]

### Architecture Diagram
[Describe diagram showing: components, data flow, integration points]

```
[Component A] --request--> [Component B]
                              |
                              v
                         [Database]
```

### Components

#### Component 1: [Name]
- **Purpose**: [What does it do?]
- **Technology**: [Stack/framework]
- **Interfaces**: [APIs, events, dependencies]
- **Responsibilities**: [Single responsibility principle]

#### Component 2: [Name]
[Repeat pattern]

---

## Affected Repositories

### Repository: [repo-name]

**Constitution.md Constraints:**
- [List constraints from constitution.md]
- [e.g., "Must use PostgreSQL for persistence"]
- [e.g., "All API endpoints must use JWT authentication"]

**Changes Required:**
- **Files to modify**: `path/to/file.py`, `path/to/config.yaml`
- **New files**: `path/to/new_module.py`
- **Dependencies**: Add `redis==5.0.0`, `celery==5.3.0`

**Why These Changes:**
[Rationale for decisions in this repo]

### Repository: [another-repo]
[Repeat pattern for each affected repo]

---

## Implementation Steps

### Phase 1: [Foundation/Setup]
1. [Concrete step with acceptance criteria]
2. [Another step]

**Acceptance**: [How do we verify this phase is complete?]

### Phase 2: [Core Implementation]
1. [Concrete step]
2. [Another step]

**Acceptance**: [Verification criteria]

### Phase 3: [Integration/Polish]
1. [Final steps]

**Acceptance**: [Done criteria]

---

## Data Model Changes

### New Tables/Collections

#### Table: `webhook_events`
```sql
CREATE TABLE webhook_events (
    id UUID PRIMARY KEY,
    ticket_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    INDEX idx_ticket_id (ticket_id)
);
```

**Rationale**: [Why this schema?]

### Schema Migrations
- Migration file: `migrations/2026_03_25_add_webhook_events.sql`
- Rollback plan: [How to undo if needed]

---

## Integration Points

### External Systems

#### Jira (via MCP)
- **Direction**: Bidirectional
- **Operations**: get_issue, update_issue, create_issue
- **Error Handling**: Exponential backoff, max 3 retries
- **Rate Limits**: 100 req/min per API key

#### Redis
- **Purpose**: Message broker, state persistence, locks, cache
- **Databases**:
  - DB 0: task queue broker
  - DB 1: Distributed locks
  - DB 2: Deduplication cache
  - DB 3: workflow engine state
- **Failure Mode**: If unavailable, queue operations fail, workers stop processing

### Internal APIs
[Describe any new internal APIs]

---

## Testing Strategy

### Unit Tests
- **Coverage Target**: 80% code coverage
- **Key Areas**:
  - [ ] Webhook validation logic
  - [ ] Deduplication logic
  - [ ] Lock acquisition/release

### Integration Tests
- **Scenarios**:
  - [ ] End-to-end: Webhook → Queue → Worker → Jira update
  - [ ] Failure: Redis unavailable, Jira rate limit hit
  - [ ] Race condition: Multiple rapid webhooks for same ticket

### Performance Tests
- **Load**: 100 webhooks/sec sustained for 5 minutes
- **Success Criteria**: <100ms p95 response time, 0% dropped events

---

## Quality Attributes

### Scalability
- **Current**: Single instance handles 100 req/sec
- **Future**: Horizontal scaling (multiple web framework + task queue workers)
- **Bottleneck**: Redis (can scale to cluster if needed)

### Reliability
- **Availability Target**: 99.9% uptime (shadow mode, production will be 99.99%)
- **Data Durability**: Redis persistence enabled (AOF + RDB)
- **Failure Recovery**: task queue tasks retried 3x, then DLQ

### Security
- **Authentication**: HMAC signature validation on webhooks
- **Secrets Management**: Environment variables (migrate to Vault in Phase 2)
- **Data Sanitization**: Strip PII from logs

### Observability
- **Metrics**: Prometheus (webhook_requests_total, errors, latency)
- **Logs**: Structured JSON logs with trace_id
- **Tracing**: LangFuse for LLM calls, OpenTelemetry for services

---

## Dependencies

### New Dependencies
- `fastapi==0.110.0` - Web framework
- `celery==5.3.0` - Task queue
- `redis==5.0.0` - Message broker, cache, locks
- `langgraph-checkpoint-redis==0.3.2` - State persistence

### Infrastructure
- Redis 7.0+ instance (standalone for Phase 1, cluster for production)
- Python 3.11+ runtime
- 2GB RAM, 2 CPU cores (minimum)

---

## Risks and Mitigations

### Risk 1: Redis as Single Point of Failure
- **Impact**: High (entire system stops if Redis down)
- **Likelihood**: Low (Redis is very stable)
- **Mitigation**: Redis persistence enabled, monitoring/alerting, documented recovery procedure

### Risk 2: Jira API Rate Limits
- **Impact**: Medium (workflow delays)
- **Likelihood**: Medium (depends on usage)
- **Mitigation**: Exponential backoff in MCP, request batching, rate limit monitoring

### Risk 3: Constitution.md Changes Breaking Plan
- **Impact**: Low (rarely changes)
- **Likelihood**: Low
- **Mitigation**: Re-validate plan when constitution.md updates detected

---

## Rollback Plan

If deployment fails:
1. Stop task queue workers
2. Revert web framework deployment to previous version
3. Drain Redis queues or flush affected databases
4. Verify no in-flight tasks remain
5. Monitor Jira for any inconsistent states

**Time to Rollback**: <15 minutes

---

## Open Questions

- [ ] Should we use Redis Cluster or Sentinel for HA in Phase 2?
- [ ] What's the long-term strategy for task queue task result storage?
- [ ] Do we need a separate Redis instance for production vs staging?

---

## References

- Constitution.md: [Link to repo constitution]
- Related Tickets: TICKET-ID, TICKET-ID, TICKET-ID
- External Docs: [Workflow State Persistence Documentation]
```

## Generation Process

### Step 1: Gather Context

1. **Read the spec.md** from the Story (approved Given/When/Then)
2. **Fetch constitution.md** from affected repos via 
3. **Review System Catalog** to understand existing architecture
4. **Read related plans** from similar Stories for consistency

### Step 2: Identify Affected Repositories

Based on spec requirements, determine:
- Which repos need changes
- What type of changes (new features, bug fixes, refactoring)
- Dependencies between repos

### Step 3: Apply Constitution.md Constraints

For each affected repo:
1. Load constitution.md rules
2. Verify plan complies (e.g., if it says "PostgreSQL only", don't plan MySQL)
3. Document which rules apply to this plan
4. If conflict found, flag it immediately (don't proceed with invalid plan)

### Step 4: Design Components

For each component:
1. Define purpose (single responsibility)
2. Specify technology stack (must align with constitution.md)
3. Describe interfaces (APIs, events, data contracts)
4. Document interactions (with diagrams)

### Step 5: Plan Implementation Steps

Break work into phases:
- **Phase 1**: Foundation (setup, scaffolding, infrastructure)
- **Phase 2**: Core implementation (business logic)
- **Phase 3**: Integration and polish (testing, monitoring, docs)

Each phase has clear acceptance criteria.

### Step 6: Define Quality Attributes

Document non-functional requirements:
- Scalability: How does it scale? What are bottlenecks?
- Reliability: Uptime targets, failure recovery
- Security: Authentication, authorization, data protection
- Observability: Metrics, logs, tracing

### Step 7: Assess Risks

Identify top 3-5 risks:
- What could go wrong?
- How likely? How bad?
- How to mitigate?

### Step 8: Document Rollback Plan

If this goes wrong in production, how do we undo it quickly?

## Quality Checklist

Before finalizing a plan, verify:

- [ ] **Constitution.md compliance**: All constraints from affected repos are satisfied
- [ ] **Rationale documented**: Why decisions were made, not just what
- [ ] **Visual elements**: Architecture diagram described clearly
- [ ] **Quality attributes**: Scalability, reliability, security, observability addressed
- [ ] **Testable**: Clear testing strategy with success criteria
- [ ] **Implementation steps**: Concrete, actionable phases with acceptance criteria
- [ ] **Dependencies explicit**: All new libraries, services, infrastructure listed
- [ ] **Risks identified**: Top risks with mitigations
- [ ] **Rollback plan**: How to undo if deployment fails
- [ ] **No ambiguity**: Precise language, defined terms

## Examples

### Good Plan Example: Redis-Based State Persistence

```markdown
## Affected Repositories

### Repository: your project

**Constitution.md Constraints:**
- Must use Redis for distributed state (not file-based storage)
- All secrets via environment variables (no hardcoded credentials)
- Python 3.11+ required

**Changes Required:**
- **Files to modify**: `orchestrator/config.py`, `orchestrator/graph.py`
- **New files**: `orchestrator/checkpointer.py`
- **Dependencies**: Add `langgraph-checkpoint-redis==0.3.2`

**Why These Changes:**
Replace SqliteSaver with RedisSaver to enable multi-worker state sharing. Redis already in use for message broker, so this consolidates infrastructure.

## Implementation Steps

### Phase 1: Redis Checkpointer Setup
1. Install `langgraph-checkpoint-redis` dependency
2. Configure RedisSaver connection string (env var: REDIS_STATE_URI)
3. Run checkpointer setup: `RedisSaver.from_conn_string(uri).setup()`
4. Test: Verify persistent storage contains `langgraph:` prefixed keys

**Acceptance**: Can create checkpoint, retrieve it, and update state

### Phase 2: Integrate with workflow engine
1. Replace SqliteSaver with RedisSaver in graph compilation
2. Update thread_id routing to use ticket_id consistently
3. Add error handling for Redis connection failures

**Acceptance**: Workflow pauses at gate, resumes on webhook with same thread_id
```

**Why This is Good:**
- Constitution.md rules explicitly listed and followed
- Rationale explains *why* Redis over SQLite
- Concrete steps with measurable acceptance criteria
- Links to existing infrastructure (Redis already in use)

### Bad Plan Example (Anti-Pattern)

```markdown
## Implementation

We'll use the best database for this. The system will be scalable and reliable. Implementation will happen in multiple phases.

[Problems: No specifics, doesn't reference constitution.md, no rationale, vague acceptance criteria]
```

## Handling Feedback

When Tech Lead requests plan changes:

1. **Read all comments** - Fetch current ticket state from Jira
2. **Identify conflicts** - Does feedback conflict with constitution.md? Raise immediately
3. **Update specific sections** - Don't regenerate entire plan, modify relevant parts
4. **Re-validate** - Run through quality checklist
5. **Document changes** - Add version/revision notes

### Example Feedback Loop

**Feedback**: "Reuse existing accounts table instead of creating new users table"

**Response**:
1. Update "Data Model Changes" section to remove new `users` table
2. Add "Integration Points" entry for existing `accounts` service
3. Update "Implementation Steps" to include integration with accounts API
4. Re-check constitution.md: Does existing accounts service align with constraints?

## Common Pitfalls to Avoid

1. **Ignoring constitution.md**
   - ❌ "We'll use MySQL for this"
   - ✅ Check constitution.md first: "Must use PostgreSQL" → plan PostgreSQL

2. **No rationale**
   - ❌ "We'll use Redis"
   - ✅ "We'll use Redis because [existing infrastructure, atomic operations needed, state sharing across workers]"

3. **Vague implementation steps**
   - ❌ "Implement the feature"
   - ✅ "Add web framework endpoint POST /webhooks/jira with HMAC validation (line 45-67 in webhook.py)"

4. **Missing quality attributes**
   - ❌ Plan only describes functional changes
   - ✅ Plan includes scalability analysis, security review, observability strategy

5. **No rollback plan**
   - ❌ Assume deployment will succeed
   - ✅ Document exact steps to undo changes if deployment fails

When generating plans in :
## Constitution.md Integration

### Loading Constitution Rules

```python
# Pseudo-code for constitution.md loading
def load_constitution(repo_name: str) -> dict:
    """Fetch constitution.md from repo root"""
    content = github_api.get_file(repo_name, "constitution.md")
    return parse_constitution(content)

def validate_plan_against_constitution(plan: str, constitution: dict) -> list[str]:
    """Return list of violations"""
    violations = []

    # Example rule: "Must use PostgreSQL"
    if "postgresql" in constitution.required_tech:
        if "mysql" in plan.lower() or "mongodb" in plan.lower():
            violations.append("Plan violates constitution: Must use PostgreSQL, not MySQL/MongoDB")

    # Example rule: "No direct database access from API layer"
    if "no_direct_db_access" in constitution.patterns:
        if "api" in plan and "db.query" in plan:
            violations.append("Plan violates constitution: API must use service layer, not direct DB")

    return violations
```

### Handling Violations

If constitution.md violations detected:
1. **Do not proceed** - Invalid plans should not be created
2. **Report to Tech Lead** - Transition to "In Design" with comment explaining violation
3. **Suggest alternatives** - Propose constitution-compliant approaches

## References

- Stack Overflow Technical Specs Guide: https://stackoverflow.blog/2020/04/06/a-practical-guide-to-writing-technical-specs/
- Architecture Documentation Best Practices: https://www.ciopages.com/best-practices-for-technical-architecture-documentation/
- Software Architecture Documentation Guide: https://document360.com/blog/software-architecture-documentation/
