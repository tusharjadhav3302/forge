"""Checkpointer for LangGraph workflow state persistence.

Uses SQLite for checkpoint storage to enable workflow pause/resume
across process restarts. For production deployments requiring Redis-based
checkpointing, install Redis with RediSearch module enabled.

## Checkpoint Recovery Behavior

When a workflow is interrupted (process crash, restart, etc.), the checkpoint
system enables transparent recovery:

1. **On workflow invocation**: LangGraph checks for existing checkpoint
   with the given thread_id (ticket key).

2. **If checkpoint exists**: Workflow resumes from the last saved state,
   including all context, current_node, retry_count, and other state fields.
   The workflow continues from the exact node where it was interrupted.

3. **If no checkpoint**: Fresh workflow execution begins.

4. **Checkpoint writes**: Each node completion automatically saves state.
   Checkpoints are transactional and atomic.

5. **Pause gates**: When a workflow hits a pause gate (human approval),
   the checkpoint persists the is_paused=True state. On resume, the gate
   checks this flag and continues appropriately.

## Thread ID Convention

Thread IDs are Jira ticket keys (e.g., "AISOS-123"). This provides:
- Natural 1:1 mapping of ticket to workflow instance
- Easy inspection and debugging
- Clear correlation in logs and monitoring

## Checkpoint Cleanup

Use `clear_checkpoint(thread_id)` to reset a workflow. This is necessary when:
- A workflow needs to restart from scratch
- Debugging workflow state issues
- Cleaning up after failed test runs
"""

from pathlib import Path

import redis.asyncio as redis
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from forge.config import get_settings

# Global instances
_checkpointer: AsyncSqliteSaver | None = None
_checkpointer_context = None
_redis_pool: redis.ConnectionPool | None = None

# Default checkpoint database path
CHECKPOINT_DB_PATH = Path.home() / ".forge" / "checkpoints.db"


async def get_checkpointer() -> AsyncSqliteSaver:
    """Get a configured SQLite checkpointer instance.

    Uses AsyncSqliteSaver from langgraph-checkpoint-sqlite for proper
    LangGraph checkpoint API compatibility. Stores checkpoints in
    ~/.forge/checkpoints.db by default.

    Returns:
        Configured AsyncSqliteSaver instance.
    """
    global _checkpointer, _checkpointer_context

    if _checkpointer is None:
        # Ensure parent directory exists
        CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        # from_conn_string returns an async context manager
        _checkpointer_context = AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB_PATH))
        # Manually enter the context manager for long-running use
        _checkpointer = await _checkpointer_context.__aenter__()

    return _checkpointer


async def close_checkpointer() -> None:
    """Close the checkpointer connection."""
    global _checkpointer, _checkpointer_context

    if _checkpointer is not None and _checkpointer_context is not None:
        await _checkpointer_context.__aexit__(None, None, None)
        _checkpointer = None
        _checkpointer_context = None


async def get_redis_client() -> redis.Redis:
    """Get a Redis client from the connection pool.

    This is used by the queue consumer and other components that need
    direct Redis access for message queuing.

    Returns:
        Async Redis client instance.
    """
    global _redis_pool

    settings = get_settings()

    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )

    return redis.Redis(connection_pool=_redis_pool)


async def close_redis_pool() -> None:
    """Close the Redis connection pool."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None


async def clear_checkpoint(thread_id: str) -> bool:
    """Clear checkpoint state for a specific thread/ticket.

    Args:
        thread_id: The thread ID (typically the ticket key like AISOS-104).

    Returns:
        True if checkpoint was cleared, False if not found.
    """
    import aiosqlite

    if not CHECKPOINT_DB_PATH.exists():
        return False

    async with aiosqlite.connect(str(CHECKPOINT_DB_PATH)) as db:
        # LangGraph checkpoint tables: checkpoints, writes
        cursor = await db.execute(
            "DELETE FROM checkpoints WHERE thread_id = ?",
            (thread_id,)
        )
        deleted = cursor.rowcount > 0

        await db.execute(
            "DELETE FROM writes WHERE thread_id = ?",
            (thread_id,)
        )

        await db.commit()
        return deleted


async def get_checkpoint_state(thread_id: str) -> dict | None:
    """Get the current checkpoint state for a thread.

    Useful for debugging and verification.

    Args:
        thread_id: The thread ID (typically the ticket key).

    Returns:
        Checkpoint state dict or None if no checkpoint exists.
    """
    from forge.orchestrator.graph import get_workflow

    checkpointer = await get_checkpointer()
    workflow = get_workflow(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": thread_id}}
    state = await workflow.aget_state(config)

    if state and state.values:
        return dict(state.values)
    return None


async def verify_checkpoint_recovery(thread_id: str) -> dict:
    """Verify checkpoint recovery for a thread.

    Tests that checkpoint can be read and contains expected fields.
    Used for testing and validation.

    Args:
        thread_id: The thread ID to verify.

    Returns:
        Dict with verification results:
        - has_checkpoint: bool
        - current_node: str or None
        - is_paused: bool or None
        - retry_count: int or None
        - context_keys: list of keys in context
        - last_updated: str or None
    """
    import logging

    logger = logging.getLogger(__name__)

    state = await get_checkpoint_state(thread_id)

    if state is None:
        logger.info(f"No checkpoint found for {thread_id}")
        return {
            "has_checkpoint": False,
            "current_node": None,
            "is_paused": None,
            "retry_count": None,
            "context_keys": [],
            "last_updated": None,
        }

    result = {
        "has_checkpoint": True,
        "current_node": state.get("current_node"),
        "is_paused": state.get("is_paused"),
        "retry_count": state.get("retry_count", 0),
        "context_keys": list(state.get("context", {}).keys()),
        "last_updated": state.get("updated_at"),
    }

    logger.info(
        f"Checkpoint verified for {thread_id}: "
        f"node={result['current_node']}, "
        f"paused={result['is_paused']}, "
        f"retries={result['retry_count']}"
    )

    return result


async def list_checkpoints(limit: int = 100) -> list[dict]:
    """List all checkpoint thread IDs.

    Args:
        limit: Maximum number of checkpoints to return.

    Returns:
        List of checkpoint summaries with thread_id and metadata.
    """
    import aiosqlite

    if not CHECKPOINT_DB_PATH.exists():
        return []

    async with aiosqlite.connect(str(CHECKPOINT_DB_PATH)) as db:
        cursor = await db.execute(
            "SELECT DISTINCT thread_id FROM checkpoints LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()

        return [{"thread_id": row[0]} for row in rows]
