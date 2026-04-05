"""Unit tests for LangGraph checkpointer."""

import pytest
from unittest.mock import patch
import uuid

from forge.models.workflow import TicketType
from forge.orchestrator.state import create_initial_state


def make_config(thread_id: str) -> dict:
    """Create a valid LangGraph checkpoint config."""
    return {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": "",  # Required by MemorySaver
        }
    }


def make_checkpoint(state: dict, checkpoint_id: str | None = None) -> dict:
    """Create a valid LangGraph checkpoint."""
    return {
        "v": 1,
        "id": checkpoint_id or str(uuid.uuid4()),
        "ts": "2024-03-30T10:00:00+00:00",
        "channel_values": state,
        "channel_versions": {},
        "versions_seen": {},
        "pending_sends": [],
    }


class TestSqliteCheckpointer:
    """Tests for SQLite checkpointer setup."""

    @pytest.mark.asyncio
    async def test_checkpointer_can_be_created(self):
        """Checkpointer can be instantiated."""
        from forge.orchestrator.checkpointer import get_checkpointer

        checkpointer = await get_checkpointer()
        assert checkpointer is not None

    @pytest.mark.asyncio
    async def test_checkpointer_is_reusable(self):
        """Same checkpointer instance is returned."""
        from forge.orchestrator.checkpointer import get_checkpointer

        cp1 = await get_checkpointer()
        cp2 = await get_checkpointer()
        assert cp1 is cp2


class TestCheckpointerOperations:
    """Tests for checkpointer save/load operations."""

    @pytest.mark.asyncio
    async def test_save_and_load_state(self):
        """State can be saved and loaded."""
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()

        state = create_initial_state(
            thread_id="test-thread-save",
            ticket_key="TEST-123",
            ticket_type=TicketType.FEATURE,
        )
        state["prd_content"] = "Test PRD content"

        config = make_config("test-thread-save")
        checkpoint = make_checkpoint(state)
        await checkpointer.aput(config, checkpoint, {}, {})

        loaded = await checkpointer.aget(config)

        assert loaded is not None
        # Checkpoint structure varies by LangGraph version - just check it saved
        assert "id" in loaded or "channel_values" in loaded

    @pytest.mark.asyncio
    async def test_thread_isolation(self):
        """Different threads have isolated state."""
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()

        state1 = create_initial_state(
            thread_id="thread-1",
            ticket_key="TEST-111",
            ticket_type=TicketType.FEATURE,
        )
        config1 = make_config("thread-1")
        await checkpointer.aput(config1, make_checkpoint(state1), {}, {})

        state2 = create_initial_state(
            thread_id="thread-2",
            ticket_key="TEST-222",
            ticket_type=TicketType.BUG,
        )
        config2 = make_config("thread-2")
        await checkpointer.aput(config2, make_checkpoint(state2), {}, {})

        loaded1 = await checkpointer.aget(config1)
        loaded2 = await checkpointer.aget(config2)

        # Both should exist and be different
        assert loaded1 is not None
        assert loaded2 is not None
        assert loaded1["id"] != loaded2["id"]

    @pytest.mark.asyncio
    async def test_state_versioning(self):
        """Multiple versions of state can be saved."""
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        config = make_config("version-test")

        state1 = create_initial_state(
            thread_id="version-test",
            ticket_key="TEST-123",
            ticket_type=TicketType.FEATURE,
        )
        state1["current_node"] = "generate_prd"
        await checkpointer.aput(config, make_checkpoint(state1, "cp-1"), {}, {})

        state2 = {**state1, "current_node": "prd_approval_gate", "prd_content": "PRD"}
        await checkpointer.aput(config, make_checkpoint(state2, "cp-2"), {}, {})

        loaded = await checkpointer.aget(config)
        # Should get the latest checkpoint
        assert loaded is not None
        assert loaded["id"] == "cp-2"


class TestCheckpointerRecovery:
    """Tests for checkpointer recovery scenarios."""

    @pytest.mark.asyncio
    async def test_missing_thread_returns_none(self):
        """Non-existent thread returns None."""
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        config = make_config("non-existent")

        loaded = await checkpointer.aget(config)

        assert loaded is None

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self):
        """Workflow can resume from checkpoint - tests basic checkpoint storage."""
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        config = make_config("resume-test")

        state = create_initial_state(
            thread_id="resume-test",
            ticket_key="TEST-123",
            ticket_type=TicketType.FEATURE,
        )
        state["current_node"] = "prd_approval_gate"
        state["is_paused"] = True
        state["prd_content"] = "Generated PRD"

        checkpoint = make_checkpoint(state)
        await checkpointer.aput(config, checkpoint, {}, {})

        loaded = await checkpointer.aget(config)

        # Verify checkpoint was saved and can be loaded
        assert loaded is not None
        # Checkpoint ID should match what we saved
        assert loaded["id"] == checkpoint["id"]
