# Drift Resolution Proposals

Generated: 2026-04-05T17:15:00Z
Based on: drift-report from 2026-04-05T17:00:00Z

## Summary

| Resolution Type | Count | Status |
|-----------------|-------|--------|
| Backfill (Code → Spec) | 4 | APPROVED |
| Align (Spec → Code) | 7 | APPROVED |
| New Specs | 3 | APPROVED |

## Approved Proposals

### Proposal 1: FR-001 (HTTP Response Code)

**Direction**: BACKFILL
**Status**: APPROVED

**Spec Change**:
```diff
- FR-001: System MUST receive webhooks from Jira and acknowledge with HTTP 200 within 500ms
+ FR-001: System MUST receive webhooks from Jira and acknowledge with HTTP 202 (Accepted) within 500ms
```

**Rationale**: HTTP 202 is semantically correct for async processing per RFC 7231.

---

### Proposal 2: FR-017 (Workflow State Tracking)

**Direction**: BACKFILL
**Status**: APPROVED

**Spec Change**:
```diff
- FR-017: System MUST transition Jira tickets through workflow states as phases complete
+ FR-017: System MUST track workflow progress using forge: labels on Jira tickets.
+         Labels indicate current phase (e.g., forge:prd-pending, forge:spec-approved).
+         This approach enables workflow visibility without requiring custom Jira
+         workflow configurations in each target project.
```

**Rationale**: Label-based approach works across any Jira project without admin configuration.

---

### Proposal 3: FR-019 (Concurrent Execution Limit)

**Direction**: BACKFILL
**Status**: APPROVED

**Spec Change**:
```diff
- FR-019: System MUST support concurrent execution across multiple repositories
+ FR-019: System MUST support concurrent execution across multiple repositories,
+         with a default limit of 5 concurrent repository workspaces to manage
+         resource consumption. This limit is configurable.
```

**Rationale**: Unbounded concurrency would exhaust system resources.

---

### Proposal 4: SC-005 (Response Time SLA)

**Direction**: BACKFILL
**Status**: APPROVED

**Spec Change**:
```diff
- SC-005: Webhook acknowledgment occurs within 500ms for 99% of events
+ SC-005: Webhook endpoints SHOULD respond promptly. Response time 
+         monitoring is available via the /metrics endpoint.
```

**Rationale**: Removes hard SLA without monitoring infrastructure in place.

---

### Proposal 5: US9-check-epic-completion

**Direction**: ALIGN (Code Change Required)
**Status**: APPROVED

**Location**: `src/forge/orchestrator/nodes/human_review.py:241-253`

**Code Change**:
```python
async def _check_epic_completion(jira: JiraClient, epic_key: str) -> bool:
    """Check if all Tasks under an Epic are done."""
    # Query Jira for child issues (Tasks) of this Epic
    jql = f'"Parent Link" = {epic_key} AND issuetype = Task'
    tasks = await jira.search_issues(jql)
    
    if not tasks:
        return True  # No tasks means nothing to complete
    
    # Check if all tasks are in Done/Closed status
    done_statuses = {"Done", "Closed", "Resolved"}
    return all(task.status in done_statuses for task in tasks)
```

**Estimated Effort**: ~1 hour

---

### Proposal 6: Edge Cases Implementation

**Direction**: ALIGN (Code Changes Required)
**Status**: APPROVED

**Implementation Tasks**:

1. **Rate Limit Handling**
   - Add exponential backoff to JiraClient
   - Detect 429 responses and retry
   - Location: `src/forge/integrations/jira/client.py`

2. **Webhook Retry/Dead-Letter**
   - Add failed event persistence
   - Implement retry queue with backoff
   - Location: `src/forge/queue/`

3. **Branch Conflict Detection**
   - Check for remote changes before push
   - Escalate conflicts to human review
   - Location: `src/forge/workspace/git_ops.py`

4. **Interrupted Execution Recovery**
   - Verify checkpointer handles mid-task restart
   - Add recovery documentation
   - Location: `src/forge/orchestrator/checkpointer.py`

5. **Guardrails Validation**
   - Add explicit warning when missing
   - Optionally block execution without guardrails
   - Location: `src/forge/workspace/guardrails.py`

6. **Merge Conflict Detection**
   - Detect conflicts before PR creation
   - Escalate to blocked status with instructions
   - Location: `src/forge/orchestrator/nodes/pr_creation.py`

**Estimated Effort**: ~2-3 days total

---

### Proposal 7: NEW SPEC - Observability (US12)

**Direction**: NEW_SPEC
**Status**: APPROVED

**Add to spec**:
```markdown
### User Story 12 - Observability and Tracing (Priority: P3)

Engineers can observe AI agent execution through distributed tracing. 
Each workflow execution is traced with spans for LLM calls, tool usage, 
and state transitions, enabling debugging and performance analysis.

**Acceptance Scenarios**:

1. **Given** a workflow execution, **When** it completes, **Then** a trace 
   is available in Langfuse showing all LLM calls with inputs/outputs.
2. **Given** a failed workflow, **When** an engineer investigates, **Then** 
   the trace shows the exact step and error that caused failure.
3. **Given** multiple concurrent workflows, **When** viewing traces, **Then** 
   each workflow has a distinct trace ID correlating all its operations.

## Requirements

- **FR-021**: System MUST emit traces to Langfuse for all AI agent operations
- **FR-022**: Each trace MUST include: workflow ID, ticket key, LLM model, 
              token usage, and latency
- **FR-023**: Traces MUST be queryable by ticket key for debugging
```

---

### Proposal 8: NEW SPEC - Metrics (US13)

**Direction**: NEW_SPEC
**Status**: APPROVED

**Add to spec**:
```markdown
### User Story 13 - System Metrics (Priority: P3)

Operations teams can monitor system health through a metrics endpoint 
compatible with Prometheus scraping. Metrics include workflow counts, 
queue depths, and processing latencies.

**Acceptance Scenarios**:

1. **Given** the system is running, **When** Prometheus scrapes `/metrics`, 
   **Then** it receives metrics in OpenMetrics format.
2. **Given** workflows are processing, **When** viewing metrics, **Then** 
   counters show workflows by status (pending, active, completed, failed).
3. **Given** the Redis queue has items, **When** viewing metrics, **Then** 
   queue depth gauges reflect current backlog per stream.

## Requirements

- **FR-024**: System MUST expose a `/api/v1/metrics` endpoint in Prometheus format
- **FR-025**: Metrics MUST include: workflow_total (by status), queue_depth 
              (by stream), webhook_latency_seconds (histogram)

## Success Criteria

- **SC-013**: Metrics endpoint SHOULD respond promptly and not impact 
              application performance under normal operation
```

---

### Proposal 9: NEW SPEC - CLI (US14)

**Direction**: NEW_SPEC
**Status**: APPROVED

**Add to spec**:
```markdown
### User Story 14 - Command Line Interface (Priority: P3)

Developers can interact with forge via CLI for local development, 
debugging, and manual workflow operations without requiring the 
full server deployment.

**Acceptance Scenarios**:

1. **Given** forge is installed, **When** running `forge --help`, **Then** 
   available commands and options are displayed.
2. **Given** a ticket key, **When** running `forge status <TICKET>`, **Then** 
   the current workflow state and progress is shown.
3. **Given** a stalled workflow, **When** running `forge resume <TICKET>`, 
   **Then** the workflow continues from its last checkpoint.
4. **Given** a completed workflow, **When** running `forge reset <TICKET>`, 
   **Then** the checkpoint is cleared for re-processing.

## Requirements

- **FR-026**: System MUST provide a CLI entry point via `forge` command
- **FR-027**: CLI MUST support: status, resume, reset, and worker subcommands
- **FR-028**: CLI MUST read configuration from environment variables and 
              .env files consistent with server deployment
```

---

## Next Steps

1. **Apply Spec Changes**: Run `/speckit.sync.apply --backfill` to update spec file
2. **Create Code Tasks**: Run `/speckit.sync.apply --align` to generate implementation tasks
3. **Review Changes**: Commit spec updates and code changes separately
