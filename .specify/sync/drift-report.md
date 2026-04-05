# Spec Drift Report

Generated: 2026-04-05T17:00:00Z
Project: forge (AI-Integrated SDLC Orchestrator)

## Summary

| Category | Count |
|----------|-------|
| Specs Analyzed | 1 |
| Requirements Checked | 43 |
| Aligned | 37 (86%) |
| Drifted | 4 (9%) |
| Not Implemented | 2 (5%) |
| Unspecced Code | 3 |

## Detailed Findings

### Spec: 001-ai-sdlc-orchestrator - AI-Integrated SDLC Orchestrator

#### Aligned

**User Stories (11/11 Implemented)**
- US1: PRD Generation from Raw Requirements -> `src/forge/orchestrator/nodes/prd_generation.py`
- US2: Specification Generation -> `src/forge/orchestrator/nodes/spec_generation.py`
- US3: Epic Decomposition and Planning -> `src/forge/orchestrator/nodes/epic_decomposition.py`
- US4: Task Generation -> `src/forge/orchestrator/nodes/task_generation.py`
- US5: Webhook Event Processing -> `src/forge/api/routes/jira.py`, `src/forge/queue/consumer.py`
- US6: Single Repository Code Execution -> `src/forge/orchestrator/nodes/workspace_setup.py`, `implementation.py`
- US7: CI/CD Validation and Autonomous Fix Loop -> `src/forge/orchestrator/nodes/ci_evaluator.py`
- US8: AI Code Review -> `src/forge/orchestrator/nodes/ai_reviewer.py`
- US9: Human Code Review and Merge -> `src/forge/orchestrator/nodes/human_review.py`
- US10: Multi-Repository Concurrent Execution -> `src/forge/orchestrator/nodes/task_router.py`
- US11: Bug Fixing Workflow -> `src/forge/orchestrator/nodes/bug_workflow.py`

**Functional Requirements (17/20 Fully Aligned)**
- FR-002: Sequential FIFO processing per ticket -> `consumer.py:50` (ticket_locks)
- FR-003: Webhook deduplication -> `src/forge/api/middleware/deduplication.py`
- FR-004: Freshness checking before processing -> `consumer.py:83` (_check_freshness)
- FR-005: PRD generation from raw requirements -> `prd_generation.py`
- FR-006: Store artifacts in Jira fields -> description, comments, attachments supported
- FR-007: Human feedback loops -> regenerate_* functions in all generation nodes
- FR-008: Create Epics immediately on Planning -> `epic_decomposition.py:107`
- FR-009: Two-level feedback (Feature/Epic) -> `regenerate_all_epics`, `update_single_epic`
- FR-010: Task repository labels -> `task_generation.py:112`
- FR-011: Ephemeral workspaces -> `src/forge/workspace/manager.py`
- FR-012: Read guardrails (constitution.md/agents.md) -> `src/forge/workspace/guardrails.py`
- FR-013: Group by repo, one PR per repo -> `task_router.py`, `pr_creation.py`
- FR-014: Autonomous CI fixes with retry limit -> `ci_evaluator.py:135`
- FR-015: Escalate on retry exhaustion -> `ci_evaluator.py:232`
- FR-016: AI code review for quality/security/spec -> `ai_reviewer.py`
- FR-018: Modular workflow routing by issue type -> `graph.py:72` (route_by_ticket_type)
- FR-020: Workflow state persistence -> `src/forge/orchestrator/checkpointer.py` (SQLite)

#### Drifted

**FR-001: Webhook HTTP Response Code**
- Spec says: "System MUST receive webhooks from Jira and acknowledge with HTTP 200 within 500ms"
- Code does: Returns HTTP 202 (Accepted) at `jira.py:23`
- Location: `src/forge/api/routes/jira.py:23-25`
- Severity: **minor**
- Note: HTTP 202 is semantically more correct for async processing, but differs from spec

**FR-017: Jira Status Transitions vs Labels**
- Spec says: "System MUST transition Jira tickets through workflow states as phases complete"
- Code does: Uses `ForgeLabel` labels instead of Jira workflow status transitions
- Location: `src/forge/models/workflow.py`, all orchestrator nodes
- Severity: **moderate**
- Note: Design decision - labels provide visibility without requiring custom Jira workflows, but behavior differs from spec expectation of status transitions

**FR-019: Concurrent Execution Limit**
- Spec says: "System MUST support concurrent execution across multiple repositories"
- Code does: Implements but limits to MAX_CONCURRENT_REPOS = 5
- Location: `src/forge/orchestrator/nodes/task_router.py:16`
- Severity: **minor**
- Note: Limit not specified in spec; 5 is a reasonable default but undocumented

**SC-005: Response Time Not Enforced**
- Spec says: "Webhook acknowledgment occurs within 500ms for 99% of events"
- Code does: No explicit timing measurement or enforcement
- Location: N/A (architectural concern)
- Severity: **minor**
- Note: Code structure supports fast response but no benchmarks or monitoring

#### Not Implemented

**Edge Case: Epic Completion Check (Placeholder)**
- Spec Scenario US9.3: "All Tasks for an Epic are Done -> Epic transitions to Done"
- Code: `_check_epic_completion` always returns True (placeholder)
- Location: `src/forge/orchestrator/nodes/human_review.py:241-253`
- Note: Would query Jira for child issues in production

**Edge Cases from Spec (6 items not handled)**
The following edge cases listed in the spec have no explicit handling:
1. Jira API rate limits during bulk Epic/Task creation
2. Webhook drops due to network issues
3. Engineer manually pushing commits to AI branch
4. Recovery from interrupted execution (mid-task restart)
5. Missing constitution.md/agents.md (warning only, no block)
6. Merge conflicts from simultaneous AI completions

### Unspecced Code

| Feature | Location | Lines | Suggested Spec |
|---------|----------|-------|----------------|
| Langfuse Tracing Integration | `src/forge/integrations/langfuse/` | ~200 | Add observability section to spec |
| Metrics Endpoint | `src/forge/api/routes/metrics.py` | ~50 | Document monitoring capabilities |
| CLI Interface | `src/forge/cli.py` | ~100 | Add CLI usage to spec |

## Inter-Spec Conflicts

None identified.

## Test Coverage Analysis

**Well-Covered Areas:**
- `tests/unit/orchestrator/` - State, graph, gates tests
- `tests/unit/api/routes/` - Webhook endpoint tests
- `tests/flows/` - Status transition flow tests

**Empty Test Modules (stubs only):**
- `tests/integration/jira/`
- `tests/integration/github/`
- `tests/integration/agents/`
- `tests/unit/workspace/`
- `tests/unit/queue/`
- `tests/flows/parallel_execution/`
- `tests/flows/ci_recovery/`
- `tests/flows/error_recovery/`

## Recommendations

1. **Update FR-001** to specify HTTP 202 (Accepted) instead of 200 - current implementation is more RESTful for async processing

2. **Document Label Strategy** - Add a section to the spec explaining the ForgeLabel approach vs Jira status transitions, since this is a deliberate design decision

3. **Implement _check_epic_completion** - The placeholder at `human_review.py:241` needs real Jira child issue querying

4. **Add Edge Case Handling** - Consider adding explicit handling for:
   - Rate limiting with exponential backoff
   - Concurrent modification detection
   - Graceful mid-execution recovery

5. **Fill Test Gaps** - Priority areas:
   - Integration tests for Jira/GitHub clients
   - Parallel execution flow tests
   - Error recovery scenarios

6. **Document Unspecced Features** - Add sections for:
   - Langfuse tracing configuration
   - Metrics/monitoring endpoints
   - CLI usage and commands
