"""Queue producer for publishing webhook events to Redis Streams."""

import logging
from typing import Any, Optional

import redis.asyncio as redis

from forge.models.events import EventSource
from forge.orchestrator.checkpointer import get_redis_client
from forge.queue.models import QueueMessage

logger = logging.getLogger(__name__)

# Stream names for different event sources
JIRA_STREAM = "forge:events:jira"
GITHUB_STREAM = "forge:events:github"


class QueueProducer:
    """Publishes webhook events to Redis Streams for async processing."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize the queue producer.

        Args:
            redis_client: Optional Redis client. Creates new if not provided.
        """
        self._redis = redis_client
        self._initialized = redis_client is not None

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis

    def _get_stream_name(self, source: EventSource) -> str:
        """Get the appropriate stream name for an event source."""
        return JIRA_STREAM if source == EventSource.JIRA else GITHUB_STREAM

    async def publish(
        self,
        event_id: str,
        source: EventSource,
        event_type: str,
        ticket_key: str,
        payload: dict[str, Any],
    ) -> str:
        """Publish an event to the queue.

        Args:
            event_id: Unique event identifier for deduplication.
            source: Event source (Jira or GitHub).
            event_type: Type of event (e.g., "issue_updated").
            ticket_key: Associated Jira ticket key.
            payload: Raw webhook payload.

        Returns:
            The Redis stream message ID.
        """
        redis_client = await self._get_redis()
        stream = self._get_stream_name(source)

        message = QueueMessage(
            message_id="",  # Will be assigned by Redis
            event_id=event_id,
            source=source,
            event_type=event_type,
            ticket_key=ticket_key,
            payload=payload,
        )

        message_id = await redis_client.xadd(stream, message.to_dict())
        logger.info(f"Published event {event_id} to {stream} as {message_id}")
        return message_id

    async def republish(self, message: QueueMessage) -> str:
        """Republish a message (e.g., for retry).

        Args:
            message: The message to republish with incremented retry count.

        Returns:
            The new Redis stream message ID.
        """
        return await self.publish(
            event_id=message.event_id,
            source=message.source,
            event_type=message.event_type,
            ticket_key=message.ticket_key,
            payload=message.payload,
        )
