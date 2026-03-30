"""Jira REST API client for CRUD operations on tickets."""

import logging
from typing import Any, Optional

import httpx

from forge.config import Settings, get_settings
from forge.integrations.jira.models import JiraComment, JiraIssue

logger = logging.getLogger(__name__)


class JiraClient:
    """Async client for Jira REST API v3.

    Handles authentication, rate limiting, and common operations
    for Features, Epics, Tasks, and Comments.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the Jira client.

        Args:
            settings: Application settings. Uses default if not provided.
        """
        self.settings = settings or get_settings()
        self.base_url = f"{self.settings.jira_base_url}/rest/api/3"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with authentication."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                auth=(
                    self.settings.jira_user_email,
                    self.settings.jira_api_token.get_secret_value(),
                ),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_issue(self, issue_key: str) -> JiraIssue:
        """Fetch a Jira issue by key.

        Args:
            issue_key: The Jira issue key (e.g., "PROJ-123").

        Returns:
            JiraIssue with fields populated from the API response.
        """
        client = await self._get_client()
        response = await client.get(f"/issue/{issue_key}")
        response.raise_for_status()
        data = response.json()
        return JiraIssue.from_api_response(data)

    async def update_description(self, issue_key: str, description: str) -> None:
        """Update the description field of a Jira issue.

        Args:
            issue_key: The Jira issue key.
            description: New description content (will be converted to ADF).
        """
        client = await self._get_client()
        adf_content = self._text_to_adf(description)
        response = await client.put(
            f"/issue/{issue_key}",
            json={"fields": {"description": adf_content}},
        )
        response.raise_for_status()
        logger.info(f"Updated description for {issue_key}")

    async def update_custom_field(
        self, issue_key: str, field_id: str, value: str
    ) -> None:
        """Update a custom field on a Jira issue.

        Args:
            issue_key: The Jira issue key.
            field_id: The custom field ID (e.g., "customfield_10050").
            value: The new value for the field.
        """
        client = await self._get_client()
        response = await client.put(
            f"/issue/{issue_key}",
            json={"fields": {field_id: value}},
        )
        response.raise_for_status()
        logger.info(f"Updated {field_id} for {issue_key}")

    async def transition_issue(self, issue_key: str, transition_name: str) -> None:
        """Transition a Jira issue to a new status.

        Args:
            issue_key: The Jira issue key.
            transition_name: The name of the target status.
        """
        client = await self._get_client()

        # Get available transitions
        response = await client.get(f"/issue/{issue_key}/transitions")
        response.raise_for_status()
        transitions = response.json().get("transitions", [])

        # Find matching transition
        transition_id = None
        for t in transitions:
            if t.get("name", "").lower() == transition_name.lower():
                transition_id = t["id"]
                break
            if t.get("to", {}).get("name", "").lower() == transition_name.lower():
                transition_id = t["id"]
                break

        if transition_id is None:
            available = [t.get("name") for t in transitions]
            raise ValueError(
                f"Transition '{transition_name}' not found. Available: {available}"
            )

        # Execute transition
        response = await client.post(
            f"/issue/{issue_key}/transitions",
            json={"transition": {"id": transition_id}},
        )
        response.raise_for_status()
        logger.info(f"Transitioned {issue_key} to {transition_name}")

    async def create_epic(
        self,
        project_key: str,
        summary: str,
        description: str,
        parent_key: str,
    ) -> str:
        """Create a new Epic linked to a parent Feature.

        Args:
            project_key: The Jira project key.
            summary: Epic title/summary.
            description: Epic description (implementation plan).
            parent_key: Parent Feature key for linking.

        Returns:
            The key of the created Epic.
        """
        client = await self._get_client()
        adf_content = self._text_to_adf(description)

        response = await client.post(
            "/issue",
            json={
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "description": adf_content,
                    "issuetype": {"name": "Epic"},
                    "parent": {"key": parent_key},
                }
            },
        )
        response.raise_for_status()
        epic_key = response.json()["key"]
        logger.info(f"Created Epic {epic_key} under {parent_key}")
        return epic_key

    async def create_task(
        self,
        project_key: str,
        summary: str,
        description: str,
        parent_key: str,
        labels: Optional[list[str]] = None,
    ) -> str:
        """Create a new Task linked to a parent Epic.

        Args:
            project_key: The Jira project key.
            summary: Task title/summary.
            description: Task implementation details.
            parent_key: Parent Epic key for linking.
            labels: Optional labels (e.g., target repository).

        Returns:
            The key of the created Task.
        """
        client = await self._get_client()
        adf_content = self._text_to_adf(description)

        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "description": adf_content,
            "issuetype": {"name": "Task"},
            "parent": {"key": parent_key},
        }
        if labels:
            fields["labels"] = labels

        response = await client.post("/issue", json={"fields": fields})
        response.raise_for_status()
        task_key = response.json()["key"]
        logger.info(f"Created Task {task_key} under {parent_key}")
        return task_key

    async def delete_issue(self, issue_key: str, delete_subtasks: bool = True) -> None:
        """Delete a Jira issue.

        Args:
            issue_key: The Jira issue key.
            delete_subtasks: Whether to also delete subtasks.
        """
        client = await self._get_client()
        params = {"deleteSubtasks": str(delete_subtasks).lower()}
        response = await client.delete(f"/issue/{issue_key}", params=params)
        response.raise_for_status()
        logger.info(f"Deleted issue {issue_key}")

    async def add_comment(self, issue_key: str, body: str) -> JiraComment:
        """Add a comment to a Jira issue.

        Args:
            issue_key: The Jira issue key.
            body: Comment text content.

        Returns:
            The created JiraComment.
        """
        client = await self._get_client()
        adf_content = self._text_to_adf(body)

        response = await client.post(
            f"/issue/{issue_key}/comment",
            json={"body": adf_content},
        )
        response.raise_for_status()
        data = response.json()
        logger.info(f"Added comment to {issue_key}")
        return JiraComment.from_api_response(data)

    async def get_comments(self, issue_key: str) -> list[JiraComment]:
        """Get all comments for a Jira issue.

        Args:
            issue_key: The Jira issue key.

        Returns:
            List of JiraComment objects.
        """
        client = await self._get_client()
        response = await client.get(f"/issue/{issue_key}/comment")
        response.raise_for_status()
        data = response.json()
        return [
            JiraComment.from_api_response(c) for c in data.get("comments", [])
        ]

    @staticmethod
    def _text_to_adf(text: str) -> dict[str, Any]:
        """Convert plain text to Atlassian Document Format.

        Args:
            text: Plain text content.

        Returns:
            ADF document structure.
        """
        paragraphs = text.split("\n\n") if text else [""]
        content = []

        for para in paragraphs:
            if para.strip():
                content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": para}],
                })

        return {
            "type": "doc",
            "version": 1,
            "content": content or [{"type": "paragraph", "content": []}],
        }
