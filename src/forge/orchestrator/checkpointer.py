"""Checkpointer for LangGraph workflow state persistence.

Uses SQLite for checkpoint storage to enable workflow pause/resume
across process restarts. For production deployments requiring Redis-based
checkpointing, install Redis with RediSearch module enabled.
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
