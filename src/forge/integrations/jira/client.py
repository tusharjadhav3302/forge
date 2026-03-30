"""Jira REST API client for CRUD operations on tickets."""

import logging
from typing import Any, Optional

import httpx

from forge.config import Settings, get_settings
from forge.integrations.jira.models import JiraComment, JiraIssue
from forge.models.workflow import ForgeLabel

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

    async def add_attachment(
        self,
        issue_key: str,
        filename: str,
        content: str | bytes,
        content_type: str = "text/markdown",
    ) -> dict[str, Any]:
        """Add an attachment to a Jira issue.

        Args:
            issue_key: The Jira issue key.
            filename: Name for the attachment file.
            content: File content (string or bytes).
            content_type: MIME type of the content.

        Returns:
            The attachment metadata from Jira API.
        """
        # Attachments require a separate client without JSON content-type
        async with httpx.AsyncClient(
            base_url=self.base_url,
            auth=(
                self.settings.jira_user_email,
                self.settings.jira_api_token.get_secret_value(),
            ),
            headers={
                "Accept": "application/json",
                "X-Atlassian-Token": "no-check",  # Required for attachments
            },
            timeout=60.0,
        ) as client:
            # Convert string to bytes if needed
            if isinstance(content, str):
                content = content.encode("utf-8")

            files = {"file": (filename, content, content_type)}
            response = await client.post(
                f"/issue/{issue_key}/attachments",
                files=files,
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Added attachment {filename} to {issue_key}")
            return data[0] if data else {}

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

    async def get_labels(self, issue_key: str) -> list[str]:
        """Get labels for a Jira issue.

        Args:
            issue_key: The Jira issue key.

        Returns:
            List of label strings.
        """
        client = await self._get_client()
        response = await client.get(f"/issue/{issue_key}?fields=labels")
        response.raise_for_status()
        data = response.json()
        return data.get("fields", {}).get("labels", [])

    async def add_labels(self, issue_key: str, labels: list[str]) -> None:
        """Add labels to a Jira issue.

        Args:
            issue_key: The Jira issue key.
            labels: Labels to add.
        """
        client = await self._get_client()
        response = await client.put(
            f"/issue/{issue_key}",
            json={
                "update": {
                    "labels": [{"add": label} for label in labels]
                }
            },
        )
        response.raise_for_status()
        logger.info(f"Added labels {labels} to {issue_key}")

    async def remove_labels(self, issue_key: str, labels: list[str]) -> None:
        """Remove labels from a Jira issue.

        Args:
            issue_key: The Jira issue key.
            labels: Labels to remove.
        """
        client = await self._get_client()
        response = await client.put(
            f"/issue/{issue_key}",
            json={
                "update": {
                    "labels": [{"remove": label} for label in labels]
                }
            },
        )
        response.raise_for_status()
        logger.info(f"Removed labels {labels} from {issue_key}")

    async def set_workflow_label(
        self,
        issue_key: str,
        new_label: ForgeLabel,
        remove_prefix: str = "forge:",
    ) -> None:
        """Set a workflow label, removing other forge: labels.

        This is used to track Forge workflow state via labels instead of
        custom Jira statuses. Only one workflow label should be active at a time.

        Args:
            issue_key: The Jira issue key.
            new_label: The new workflow label to set.
            remove_prefix: Prefix of labels to remove (default: "forge:").
        """
        # Get current labels
        current_labels = await self.get_labels(issue_key)

        # Find forge: labels to remove (except the new one and forge:managed)
        labels_to_remove = [
            label for label in current_labels
            if label.startswith(remove_prefix)
            and label != new_label.value
            and label != ForgeLabel.FORGE_MANAGED.value
        ]

        # Build update operations
        operations: list[dict[str, str]] = []
        for label in labels_to_remove:
            operations.append({"remove": label})
        operations.append({"add": new_label.value})

        # Ensure forge:managed is set
        if ForgeLabel.FORGE_MANAGED.value not in current_labels:
            operations.append({"add": ForgeLabel.FORGE_MANAGED.value})

        client = await self._get_client()
        response = await client.put(
            f"/issue/{issue_key}",
            json={"update": {"labels": operations}},
        )
        response.raise_for_status()
        logger.info(
            f"Set workflow label {new_label.value} on {issue_key} "
            f"(removed: {labels_to_remove})"
        )

    async def add_structured_comment(
        self,
        issue_key: str,
        title: str,
        content: str,
        comment_type: str = "forge-artifact",
    ) -> JiraComment:
        """Add a structured comment with a marker for later retrieval.

        Used to store PRD/Spec content in comments when custom fields
        are not available.

        Args:
            issue_key: The Jira issue key.
            title: Title/header for the comment.
            content: Main content of the comment.
            comment_type: Type marker (e.g., 'prd', 'spec', 'plan').

        Returns:
            The created JiraComment.
        """
        # Format with markers for easy parsing
        formatted_body = (
            f"[FORGE:{comment_type.upper()}]\n"
            f"# {title}\n\n"
            f"{content}\n\n"
            f"[/FORGE:{comment_type.upper()}]"
        )
        return await self.add_comment(issue_key, formatted_body)

    async def get_structured_comment(
        self,
        issue_key: str,
        comment_type: str,
    ) -> str | None:
        """Get the latest structured comment of a specific type.

        Args:
            issue_key: The Jira issue key.
            comment_type: Type marker to search for.

        Returns:
            The comment content or None if not found.
        """
        comments = await self.get_comments(issue_key)
        marker_start = f"[FORGE:{comment_type.upper()}]"
        marker_end = f"[/FORGE:{comment_type.upper()}]"

        # Search in reverse order to get the latest
        for comment in reversed(comments):
            body = comment.body
            if marker_start in body and marker_end in body:
                # Extract content between markers
                start_idx = body.index(marker_start) + len(marker_start)
                end_idx = body.index(marker_end)
                return body[start_idx:end_idx].strip()

        return None

    @staticmethod
    def _text_to_adf(text: str) -> dict[str, Any]:
        """Convert markdown text to Atlassian Document Format.

        Supports: headings, bold, italic, code blocks, inline code,
        bullet lists, numbered lists, and links.

        Args:
            text: Markdown text content.

        Returns:
            ADF document structure.
        """
        import re

        content: list[dict[str, Any]] = []
        lines = text.split("\n") if text else []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Code block
            if line.startswith("```"):
                code_lines = []
                language = line[3:].strip() or None
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                content.append({
                    "type": "codeBlock",
                    "attrs": {"language": language} if language else {},
                    "content": [{"type": "text", "text": "\n".join(code_lines)}] if code_lines else [],
                })
                i += 1
                continue

            # Heading
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2)
                content.append({
                    "type": "heading",
                    "attrs": {"level": level},
                    "content": JiraClient._parse_inline_markdown(heading_text),
                })
                i += 1
                continue

            # Bullet list
            if re.match(r"^[\-\*]\s+", line):
                list_items = []
                while i < len(lines) and re.match(r"^[\-\*]\s+", lines[i]):
                    item_text = re.sub(r"^[\-\*]\s+", "", lines[i])
                    list_items.append({
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": JiraClient._parse_inline_markdown(item_text),
                        }],
                    })
                    i += 1
                content.append({
                    "type": "bulletList",
                    "content": list_items,
                })
                continue

            # Numbered list
            if re.match(r"^\d+\.\s+", line):
                list_items = []
                while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                    item_text = re.sub(r"^\d+\.\s+", "", lines[i])
                    list_items.append({
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": JiraClient._parse_inline_markdown(item_text),
                        }],
                    })
                    i += 1
                content.append({
                    "type": "orderedList",
                    "content": list_items,
                })
                continue

            # Table (lines starting with |)
            if line.strip().startswith("|") and line.strip().endswith("|"):
                table_rows: list[dict[str, Any]] = []
                is_first_row = True
                has_header = False

                while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                    row_line = lines[i].strip()

                    # Check if this is a separator row (|---|---|)
                    if re.match(r"^\|[\s\-:]+\|$", row_line.replace(" ", "")):
                        has_header = True
                        i += 1
                        continue

                    # Parse cells
                    cells = [cell.strip() for cell in row_line.split("|")[1:-1]]
                    cell_type = "tableHeader" if is_first_row and has_header is False else "tableCell"

                    # After we've processed the first row and found a separator,
                    # mark first row as header
                    if is_first_row and i + 1 < len(lines):
                        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                        if re.match(r"^\|[\s\-:]+\|$", next_line.replace(" ", "")):
                            cell_type = "tableHeader"

                    row_content = []
                    for cell in cells:
                        row_content.append({
                            "type": cell_type,
                            "attrs": {},
                            "content": [{
                                "type": "paragraph",
                                "content": JiraClient._parse_inline_markdown(cell),
                            }],
                        })

                    if row_content:
                        table_rows.append({
                            "type": "tableRow",
                            "content": row_content,
                        })

                    is_first_row = False
                    i += 1

                if table_rows:
                    content.append({
                        "type": "table",
                        "attrs": {
                            "isNumberColumnEnabled": False,
                            "layout": "default",
                        },
                        "content": table_rows,
                    })
                continue

            # Empty line - skip
            if not line.strip():
                i += 1
                continue

            # Regular paragraph - collect consecutive non-empty lines
            para_lines = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,6}\s|[\-\*]\s|\d+\.\s|```|\|)", lines[i]):
                para_lines.append(lines[i])
                i += 1

            if para_lines:
                content.append({
                    "type": "paragraph",
                    "content": JiraClient._parse_inline_markdown(" ".join(para_lines)),
                })

        return {
            "type": "doc",
            "version": 1,
            "content": content or [{"type": "paragraph", "content": []}],
        }

    @staticmethod
    def _parse_inline_markdown(text: str) -> list[dict[str, Any]]:
        """Parse inline markdown (bold, italic, code, links) to ADF content.

        Args:
            text: Text with inline markdown.

        Returns:
            List of ADF inline content nodes.
        """
        import re

        result: list[dict[str, Any]] = []
        # Pattern matches: **bold**, *italic*, `code`, [text](url)
        pattern = r"(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|\[(.+?)\]\((.+?)\))"

        last_end = 0
        for match in re.finditer(pattern, text):
            # Add text before match
            if match.start() > last_end:
                result.append({"type": "text", "text": text[last_end:match.start()]})

            full_match = match.group(0)
            if full_match.startswith("**"):
                # Bold
                result.append({
                    "type": "text",
                    "text": match.group(2),
                    "marks": [{"type": "strong"}],
                })
            elif full_match.startswith("*"):
                # Italic
                result.append({
                    "type": "text",
                    "text": match.group(3),
                    "marks": [{"type": "em"}],
                })
            elif full_match.startswith("`"):
                # Inline code
                result.append({
                    "type": "text",
                    "text": match.group(4),
                    "marks": [{"type": "code"}],
                })
            elif full_match.startswith("["):
                # Link
                result.append({
                    "type": "text",
                    "text": match.group(5),
                    "marks": [{"type": "link", "attrs": {"href": match.group(6)}}],
                })

            last_end = match.end()

        # Add remaining text
        if last_end < len(text):
            result.append({"type": "text", "text": text[last_end:]})

        return result if result else [{"type": "text", "text": text}]
