"""Unit tests for the orchestrator worker."""

import pytest
from unittest.mock import MagicMock

from forge.models.events import EventSource
from forge.orchestrator.worker import OrchestratorWorker
from forge.queue.models import QueueMessage


class TestQuestionDetection:
    """Tests for Q&A mode question detection."""

    @pytest.fixture
    def worker(self) -> OrchestratorWorker:
        """Create a worker instance for testing."""
        return OrchestratorWorker(consumer_name="test-worker")

    @pytest.fixture
    def base_message(self) -> QueueMessage:
        """Create a base queue message for testing."""
        return QueueMessage(
            message_id="1234567890-0",
            event_id="test-event-001",
            source=EventSource.JIRA,
            event_type="jira:issue_updated",
            ticket_key="TEST-123",
            payload={
                "issue": {
                    "key": "TEST-123",
                    "fields": {
                        "issuetype": {"name": "Feature"},
                    },
                },
            },
        )

    @pytest.fixture
    def base_state(self) -> dict:
        """Create a base workflow state for testing."""
        return {
            "ticket_key": "TEST-123",
            "ticket_type": "Feature",
            "current_node": "prd_approval_gate",
            "is_paused": True,
            "context": {},
        }

    def _make_message_with_comment(
        self, base_message: QueueMessage, comment_body: str
    ) -> QueueMessage:
        """Create a message with a comment in the payload."""
        payload = {
            **base_message.payload,
            "comment": {"body": comment_body},
            "changelog": {"items": []},
        }
        return QueueMessage(
            message_id=base_message.message_id,
            event_id=base_message.event_id,
            source=base_message.source,
            event_type="comment_created",
            ticket_key=base_message.ticket_key,
            payload=payload,
        )

    @pytest.mark.asyncio
    async def test_question_comment_sets_is_question_flag(
        self, worker: OrchestratorWorker, base_message: QueueMessage, base_state: dict
    ):
        """Comments starting with ? set is_question flag."""
        message = self._make_message_with_comment(base_message, "?Why REST instead of GraphQL?")

        result = await worker._handle_resume_event(message, base_state)

        assert result["is_question"] is True
        assert result["feedback_comment"] == "?Why REST instead of GraphQL?"
        assert result["revision_requested"] is False
        assert result["is_paused"] is False

    @pytest.mark.asyncio
    async def test_forge_ask_comment_sets_is_question_flag(
        self, worker: OrchestratorWorker, base_message: QueueMessage, base_state: dict
    ):
        """Comments with @forge ask set is_question flag."""
        message = self._make_message_with_comment(
            base_message, "@forge ask explain the database choice"
        )

        result = await worker._handle_resume_event(message, base_state)

        assert result["is_question"] is True
        assert result["feedback_comment"] == "@forge ask explain the database choice"
        assert result["revision_requested"] is False
        assert result["is_paused"] is False

    @pytest.mark.asyncio
    async def test_normal_feedback_still_works(
        self, worker: OrchestratorWorker, base_message: QueueMessage, base_state: dict
    ):
        """Normal feedback comments still trigger revision_requested."""
        message = self._make_message_with_comment(
            base_message, "Please add more detail to the security section"
        )

        result = await worker._handle_resume_event(message, base_state)

        assert result.get("is_question") is not True
        assert result["revision_requested"] is True
        assert result["feedback_comment"] == "Please add more detail to the security section"
        assert result["is_paused"] is False

    @pytest.mark.asyncio
    async def test_prd_label_change_to_approved_sets_approved_flag(
        self, worker: OrchestratorWorker, base_message: QueueMessage, base_state: dict
    ):
        """Approval is detected via label change from pending to approved, not comment text."""
        payload = {
            **base_message.payload,
            "changelog": {
                "items": [
                    {
                        "field": "labels",
                        "fromString": "forge:managed forge:prd-pending",
                        "toString": "forge:managed forge:prd-approved",
                    }
                ]
            },
        }
        message = QueueMessage(
            message_id=base_message.message_id,
            event_id=base_message.event_id,
            source=base_message.source,
            event_type="jira:issue_updated",
            ticket_key=base_message.ticket_key,
            payload=payload,
        )

        result = await worker._handle_resume_event(message, base_state)

        assert result.get("is_question") is not True
        assert result["revision_requested"] is False
        assert result["is_paused"] is False

    @pytest.mark.asyncio
    async def test_question_with_leading_whitespace(
        self, worker: OrchestratorWorker, base_message: QueueMessage, base_state: dict
    ):
        """Questions with leading whitespace are still detected."""
        message = self._make_message_with_comment(base_message, "  ?What about caching?")

        result = await worker._handle_resume_event(message, base_state)

        assert result["is_question"] is True
        assert result["revision_requested"] is False

    @pytest.mark.asyncio
    async def test_forge_ask_case_insensitive(
        self, worker: OrchestratorWorker, base_message: QueueMessage, base_state: dict
    ):
        """@forge ask detection is case insensitive."""
        message = self._make_message_with_comment(
            base_message, "@FORGE ASK why use microservices?"
        )

        result = await worker._handle_resume_event(message, base_state)

        assert result["is_question"] is True
        assert result["revision_requested"] is False
