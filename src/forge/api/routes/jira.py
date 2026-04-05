"""Jira webhook endpoint for receiving issue events."""

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from forge.config import get_settings
from forge.integrations.jira.webhooks import (
    create_webhook_event,
    parse_jira_webhook,
)
from forge.models.events import EventSource
from forge.observability.config import get_tracer
from forge.observability.context import get_correlation_id
from forge.queue.producer import QueueProducer

logger = logging.getLogger(__name__)
tracer = get_tracer("forge.api.jira")

router = APIRouter(prefix="/api/v1/webhooks", tags=["jira"])


@router.post(
    "/jira",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Event accepted for processing"},
        400: {"description": "Invalid payload"},
        401: {"description": "Invalid webhook signature"},
    },
)
async def receive_jira_webhook(
    request: Request,
    x_atlassian_webhook_identifier: str = Header(default=""),
) -> dict[str, str]:
    """Receive and queue Jira webhook events.

    This endpoint:
    1. Validates webhook signature (if configured)
    2. Parses the webhook payload
    3. Queues the event for async processing
    4. Returns immediately (<500ms target)

    Args:
        request: FastAPI request object.
        x_atlassian_webhook_identifier: Unique webhook event ID from Jira.

    Returns:
        Acknowledgment with event ID.
    """
    settings = get_settings()
    span = tracer.start_span(
        "jira_webhook",
        attributes={
            "correlation_id": get_correlation_id(),
            "forge.source": "jira",
        },
    )

    try:
        # Read raw body for signature verification
        body = await request.body()

        # Validate signature if webhook secret is configured
        if settings.jira_webhook_secret.get_secret_value():
            x_hub_signature = request.headers.get("X-Hub-Signature-256", "")
            if not _verify_jira_signature(
                body,
                x_hub_signature,
                settings.jira_webhook_secret.get_secret_value(),
            ):
                span.set_attribute("error", True)
                span.set_attribute("error.type", "auth_failure")
                logger.warning("Invalid Jira webhook signature")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature",
                )

        # Parse JSON payload
        try:
            payload: dict[str, Any] = await request.json()
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", "parse_error")
            logger.error(f"Failed to parse Jira webhook payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )

        # Generate event ID if not provided
        event_id = x_atlassian_webhook_identifier or _generate_event_id(payload)
        span.set_attribute("forge.event_id", event_id)

        # Parse webhook data
        webhook_data = parse_jira_webhook(payload, event_id)
        span.set_attribute("forge.ticket_key", webhook_data.ticket_key)
        span.set_attribute("forge.event_type", webhook_data.event_type)

        # Filter: only process issues with forge:managed label
        issue_labels = payload.get("issue", {}).get("fields", {}).get("labels", [])
        has_forge_managed = "forge:managed" in issue_labels

        # Also check if forge:managed is being added in this event
        changelog_items = payload.get("changelog", {}).get("items", [])
        for item in changelog_items:
            if item.get("field") == "labels":
                to_labels = item.get("toString", "")
                if "forge:managed" in to_labels:
                    has_forge_managed = True
                    break

        if not has_forge_managed:
            span.set_attribute("forge.skipped", True)
            span.set_attribute("forge.skip_reason", "missing forge:managed label")
            logger.debug(
                f"Skipping {webhook_data.ticket_key}: missing forge:managed label"
            )
            return {
                "status": "skipped",
                "event_id": event_id,
                "ticket_key": webhook_data.ticket_key,
                "reason": "missing forge:managed label",
            }

        webhook_event = create_webhook_event(webhook_data)

        # Queue for async processing
        producer = QueueProducer()
        await producer.publish(
            event_id=webhook_event.event_id,
            source=EventSource.JIRA,
            event_type=webhook_event.event_type,
            ticket_key=webhook_event.ticket_key,
            payload=webhook_event.payload,
        )

        span.set_attribute("forge.queued", True)
        logger.info(f"Queued Jira event {event_id} for {webhook_data.ticket_key}")

        return {
            "status": "accepted",
            "event_id": event_id,
            "ticket_key": webhook_data.ticket_key,
        }

    except HTTPException:
        raise
    except ValueError as e:
        span.set_attribute("error", True)
        span.set_attribute("error.type", "validation_error")
        logger.error(f"Failed to parse Jira webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        span.set_attribute("error", True)
        span.set_attribute("error.type", "internal_error")
        logger.error(f"Failed to queue Jira event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue event",
        )
    finally:
        span.end()


def _verify_jira_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Jira webhook signature.

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
