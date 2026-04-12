"""Jira webhook payload parsing and validation."""

import logging
from dataclasses import dataclass
from typing import Any

from forge.models.events import EventSource, WebhookEvent
from forge.models.workflow import TicketType

logger = logging.getLogger(__name__)


@dataclass
class JiraWebhookData:
    """Parsed data from a Jira webhook payload."""

    event_id: str
    event_type: str
    ticket_key: str
    ticket_type: TicketType
    status: str
    previous_status: str | None
    summary: str
    description: str
    comment: str | None
    comment_author: str | None
    user_id: str
    user_name: str
    raw_payload: dict[str, Any]


def parse_jira_webhook(payload: dict[str, Any], event_id: str) -> JiraWebhookData:
    """Parse a Jira webhook payload into structured data.

    Args:
        payload: Raw webhook payload from Jira.
        event_id: Unique event identifier from webhook header.

    Returns:
        Parsed JiraWebhookData.

    Raises:
        ValueError: If required fields are missing.
    """
    issue = payload.get("issue", {})
    fields = issue.get("fields", {})
    changelog = payload.get("changelog", {})

    # Extract ticket key
    ticket_key = issue.get("key")
    if not ticket_key:
        raise ValueError("Missing issue key in webhook payload")

    # Determine ticket type
    issue_type_name = fields.get("issuetype", {}).get("name", "").lower()
    ticket_type = _map_issue_type(issue_type_name)

    # Extract current and previous status
    status = fields.get("status", {}).get("name", "")
    previous_status = _extract_previous_status(changelog)

    # Extract description (handle ADF format)
    description = _extract_description(fields.get("description"))

    # Extract comment if present
    comment_data = payload.get("comment")
    comment = None
    comment_author = None
    if comment_data:
        comment = _extract_description(comment_data.get("body"))
        comment_author = comment_data.get("author", {}).get("displayName")

    # Extract user info
    user = payload.get("user", {})

    return JiraWebhookData(
        event_id=event_id,
        event_type=payload.get("webhookEvent", "unknown"),
        ticket_key=ticket_key,
        ticket_type=ticket_type,
        status=status,
        previous_status=previous_status,
        summary=fields.get("summary", ""),
        description=description,
        comment=comment,
        comment_author=comment_author,
        user_id=user.get("accountId", ""),
        user_name=user.get("displayName", ""),
        raw_payload=payload,
    )


def create_webhook_event(data: JiraWebhookData) -> WebhookEvent:
    """Create a WebhookEvent from parsed Jira webhook data.

    Args:
        data: Parsed Jira webhook data.

    Returns:
        WebhookEvent ready for queue publishing.
    """
    return WebhookEvent(
        event_id=data.event_id,
        source=EventSource.JIRA,
        event_type=data.event_type,
        ticket_key=data.ticket_key,
        payload=data.raw_payload,
    )


def _map_issue_type(issue_type_name: str) -> TicketType:
    """Map Jira issue type name to TicketType enum.

    Args:
        issue_type_name: Lowercase issue type name from Jira.

    Returns:
        Corresponding TicketType.
    """
    mapping = {
        "feature": TicketType.FEATURE,
        "epic": TicketType.EPIC,
        "task": TicketType.TASK,
        "sub-task": TicketType.TASK,
        "bug": TicketType.BUG,
        "story": TicketType.FEATURE,  # Treat stories as features
    }
    return mapping.get(issue_type_name, TicketType.TASK)


def _extract_previous_status(changelog: dict[str, Any]) -> str | None:
    """Extract previous status from changelog.

    Args:
        changelog: Changelog section of webhook payload.

    Returns:
        Previous status name if found, None otherwise.
    """
    items = changelog.get("items", [])
    for item in items:
        if item.get("field") == "status":
            return item.get("fromString")
    return None


def _extract_description(content: Any) -> str:
    """Extract plain text from description field (handles ADF).

    Args:
        content: Description field value (string or ADF dict).

    Returns:
        Extracted plain text.
    """
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        return _extract_text_from_adf(content)

    return str(content)


def _extract_text_from_adf(adf: dict[str, Any]) -> str:
    """Extract plain text from Atlassian Document Format.

    Args:
        adf: ADF document structure.

    Returns:
        Extracted plain text.
    """
    if not isinstance(adf, dict):
        return str(adf) if adf else ""

    content = adf.get("content", [])
    texts = []

    for node in content:
        node_type = node.get("type")
        if node_type == "paragraph":
            para_texts = []
            for child in node.get("content", []):
                if child.get("type") == "text":
                    para_texts.append(child.get("text", ""))
            texts.append("".join(para_texts))
        elif node_type == "text":
            texts.append(node.get("text", ""))
        elif node_type in ("bulletList", "orderedList"):
            for item in node.get("content", []):
                item_text = _extract_text_from_adf(item)
                if item_text:
                    texts.append(f"- {item_text}")
        elif node_type == "heading":
            heading_texts = []
            for child in node.get("content", []):
                if child.get("type") == "text":
                    heading_texts.append(child.get("text", ""))
            texts.append("".join(heading_texts))

    return "\n\n".join(filter(None, texts))


def is_status_transition(data: JiraWebhookData, to_status: str) -> bool:
    """Check if the webhook represents a transition to a specific status.

    Args:
        data: Parsed webhook data.
        to_status: Target status to check for.

    Returns:
        True if this is a transition to the specified status.
    """
    return (
        data.status.lower() == to_status.lower()
        and data.previous_status is not None
        and data.previous_status.lower() != to_status.lower()
    )


def is_feedback_comment(data: JiraWebhookData) -> bool:
    """Check if the webhook represents a feedback comment.

    Args:
        data: Parsed webhook data.

    Returns:
        True if this is a comment event with feedback content.
    """
    return (
        "comment" in data.event_type.lower()
        and data.comment is not None
        and len(data.comment.strip()) > 0
    )
