"""Webhook event schemas."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class JiraUser(BaseModel):
    """Jira user information."""

    display_name: str = Field(..., alias="displayName")
    email_address: Optional[str] = Field(None, alias="emailAddress")
    account_id: str = Field(..., alias="accountId")


class JiraStatus(BaseModel):
    """Jira issue status."""

    name: str
    id: str


class JiraIssueType(BaseModel):
    """Jira issue type."""

    name: str
    id: str


class JiraIssueFields(BaseModel):
    """Jira issue fields."""

    summary: str
    description: Optional[str] = None
    status: JiraStatus
    issuetype: JiraIssueType = Field(..., alias="issuetype")
    parent: Optional[dict[str, Any]] = None


class JiraIssue(BaseModel):
    """Jira issue in webhook payload."""

    key: str
    id: str
    fields: JiraIssueFields


class ChangelogItem(BaseModel):
    """Single changelog item."""

    field: str
    fieldtype: str
    from_: Optional[str] = Field(None, alias="from")
    from_string: Optional[str] = Field(None, alias="fromString")
    to: Optional[str] = Field(None, alias="to")
    to_string: Optional[str] = Field(None, alias="toString")


class Changelog(BaseModel):
    """Webhook changelog."""

    items: list[ChangelogItem] = Field(default_factory=list)


class Comment(BaseModel):
    """Jira comment."""

    id: str
    body: str
    author: JiraUser
    created: datetime


class WebhookEvent(BaseModel):
    """Base webhook event from Jira."""

    timestamp: int
    webhook_event: str = Field(..., alias="webhookEvent")
    issue: JiraIssue
    changelog: Optional[Changelog] = None
    comment: Optional[Comment] = None

    @property
    def event_type(self) -> Literal["issue_updated", "comment_created"]:
        """Get simplified event type."""
        if self.webhook_event == "comment_created":
            return "comment_created"
        return "issue_updated"

    @property
    def ticket_id(self) -> str:
        """Get ticket ID (issue key)."""
        return self.issue.key

    @property
    def current_status(self) -> str:
        """Get current issue status."""
        return self.issue.fields.status.name

    @property
    def previous_status(self) -> Optional[str]:
        """Get previous status from changelog (if status changed)."""
        if not self.changelog:
            return None

        for item in self.changelog.items:
            if item.field == "status" and item.from_string:
                return item.from_string

        return None

    @property
    def issue_type(self) -> str:
        """Get issue type (Feature, Epic, Story)."""
        return self.issue.fields.issuetype.name


class WebhookResponse(BaseModel):
    """Response sent back to Jira webhook."""

    status: Literal["success", "error", "duplicate"]
    message: str
    ticket_id: Optional[str] = None
    event_id: Optional[str] = None
