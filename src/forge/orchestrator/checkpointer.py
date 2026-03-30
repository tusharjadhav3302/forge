"""Redis checkpointer for LangGraph workflow state persistence."""

from typing import Optional

import redis.asyncio as redis
from langgraph.checkpoint.base import BaseCheckpointSaver

from forge.config import get_settings


class RedisCheckpointer(BaseCheckpointSaver):
    """Redis-based checkpointer for LangGraph state persistence.

    Enables workflow pause/resume across process restarts by storing
    graph state in Redis with automatic serialization.
    """

    def __init__(self, redis_client: redis.Redis, prefix: str = "forge:checkpoint:"):
        """Initialize the Redis checkpointer.

        Args:
            redis_client: Async Redis client instance.
            prefix: Key prefix for checkpoint storage.
        """
        super().__init__()
        self.redis = redis_client
        self.prefix = prefix

    def _make_key(self, thread_id: str, checkpoint_id: str) -> str:
        """Generate Redis key for a checkpoint."""
        return f"{self.prefix}{thread_id}:{checkpoint_id}"

    async def aget(self, config: dict) -> Optional[dict]:
        """Get checkpoint from Redis."""
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id", "latest")

        if not thread_id:
            return None

        key = self._make_key(thread_id, checkpoint_id)
        data = await self.redis.get(key)

        if data is None:
            return None

        import json
        return json.loads(data)

    async def aput(self, config: dict, checkpoint: dict) -> dict:
        """Store checkpoint in Redis."""
        import json
        import uuid

        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_id = str(uuid.uuid4())

        key = self._make_key(thread_id, checkpoint_id)
        await self.redis.set(key, json.dumps(checkpoint))

        # Also store as latest
        latest_key = self._make_key(thread_id, "latest")
        await self.redis.set(latest_key, json.dumps(checkpoint))

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }

    def get(self, config: dict) -> Optional[dict]:
        """Synchronous get - not implemented, use aget."""
        raise NotImplementedError("Use aget for async operations")

    def put(self, config: dict, checkpoint: dict) -> dict:
        """Synchronous put - not implemented, use aput."""
        raise NotImplementedError("Use aput for async operations")


_redis_pool: Optional[redis.ConnectionPool] = None


async def get_redis_client() -> redis.Redis:
    """Get a Redis client from the connection pool."""
    global _redis_pool

    settings = get_settings()

    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )

    return redis.Redis(connection_pool=_redis_pool)


async def get_checkpointer() -> RedisCheckpointer:
    """Get a configured Redis checkpointer instance."""
    client = await get_redis_client()
    return RedisCheckpointer(client)


async def close_redis_pool() -> None:
    """Close the Redis connection pool."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
