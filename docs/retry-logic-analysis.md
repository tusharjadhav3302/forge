# Retry Logic Analysis

Analysis of retry/resume behavior across the Forge workflow orchestrator.

## State Fields Involved

| Field | Type | Purpose |
|-------|------|---------|
| `last_error` | `Optional[str]` | Error message from failed node |
| `retry_count` | `int` | Number of retry attempts |
| `is_paused` | `bool` | Whether workflow is paused at a gate |
| `revision_requested` | `bool` | Whether feedback/rejection occurred |
| `feedback_comment` | `Optional[str]` | User feedback for regeneration |
| `current_node` | `str` | Where workflow currently is |
| `current_task_key` | `Optional[str]` | Task being revised (for single-task updates) |
| `terminal_error_notified` | `bool` | Whether Jira comment was posted for terminal error |
| `implemented_tasks` | `list[str]` | Tasks that have been implemented |
| `repos_completed` | `list[str]` | Repositories that have been processed |

---

## Retry Flow Overview

### Entry Point: Worker._handle_resume_event()

Location: `src/forge/orchestrator/worker.py:135-334`

When a webhook arrives for an existing workflow:

1. Check if workflow `should_resume` (is_paused OR has current_node)
2. Detect signals from webhook:
   - `forge:retry` label → explicit retry request
   - `*-approved` label → approval signal
   - Comment on ticket → feedback/rejection
3. Build `updated_state` with appropriate flags
4. Resume workflow via `ainvoke()`

### Routing: graph.route_by_ticket_type()

Location: `src/forge/orchestrator/graph.py:80-158`

Routes based on `current_node`:
- Planning stages → resume at that stage
- Execution stages → resume at `task_router`
- Terminal states → route to END
- Unknown → fall through to ticket type routing

---

## Case-by-Case Analysis

### Case 1: Planning Stage Errors

**Nodes:** generate_prd, generate_spec, decompose_epics, generate_tasks

**When error occurs:**
```python
# From task_generation.py:152-161
return {
    **state,
    "last_error": str(e),
    "current_node": "generate_tasks",
    "retry_count": state.get("retry_count", 0) + 1,
}
```

**On next webhook:**
- Worker detects `last_error is not None`
- Clears `last_error` (worker.py:326-332)
- Routes to same node via `route_by_ticket_type`

**Status:** ✅ Working correctly

---

### Case 2: Partial Content + Error

**Scenario:** Generation partially succeeds but throws error

**Routing logic:**
```python
# From graph.py:442-459
def _route_after_generation(state):
    last_error = state.get("last_error")
    prd_content = state.get("prd_content", "")

    if last_error and not prd_content:
        return END  # Don't advance

    return "prd_approval_gate"  # Advance if content exists
```

**Behavior:** If content exists despite error, proceeds to approval

**Status:** ✅ Intentional design - allows partial progress

---

### Case 3: Approval Label Doesn't Match Stage

**Scenario:** User adds `prd-approved` label while workflow is at `spec_approval_gate`

**Detection logic:**
```python
# From worker.py:191-217
node_to_stage = {
    "prd_approval_gate": "prd",
    "spec_approval_gate": "spec",
    ...
}
expected_stage = node_to_stage.get(current_node)

if approval_stage and expected_stage and approval_stage == expected_stage:
    is_approved = True
elif approval_stage:
    logger.warning(f"Ignoring {approval_stage} approval...")
```

**Behavior:** Mismatched approvals are logged and ignored

**Status:** ✅ Working correctly

---

### Case 4: Comment on Child Ticket (Task-level feedback)

**Scenario:** User comments on a Task ticket instead of Feature

**Detection logic:**
```python
# From worker.py:235-254
if message.ticket_key != workflow_ticket_key:
    # Comment is on a child ticket
    if message.ticket_key in task_keys:
        comment_ticket_key = message.ticket_key
        # Sets current_task_key for single-task update
```

**Routing:**
```python
# From gates/task_approval.py:84-90
if current_task:
    # Single Task update
    return "update_single_task"
elif feedback:
    # Feature-level regeneration
    return "regenerate_all_tasks"
```

**Status:** ✅ Working correctly

---

### Case 5: Tests Fail in Container

**Scenario:** Container runs, code is implemented, but tests fail

**Current behavior:**
```python
# From implementation.py:128-140
if result.tests_failed:
    # Still continue - tests failed but code was committed
    implemented = state.get("implemented_tasks", [])
    implemented.append(current_task)

    return update_state_timestamp({
        **state,
        "current_task_key": None,
        "implemented_tasks": implemented,
        "current_node": "implement_task",
        "last_error": f"Tests failed: {error_msg}",
    })
```

**Behavior:** Task is marked as implemented despite test failure

**Questions:**
- Should test failures block further progress?
- Should the PR be created with failing tests?
- Is `last_error` being set here causing issues downstream?

**Status:** ⚠️ Design decision needed

---

### Case 6: Max Implementation Retries Exceeded

**Scenario:** Task implementation fails 3+ times

**Routing logic:**
```python
# From graph.py:546-555
def _route_implementation(state):
    retry_count = state.get("retry_count", 0)
    max_retries = 3
    last_error = state.get("last_error")

    if last_error and retry_count >= max_retries:
        return "escalate_blocked"
```

**Behavior:** Routes to `escalate_blocked` which ends at END

**Status:** ✅ Working correctly

---

### Case 7: Terminal State + Error + Random Webhook

**Scenario:** Workflow completed with error at `aggregate_feature_status`, receives unrelated webhook

**Previous behavior (BUG):**
- `route_by_ticket_type` didn't recognize terminal states
- Fell through to ticket type routing
- Restarted from `generate_prd`

**Fixed behavior:**
```python
# From graph.py:140-144
elif current_node in ("complete", "complete_tasks", "aggregate_feature_status"):
    logger.info(f"Workflow at terminal state '{current_node}', returning END")
    return END
```

```python
# From worker.py:307-324
if is_terminal and not is_retry:
    # Post Jira comment explaining how to retry
    if not current_state.get("terminal_error_notified"):
        await self._post_terminal_error_comment(ticket_key, last_error)
        return {**current_state, "terminal_error_notified": True}
    return current_state  # No changes
```

**Status:** ✅ Fixed in current changes

---

### Case 8: Terminal State + forge:retry Label

**Scenario:** User adds `forge:retry` label to retry failed terminal state

**Current behavior:**
```python
# From worker.py:277-291
if is_retry:
    updated_state["last_error"] = None
    updated_state["revision_requested"] = False
    updated_state["feedback_comment"] = None
    updated_state["terminal_error_notified"] = False

    if is_terminal:
        logger.info(f"Terminal state retry: resetting {current_node} -> task_router")
        updated_state["current_node"] = "task_router"
```

**Then task_router.py:52-63 does:**
```python
return update_state_timestamp({
    **state,
    "repos_to_process": repos_to_process,
    "current_repo": repos_to_process[0] if repos_to_process else None,
    "repos_completed": [],        # <-- RESETS!
    "implemented_tasks": [],       # <-- RESETS!
    "current_node": "setup_workspace",
    "last_error": None,
})
```

**Problem:** All progress is lost - previously completed repos/tasks forgotten

**Status:** ❌ Bug - progress reset on retry

---

### Case 9: Terminal State + forge:retry + NO Error

**Scenario:** Workflow completed successfully, user accidentally adds `forge:retry`

**Current behavior:**
```python
# From worker.py:277-291
if is_retry:
    # ... clears error flags ...
    if is_terminal:
        updated_state["current_node"] = "task_router"
```

**Problem:** No check for whether `last_error` exists

**Expected:** Should ignore retry if no error to retry from

**Status:** ❌ Bug - restarts even without error

---

### Case 10: Multiple Webhooks After Terminal Error

**Scenario:** Multiple webhooks arrive after terminal error

**Current behavior:**
```python
# From worker.py:317-324
if not current_state.get("terminal_error_notified"):
    await self._post_terminal_error_comment(ticket_key, last_error)
    return {**current_state, "terminal_error_notified": True}
return current_state
```

**Status:** ✅ Fixed - uses flag to prevent duplicate comments

---

### Case 11: Retry Should Preserve Progress

**Scenario:** Error at `aggregate_feature_status`, user retries

**Expected:** Should only retry the failed aggregation, not re-implement all tasks

**Current:** Routes to `task_router` which resets `implemented_tasks`

**Status:** ❌ Bug - see Case 8

---

### Case 12: Error in aggregate_feature_status

**Scenario:** Jira API fails when transitioning Feature to Done

**Current behavior:**
```python
# From human_review.py:230-236
except Exception as e:
    logger.error(f"Feature completion failed for {ticket_key}: {e}")
    return {
        **state,
        "last_error": str(e),
    }
```

**Note:** Doesn't set `current_node` or increment `retry_count`

**Status:** ⚠️ Inconsistent error handling

---

## Summary of Issues

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 5 | Test failures allow progress | Low | implementation.py:128-140 |
| 8 | Terminal retry resets progress | High | worker.py:288 + task_router.py:55-63 |
| 9 | Retry without error restarts | Medium | worker.py:277-291 |
| 12 | Inconsistent error state in aggregation | Low | human_review.py:230-236 |

---

## Recommended Fixes

### Fix for Issue 8 & 9: Preserve progress on terminal retry

```python
# In worker.py, around line 277
if is_retry:
    # Only process retry if there was an error
    if not was_errored and not current_state.get("last_error"):
        logger.info(f"Ignoring forge:retry - no error to retry from")
        return current_state
    
    updated_state["last_error"] = None
    updated_state["revision_requested"] = False
    updated_state["feedback_comment"] = None
    updated_state["terminal_error_notified"] = False
    
    if is_terminal:
        # Don't go through task_router - go directly to the failed node
        # This preserves implemented_tasks and repos_completed
        logger.info(f"Terminal state retry: retrying {current_node}")
        # Keep current_node as-is, just clear the error
```

### Alternative: Make task_router preserve existing progress

```python
# In task_router.py route_tasks_by_repo()
# Don't reset if already have progress
repos_completed = state.get("repos_completed", [])
implemented_tasks = state.get("implemented_tasks", [])

return update_state_timestamp({
    **state,
    "repos_to_process": repos_to_process,
    "current_repo": repos_to_process[0] if repos_to_process else None,
    "repos_completed": repos_completed,  # Preserve
    "implemented_tasks": implemented_tasks,  # Preserve
    ...
})
```

### Fix for Issue 12: Consistent error handling

```python
# In human_review.py aggregate_feature_status()
except Exception as e:
    logger.error(f"Feature completion failed for {ticket_key}: {e}")
    return {
        **state,
        "last_error": str(e),
        "current_node": "aggregate_feature_status",  # Add this
        "retry_count": state.get("retry_count", 0) + 1,  # Add this
    }
```

---

## Test Scenarios to Verify

1. [ ] PRD generation fails → webhook → retries PRD generation
2. [ ] Spec approved → workflow advances to decompose_epics
3. [ ] Comment on Task ticket → routes to update_single_task
4. [ ] Implementation retries 3x → escalates to blocked
5. [ ] Terminal state + webhook → posts Jira comment, doesn't restart
6. [ ] Terminal state + forge:retry → retries failed node
7. [ ] Terminal state + forge:retry (no error) → does nothing
8. [ ] Retry preserves implemented_tasks list
