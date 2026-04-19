# Retryable Blocked State via forge:retry

## Problem

`escalate_to_blocked` always overwrites `current_node = "complete"`, erasing which node triggered the escalation. The worker treats this as a successful terminal state — indistinguishable from a happy-path completion — and refuses to invoke on `forge:retry`. There is no way for a user to retry a blocked ticket without directly patching the Redis checkpoint.

## Design

Add a new `is_blocked: bool` state field. `escalate_to_blocked` sets it instead of overwriting `current_node`. The triggering node is preserved in state, so `forge:retry` knows exactly where to resume.

**Retry behavior**: always resume at the node that failed, never back-track to an earlier stage.

## Changes

### 1. State Schema — `src/forge/workflow/base.py`

Add `is_blocked: bool` to `BaseState`. Add `"is_blocked": False` default to `create_initial_feature_state` and `create_initial_bug_state`.

### 2. `escalate_to_blocked` — `src/forge/workflow/nodes/ci_evaluator.py`

Remove `"current_node": "complete"` from the return value. Add `"is_blocked": True`. Keep the Jira label, error comment, and state cleanup (generation_context, qa_history) unchanged.

Before:
```python
return update_state_timestamp({
    **state,
    "ci_status": "blocked",
    "current_node": "complete",   # ← erases the failing node
    "generation_context": {},
    "qa_history": [],
})
```

After:
```python
return update_state_timestamp({
    **state,
    "is_blocked": True,
    "ci_status": "blocked",
    # current_node preserved — retry resumes here
    "generation_context": {},
    "qa_history": [],
})
```

### 3. `forge:retry` handler — `src/forge/orchestrator/worker.py`

In `_handle_resume_event`, when `is_retry = True`, add to the reset:

```python
updated_state["is_blocked"] = False
updated_state["ci_fix_attempts"] = 0   # so CI retry counter doesn't immediately exhaust again
```

`current_node`, `retry_count`, and `last_error` are already handled.

### 4. Worker terminal/blocked check — `src/forge/orchestrator/worker.py`

Replace the current terminal-only check in `_process_workflow` with a check that covers both cases:

```python
# Treat as non-invocable if: happy-path complete OR blocked without explicit retry
terminal_nodes = ("complete", "complete_tasks", "aggregate_feature_status")
is_terminal_or_blocked = (
    updated_values.get("current_node") in terminal_nodes
    or updated_values.get("is_blocked", False)
)

if is_terminal_or_blocked:
    logger.info(
        f"Workflow for {ticket_key} at "
        f"{'terminal state' if updated_values.get('current_node') in terminal_nodes else 'blocked state'} "
        f"'{updated_values.get('current_node')}', skipping invocation"
    )
    await compiled_workflow.aupdate_state(config, updated_values)
    return
```

Note: when `forge:retry` is used, `is_blocked` is cleared to `False` by step 3, so this check is bypassed and invocation proceeds normally.

### 5. `route_by_ticket_type` — `src/forge/workflow/feature/graph.py`

No changes required. The preserved `current_node` (e.g. `ci_evaluator`, `setup_workspace`, `implement_task`) is already handled in the existing routing table.

## Behavior After the Fix

| Scenario | forge:retry result |
|----------|-------------------|
| CI exhausted retries | resumes at `ci_evaluator`, `ci_fix_attempts` reset to 0 |
| Workspace setup failed | resumes at `setup_workspace` |
| Implementation hit max retries | resumes at `implement_task`, `retry_count` reset to 0 |
| PR creation failed | resumes at `create_pr` |
| Happy-path `complete` | `forge:retry` ignored (no error, no block) |
| Multiple blocked events | error comment re-posted each time (consistent with existing behavior) |

## Out of Scope

- Back-tracking to earlier stages on retry (e.g. re-running implementation after CI exhaustion is a separate decision)
- Per-node retry limits beyond what already exists (`retry_count`, `ci_fix_attempts`)
