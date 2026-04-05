# Implementation Tasks from Spec Sync

Generated: 2026-04-05
Source: drift proposals from spec 001-ai-sdlc-orchestrator

These tasks represent code changes needed to align implementation with specifications.

---

## Task: Implement Epic Completion Check (US9)

**Spec Requirement**: User Story 9 - Human Code Review and Merge
**Current Code**: `_check_epic_completion` is a stub returning False
**Required Change**: Query Jira for child Tasks and verify all are Done
**Files to Modify**: 
- `src/forge/orchestrator/nodes/human_review.py:241-253`

**Estimated Effort**: 1 hour

### Acceptance Criteria
- [ ] Query Jira API for all Tasks linked to the Epic
- [ ] Return True only when all child Tasks have status "Done"
- [ ] Handle edge case of Epic with no Tasks
- [ ] Add appropriate error handling for Jira API failures

---

## Task: Add Jira Rate Limit Handling

**Spec Requirement**: Edge Cases - Rate Limit Resilience
**Current Code**: No exponential backoff on 429 responses
**Required Change**: Add exponential backoff and retry logic for 429 responses
**Files to Modify**: 
- `src/forge/integrations/jira/client.py`

**Estimated Effort**: 2 hours

### Acceptance Criteria
- [ ] Detect HTTP 429 responses from Jira API
- [ ] Implement exponential backoff (starting at 1s, max 60s)
- [ ] Respect Retry-After header when provided
- [ ] Log rate limit events with backoff duration
- [ ] Configure max retry attempts (default: 5)

---

## Task: Implement Webhook Retry/Dead-Letter Queue

**Spec Requirement**: Edge Cases - Webhook Reliability
**Current Code**: Failed webhooks are dropped
**Required Change**: Persist failed events and implement retry queue
**Files to Modify**: 
- `src/forge/queue/` (new files may be needed)

**Estimated Effort**: 4 hours

### Acceptance Criteria
- [ ] Persist failed webhook events to Redis/database
- [ ] Implement configurable retry policy (3 attempts, exponential backoff)
- [ ] Move permanently failed events to dead-letter queue
- [ ] Expose dead-letter queue for manual inspection
- [ ] Add metrics for retry/dead-letter counts

---

## Task: Add Branch Conflict Detection

**Spec Requirement**: Edge Cases - Concurrent Modification
**Current Code**: Pushes without checking for remote changes
**Required Change**: Check for remote changes before push, handle conflicts
**Files to Modify**: 
- `src/forge/workspace/git_ops.py`

**Estimated Effort**: 2 hours

### Acceptance Criteria
- [ ] Fetch remote before push
- [ ] Detect diverged branches (remote has commits not in local)
- [ ] Escalate to human review when conflicts detected
- [ ] Log conflict details with affected files

---

## Task: Verify Checkpoint Recovery

**Spec Requirement**: FR-020 - Workflow State Persistence
**Current Code**: Checkpoint recovery exists but needs verification
**Required Change**: Verify and document checkpoint recovery behavior
**Files to Modify**: 
- `src/forge/orchestrator/checkpointer.py`

**Estimated Effort**: 2 hours

### Acceptance Criteria
- [ ] Write integration test for orchestrator restart mid-task
- [ ] Verify workflow resumes from correct state
- [ ] Document recovery behavior in code comments
- [ ] Add logging for recovery events

---

## Task: Add Missing Guardrails Validation

**Spec Requirement**: FR-012 - Repository Guardrails
**Current Code**: Silently proceeds when constitution.md/agents.md missing
**Required Change**: Add explicit warnings for missing guardrails
**Files to Modify**: 
- `src/forge/workspace/guardrails.py`

**Estimated Effort**: 1 hour

### Acceptance Criteria
- [ ] Log warning when constitution.md is missing
- [ ] Log warning when agents.md is missing
- [ ] Optionally block execution via configuration flag
- [ ] Include repository name in warning messages

---

## Task: Add Merge Conflict Detection

**Spec Requirement**: Edge Cases - Parallel Execution
**Current Code**: No pre-push conflict detection
**Required Change**: Detect potential merge conflicts and escalate
**Files to Modify**: 
- `src/forge/orchestrator/nodes/pr_creation.py`

**Estimated Effort**: 3 hours

### Acceptance Criteria
- [ ] Simulate merge against target branch before PR creation
- [ ] Detect conflicting files
- [ ] Transition Task to "Blocked" when conflicts found
- [ ] Include conflict details in Jira comment
- [ ] Notify appropriate human reviewer

---

## Summary

| Task | Effort | Priority |
|------|--------|----------|
| Epic Completion Check | 1 hour | High |
| Rate Limit Handling | 2 hours | High |
| Webhook Retry Queue | 4 hours | Medium |
| Branch Conflict Detection | 2 hours | Medium |
| Checkpoint Recovery | 2 hours | Medium |
| Guardrails Validation | 1 hour | Low |
| Merge Conflict Detection | 3 hours | Medium |

**Total Estimated Effort**: 15 hours (2-3 days)
