"""Tests for Q&A summary utility."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge.workflow.utils.qa_summary import post_qa_summary_if_needed


class TestPostQaSummaryIfNeeded:
    """Test cases for the post_qa_summary_if_needed function."""

    @pytest.mark.asyncio
    async def test_posts_summary_when_qa_exists_for_artifact_type(self) -> None:
        """Should post a summary comment when Q&A exists for the artifact type."""
        qa_history = [
            {
                "artifact_type": "prd",
                "question": "Why use REST over GraphQL?",
                "answer": "REST is simpler for this use case.",
            },
            {
                "artifact_type": "prd",
                "question": "What about caching?",
                "answer": "We will use Redis for caching.",
            },
        ]

        with patch("forge.workflow.utils.qa_summary.JiraClient") as mock_jira_cls:
            mock_jira = MagicMock()
            mock_jira.add_comment = AsyncMock()
            mock_jira.close = AsyncMock()
            mock_jira_cls.return_value = mock_jira

            await post_qa_summary_if_needed("TEST-123", qa_history, "prd")

            mock_jira.add_comment.assert_called_once()
            call_args = mock_jira.add_comment.call_args
            assert call_args[0][0] == "TEST-123"
            # Check that the comment contains the Q&A content
            comment_body = call_args[0][1]
            assert "*Q&A Summary for PRD*" in comment_body
            assert "*Q1:* Why use REST over GraphQL?" in comment_body
            assert "*A1:* REST is simpler for this use case." in comment_body
            assert "*Q2:* What about caching?" in comment_body
            assert "*A2:* We will use Redis for caching." in comment_body
            mock_jira.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_when_no_qa_for_artifact_type(self) -> None:
        """Should not post anything when no Q&A exists for the artifact type."""
        qa_history = [
            {
                "artifact_type": "spec",
                "question": "How does this work?",
                "answer": "It uses async processing.",
            },
        ]

        with patch("forge.workflow.utils.qa_summary.JiraClient") as mock_jira_cls:
            mock_jira = MagicMock()
            mock_jira.add_comment = AsyncMock()
            mock_jira.close = AsyncMock()
            mock_jira_cls.return_value = mock_jira

            # Request PRD summary but only spec Q&A exists
            await post_qa_summary_if_needed("TEST-123", qa_history, "prd")

            # Should not have called add_comment
            mock_jira.add_comment.assert_not_called()
            # Should not have created client at all (early return)
            mock_jira_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_qa_history_empty(self) -> None:
        """Should not post anything when Q&A history is empty."""
        with patch("forge.workflow.utils.qa_summary.JiraClient") as mock_jira_cls:
            await post_qa_summary_if_needed("TEST-123", [], "prd")

            # Should not have created client (early return)
            mock_jira_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_jira_errors_gracefully(self) -> None:
        """Should log warning but not raise when Jira fails."""
        qa_history = [
            {
                "artifact_type": "prd",
                "question": "Test question?",
                "answer": "Test answer.",
            },
        ]

        with patch("forge.workflow.utils.qa_summary.JiraClient") as mock_jira_cls:
            mock_jira = MagicMock()
            mock_jira.add_comment = AsyncMock(side_effect=Exception("Jira error"))
            mock_jira.close = AsyncMock()
            mock_jira_cls.return_value = mock_jira

            # Should not raise
            await post_qa_summary_if_needed("TEST-123", qa_history, "prd")

            mock_jira.add_comment.assert_called_once()
            # Close should still be called in finally block
            mock_jira.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_filters_to_matching_artifact_type_only(self) -> None:
        """Should only include Q&A for the specified artifact type."""
        qa_history = [
            {
                "artifact_type": "prd",
                "question": "PRD question?",
                "answer": "PRD answer.",
            },
            {
                "artifact_type": "spec",
                "question": "Spec question?",
                "answer": "Spec answer.",
            },
            {
                "artifact_type": "prd",
                "question": "Another PRD question?",
                "answer": "Another PRD answer.",
            },
        ]

        with patch("forge.workflow.utils.qa_summary.JiraClient") as mock_jira_cls:
            mock_jira = MagicMock()
            mock_jira.add_comment = AsyncMock()
            mock_jira.close = AsyncMock()
            mock_jira_cls.return_value = mock_jira

            await post_qa_summary_if_needed("TEST-123", qa_history, "prd")

            call_args = mock_jira.add_comment.call_args
            comment_body = call_args[0][1]
            # Should include PRD questions
            assert "PRD question?" in comment_body
            assert "Another PRD question?" in comment_body
            # Should not include spec questions
            assert "Spec question?" not in comment_body
