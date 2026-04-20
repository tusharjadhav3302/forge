"""Unit tests for ForgeAgent."""

from unittest.mock import AsyncMock, patch

import pytest

from forge.integrations.agents.agent import ForgeAgent


@pytest.mark.asyncio
async def test_answer_question():
    """ForgeAgent can answer questions about artifacts."""
    agent = ForgeAgent()

    with patch.object(agent, "run_task", new_callable=AsyncMock) as mock_run_task:
        mock_run_task.return_value = "Because of performance"

        answer = await agent.answer_question(
            question="Why REST?",
            artifact_content="# PRD\n\nWe use REST",
            context={
                "artifact_type": "prd",
                "generation_context": {"raw_requirements": "Build API"},
            },
        )

    assert "performance" in answer
    mock_run_task.assert_called_once()
    call_kwargs = mock_run_task.call_args
    assert call_kwargs.kwargs["task"] == "answer-question"

    await agent.close()


@pytest.mark.asyncio
async def test_answer_question_default_artifact_type():
    """ForgeAgent uses default artifact type when not provided."""
    agent = ForgeAgent()

    with patch.object(agent, "run_task", new_callable=AsyncMock) as mock_run_task:
        mock_run_task.return_value = "The answer"

        await agent.answer_question(
            question="What is this?",
            artifact_content="Some content",
            context={},  # No artifact_type provided
        )

    call_kwargs = mock_run_task.call_args
    # The prompt should use "document" as default artifact type
    assert call_kwargs.kwargs["context"]["artifact_type"] == "document"

    await agent.close()


@pytest.mark.asyncio
async def test_answer_question_empty_response():
    """ForgeAgent handles empty response gracefully."""
    agent = ForgeAgent()

    with patch.object(agent, "run_task", new_callable=AsyncMock) as mock_run_task:
        mock_run_task.return_value = ""

        answer = await agent.answer_question(
            question="Test?",
            artifact_content="Content",
            context={"artifact_type": "spec"},
        )

    assert answer == ""

    await agent.close()
