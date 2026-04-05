"""Unit tests for Jira client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from forge.integrations.jira.client import JiraClient
from forge.models.workflow import ForgeLabel


class TestJiraClientInit:
    """Tests for JiraClient initialization."""

    def test_creates_with_default_settings(self):
        """Client creates with default settings."""
        with patch("forge.integrations.jira.client.get_settings") as mock_settings:
            mock_settings.return_value.jira_base_url = "https://test.atlassian.net"
            mock_settings.return_value.jira_api_token = MagicMock()
            mock_settings.return_value.jira_api_token.get_secret_value.return_value = "token"
            mock_settings.return_value.jira_user_email = "test@example.com"

            client = JiraClient()

            assert client.base_url == "https://test.atlassian.net/rest/api/3"

    def test_creates_with_custom_settings(self):
        """Client creates with custom settings."""
        from forge.config import Settings

        settings = Settings(
            jira_base_url="https://custom.atlassian.net",
            jira_api_token="custom-token",
            jira_user_email="custom@example.com",
            jira_webhook_secret="secret",
            redis_url="redis://localhost:6379",
            github_token="token",
            github_webhook_secret="secret",
            anthropic_api_key="key",
        )

        client = JiraClient(settings=settings)

        assert "custom.atlassian.net" in client.base_url


class TestJiraClientGetIssue:
    """Tests for get_issue method."""

    @pytest.fixture
    def mock_client(self):
        """Create client with mocked HTTP."""
        with patch("forge.integrations.jira.client.get_settings") as mock_settings:
            mock_settings.return_value.jira_base_url = "https://test.atlassian.net"
            mock_settings.return_value.jira_api_token = MagicMock()
            mock_settings.return_value.jira_api_token.get_secret_value.return_value = "token"
            mock_settings.return_value.jira_user_email = "test@example.com"

            client = JiraClient()
            return client

    @pytest.mark.asyncio
    async def test_get_issue_success(self, mock_client):
        """Successfully retrieves issue."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "10001",
            "key": "TEST-123",
            "fields": {
                "issuetype": {"name": "Feature"},
                "status": {"name": "New"},
                "summary": "Test Issue",
                "description": {"type": "doc", "content": []},
                "labels": ["forge:managed"],
                "project": {"key": "TEST"},
            },
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(mock_client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            issue = await mock_client.get_issue("TEST-123")

        assert issue.key == "TEST-123"
        assert issue.issue_type == "Feature"


class TestJiraClientLabels:
    """Tests for label operations."""

    @pytest.fixture
    def mock_client(self):
        """Create client with mocked HTTP."""
        with patch("forge.integrations.jira.client.get_settings") as mock_settings:
            mock_settings.return_value.jira_base_url = "https://test.atlassian.net"
            mock_settings.return_value.jira_api_token = MagicMock()
            mock_settings.return_value.jira_api_token.get_secret_value.return_value = "token"
            mock_settings.return_value.jira_user_email = "test@example.com"

            client = JiraClient()
            return client

    @pytest.mark.asyncio
    async def test_get_labels(self, mock_client):
        """Successfully retrieves labels."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "fields": {"labels": ["forge:managed", "forge:prd-pending"]}
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(mock_client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            labels = await mock_client.get_labels("TEST-123")

        assert "forge:managed" in labels
        assert "forge:prd-pending" in labels

    @pytest.mark.asyncio
    async def test_add_labels(self, mock_client):
        """Successfully adds labels."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(mock_client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.put = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            await mock_client.add_labels("TEST-123", ["new-label"])

        mock_http.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_workflow_label_removes_old_forge_labels(self, mock_client):
        """set_workflow_label removes old forge labels."""
        # Mock get_labels to return current labels
        mock_client.get_labels = AsyncMock(
            return_value=["forge:managed", "forge:prd-pending", "other-label"]
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(mock_client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.put = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            await mock_client.set_workflow_label("TEST-123", ForgeLabel.PRD_APPROVED)

        # Check that the PUT was called with correct operations
        mock_http.put.assert_called_once()
        call_args = mock_http.put.call_args
        update_ops = call_args.kwargs["json"]["update"]["labels"]

        # Should remove prd-pending and add prd-approved
        remove_ops = [op for op in update_ops if "remove" in op]
        add_ops = [op for op in update_ops if "add" in op]

        assert any(op["remove"] == "forge:prd-pending" for op in remove_ops)
        assert any(op["add"] == ForgeLabel.PRD_APPROVED.value for op in add_ops)


class TestJiraClientADF:
    """Tests for ADF conversion."""

    def test_text_to_adf_simple_paragraph(self):
        """Simple text converts to ADF paragraph."""
        text = "This is a simple paragraph."

        adf = JiraClient._text_to_adf(text)

        assert adf["type"] == "doc"
        assert adf["version"] == 1
        assert len(adf["content"]) >= 1

    def test_text_to_adf_heading(self):
        """Markdown heading converts to ADF heading."""
        text = "# Heading 1"

        adf = JiraClient._text_to_adf(text)

        heading = adf["content"][0]
        assert heading["type"] == "heading"
        assert heading["attrs"]["level"] == 1

    def test_text_to_adf_bullet_list(self):
        """Markdown bullet list converts to ADF."""
        text = "- Item 1\n- Item 2\n- Item 3"

        adf = JiraClient._text_to_adf(text)

        bullet_list = adf["content"][0]
        assert bullet_list["type"] == "bulletList"
        assert len(bullet_list["content"]) == 3

    def test_text_to_adf_code_block(self):
        """Markdown code block converts to ADF."""
        text = "```python\ndef hello():\n    print('world')\n```"

        adf = JiraClient._text_to_adf(text)

        code_block = adf["content"][0]
        assert code_block["type"] == "codeBlock"

    def test_text_to_adf_inline_formatting(self):
        """Inline formatting converts correctly."""
        text = "This has **bold** and *italic* text."

        adf = JiraClient._text_to_adf(text)

        # Should have paragraph with inline marks
        assert adf["content"][0]["type"] == "paragraph"
