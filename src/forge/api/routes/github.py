"""GitHub webhook endpoint for receiving repository events."""

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from forge.config import get_settings
from forge.integrations.github.webhooks import (
    create_github_webhook_event,
    parse_github_webhook,
)
from forge.models.events import EventSource
from forge.queue.producer import QueueProducer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["github"])


@router.post(
    "/github",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Event accepted for processing"},
        400: {"description": "Invalid payload"},
        401: {"description": "Invalid webhook signature"},
    },
)
async def receive_github_webhook(
    request: Request,
    x_github_event: str = Header(default="ping"),
    x_github_delivery: str = Header(default=""),
    x_hub_signature_256: str = Header(default=""),
) -> dict[str, str]:
    """Receive and queue GitHub webhook events.

    This endpoint:
    1. Validates webhook signature
    2. Parses the webhook payload
    3. Queues the event for async processing
    4. Returns immediately (<500ms target)

    Args:
        request: FastAPI request object.
        x_github_event: Event type (e.g., "push", "pull_request").
        x_github_delivery: Unique delivery ID from GitHub.
        x_hub_signature_256: HMAC signature for verification.

    Returns:
        Acknowledgment with event ID.
    """
    settings = get_settings()

    # Handle ping events
    if x_github_event == "ping":
        return {"status": "pong", "event_id": x_github_delivery}

    # Read raw body for signature verification
    body = await request.body()

    # Validate signature
    if settings.github_webhook_secret.get_secret_value():
        if not _verify_github_signature(body, x_hub_signature_256, settings.github_webhook_secret.get_secret_value()):
            logger.warning("Invalid GitHub webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    # Parse JSON payload
    try:
        payload: dict[str, Any] = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse GitHub webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event_id = x_github_delivery or _generate_event_id(payload)

    try:
        # Parse webhook data
        webhook_data = parse_github_webhook(payload, x_github_event, event_id)

        # Skip events without ticket association
        if not webhook_data.ticket_key:
            logger.debug(f"Skipping GitHub event {event_id} - no ticket association")
            return {
                "status": "skipped",
                "event_id": event_id,
                "reason": "no_ticket_association",
            }

        webhook_event = create_github_webhook_event(webhook_data)

        # Queue for async processing
        producer = QueueProducer()
        await producer.publish(
            event_id=webhook_event.event_id,
            source=EventSource.GITHUB,
            event_type=webhook_event.event_type,
            ticket_key=webhook_event.ticket_key,
            payload=webhook_event.payload,
        )

        logger.info(f"Queued GitHub event {event_id} for {webhook_data.ticket_key}")

        return {
            "status": "accepted",
            "event_id": event_id,
            "ticket_key": webhook_data.ticket_key,
        }

    except ValueError as e:
        logger.error(f"Failed to parse GitHub webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to queue GitHub event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue event",
        )


def _verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature.

    Args:
        payload: Raw request body.
        signature: X-Hub-Signature-256 header value.
        secret: Webhook secret.

    Returns:
        True if signature is valid.
    """
    if not signature:
        return False

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


def _generate_event_id(payload: dict[str, Any]) -> str:
    """Generate a deterministic event ID from payload.

    Args:
        payload: Webhook payload.

    Returns:
        SHA256-based event ID.
    """
    import json
    content = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]
