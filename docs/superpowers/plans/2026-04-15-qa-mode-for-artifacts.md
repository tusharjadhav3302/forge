# Q&A Mode for Generated Artifacts - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable users to ask questions about generated PRDs and specs without triggering regeneration, using `?` or `@forge ask` prefix.

**Architecture:** Add comment classification to detect questions, store generation context during artifact creation, and route questions to a new `answer_question` node that responds without advancing the workflow.

**Tech Stack:** Python, LangGraph, Jira API, ForgeAgent

**Design Decisions (from proposal review):**
- Generation history retained until workflow completion (not just approval)
- Q&A exchanges stored as structured Jira comment on approval
- No "summarize all Q&A" option for MVP
- Support both `?` and `@forge ask` prefixes

---

## Task 1: Add Comment Classification Function

**Files:**
- Create: `src/forge/workflow/utils/comment_classifier.py`
- Test: `tests/unit/workflow/test_comment_classifier.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/workflow/test_comment_classifier.py
"""Tests for comment classification."""

import pytest
from forge.workflow.utils.comment_classifier import classify_comment, CommentType


class TestClassifyComment:
    """Tests for classify_comment function."""

    def test_question_with_question_mark_prefix(self):
        """Comments starting with ? are questions."""
        assert classify_comment("?Why did you choose REST?") == CommentType.QUESTION
        assert classify_comment("? Why this approach") == CommentType.QUESTION

    def test_question_with_forge_ask_prefix(self):
        """Comments starting with @forge ask are questions."""
        assert classify_comment("@forge ask why microservices?") == CommentType.QUESTION
        assert classify_comment("@Forge Ask explain the tradeoff") == CommentType.QUESTION

    def test_approval_keywords(self):
        """Comments with approval keywords are approvals."""
        assert classify_comment("Approved") == CommentType.APPROVAL
        assert classify_comment("LGTM") == CommentType.APPROVAL
        assert classify_comment("looks good to me") == CommentType.APPROVAL

    def test_feedback_is_default(self):
        """Other comments are treated as feedback."""
        assert classify_comment("Please add more detail") == CommentType.FEEDBACK
        assert classify_comment("This needs work") == CommentType.FEEDBACK

    def test_empty_comment(self):
        """Empty comments are feedback."""
        assert classify_comment("") == CommentType.FEEDBACK
        assert classify_comment("   ") == CommentType.FEEDBACK

    def test_question_mark_in_middle_is_feedback(self):
        """Question marks not at start are feedback, not questions."""
        assert classify_comment("What about this? Add more") == CommentType.FEEDBACK
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/workflow/test_comment_classifier.py -v`
Expected: FAIL with "No module named 'forge.workflow.utils.comment_classifier'"

- [ ] **Step 3: Create the comment classifier module**

```python
# src/forge/workflow/utils/comment_classifier.py
"""Comment classification for Q&A mode."""

from enum import StrEnum


class CommentType(StrEnum):
    """Types of comments that can be made on artifacts."""

    QUESTION = "question"
    APPROVAL = "approval"
    FEEDBACK = "feedback"


def classify_comment(comment_text: str) -> CommentType:
    """Classify a Jira comment to determine how to handle it.

    Args:
        comment_text: The raw comment text.

    Returns:
        CommentType indicating how to process this comment.
    """
    text = comment_text.strip()

    if not text:
        return CommentType.FEEDBACK

    # Check for explicit question markers (must be at start)
    lower_text = text.lower()
    if text.startswith("?") or lower_text.startswith("@forge ask"):
        return CommentType.QUESTION

    # Check for approval keywords
    approval_keywords = ("approved", "lgtm", "looks good to me", "looks good")
    if any(keyword in lower_text for keyword in approval_keywords):
        return CommentType.APPROVAL

    # Default to feedback
    return CommentType.FEEDBACK
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/workflow/test_comment_classifier.py -v`
Expected: PASS

- [ ] **Step 5: Export from utils package**

Update `src/forge/workflow/utils/__init__.py` to add:
```python
from forge.workflow.utils.comment_classifier import CommentType, classify_comment
```

- [ ] **Step 6: Commit**

```bash
git add src/forge/workflow/utils/comment_classifier.py tests/unit/workflow/test_comment_classifier.py src/forge/workflow/utils/__init__.py
git commit -m "feat(qa-mode): add comment classification for questions"
```

---

## Task 2: Add Q&A State Fields to Workflow States

**Files:**
- Modify: `src/forge/workflow/feature/state.py`
- Modify: `src/forge/workflow/bug/state.py`
- Test: `tests/unit/workflow/test_state.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/workflow/test_state.py

class TestQAStateFields:
    """Tests for Q&A mode state fields."""

    def test_feature_state_has_qa_fields(self):
        """Feature state includes Q&A tracking fields."""
        state = create_initial_feature_state("TEST-123")
        assert "qa_history" in state
        assert state["qa_history"] == []
        assert "generation_context" in state
        assert state["generation_context"] == {}

    def test_bug_state_has_qa_fields(self):
        """Bug state includes Q&A tracking fields."""
        state = create_initial_bug_state("TEST-456")
        assert "qa_history" in state
        assert state["qa_history"] == []
        assert "generation_context" in state
        assert state["generation_context"] == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/workflow/test_state.py::TestQAStateFields -v`
Expected: FAIL with KeyError

- [ ] **Step 3: Add Q&A fields to FeatureState**

In `src/forge/workflow/feature/state.py`, add to `FeatureState` class:
```python
    # Q&A mode
    qa_history: list[dict[str, str]]  # List of {question, answer, timestamp}
    generation_context: dict[str, Any]  # Stored context from generation
```

And add defaults in `create_initial_feature_state`:
```python
        "qa_history": [],
        "generation_context": {},
```

- [ ] **Step 4: Add Q&A fields to BugState**

In `src/forge/workflow/bug/state.py`, add same fields to `BugState` and `create_initial_bug_state`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/workflow/test_state.py::TestQAStateFields -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/forge/workflow/feature/state.py src/forge/workflow/bug/state.py tests/unit/workflow/test_state.py
git commit -m "feat(qa-mode): add Q&A state fields to workflow states"
```

---

## Task 3: Store Generation Context During PRD/Spec Creation

**Files:**
- Modify: `src/forge/workflow/nodes/prd_generation.py`
- Modify: `src/forge/workflow/nodes/spec_generation.py`
- Test: `tests/unit/workflow/nodes/test_prd_generation.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/workflow/nodes/test_prd_generation.py

@pytest.mark.asyncio
async def test_generate_prd_stores_generation_context(
    mock_jira_client, mock_forge_agent
):
    """PRD generation stores context for Q&A mode."""
    state = create_initial_feature_state("TEST-123")

    with patch("forge.workflow.nodes.prd_generation.JiraClient", return_value=mock_jira_client):
        with patch("forge.workflow.nodes.prd_generation.ForgeAgent", return_value=mock_forge_agent):
            result = await generate_prd(state)

    # Verify generation context is stored
    assert "generation_context" in result
    context = result["generation_context"]
    assert "prd" in context
    assert "raw_requirements" in context["prd"]
    assert "generated_at" in context["prd"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/workflow/nodes/test_prd_generation.py::test_generate_prd_stores_generation_context -v`
Expected: FAIL

- [ ] **Step 3: Update generate_prd to store context**

In `src/forge/workflow/nodes/prd_generation.py`, after successful generation, store the context:

```python
        # Store generation context for Q&A mode
        generation_context = state.get("generation_context", {})
        generation_context["prd"] = {
            "raw_requirements": raw_requirements,
            "summary": issue.summary,
            "generated_at": datetime.utcnow().isoformat(),
        }

        return update_state_timestamp({
            **state,
            "prd_content": prd_content,
            "generation_context": generation_context,
            "current_node": "prd_approval_gate",
            # ... rest of state
        })
```

- [ ] **Step 4: Update generate_spec similarly**

Apply same pattern to `src/forge/workflow/nodes/spec_generation.py`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/workflow/nodes/test_prd_generation.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/forge/workflow/nodes/prd_generation.py src/forge/workflow/nodes/spec_generation.py tests/unit/workflow/nodes/test_prd_generation.py
git commit -m "feat(qa-mode): store generation context during PRD/spec creation"
```

---

## Task 4: Create Answer Question Node

**Files:**
- Create: `src/forge/workflow/nodes/qa_handler.py`
- Test: `tests/unit/workflow/nodes/test_qa_handler.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/workflow/nodes/test_qa_handler.py
"""Tests for Q&A handler node."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from forge.workflow.nodes.qa_handler import answer_question, extract_question_text
from forge.workflow.feature.state import create_initial_feature_state


class TestExtractQuestionText:
    """Tests for extract_question_text helper."""

    def test_strips_question_mark_prefix(self):
        """Removes ? prefix from question."""
        assert extract_question_text("?Why REST?") == "Why REST?"
        assert extract_question_text("? Why this") == "Why this"

    def test_strips_forge_ask_prefix(self):
        """Removes @forge ask prefix from question."""
        assert extract_question_text("@forge ask why this") == "why this"
        assert extract_question_text("@Forge Ask explain") == "explain"


class TestAnswerQuestion:
    """Tests for answer_question node."""

    @pytest.mark.asyncio
    async def test_answer_question_posts_to_jira(self, mock_jira_client, mock_forge_agent):
        """Answer is posted as Jira comment."""
        state = create_initial_feature_state("TEST-123")
        state["current_node"] = "prd_approval_gate"
        state["is_paused"] = True
        state["prd_content"] = "# PRD\n\nTest content"
        state["feedback_comment"] = "?Why did you choose REST?"
        state["generation_context"] = {"prd": {"raw_requirements": "Build an API"}}

        mock_forge_agent.answer_question = AsyncMock(return_value="REST was chosen because...")

        with patch("forge.workflow.nodes.qa_handler.JiraClient", return_value=mock_jira_client):
            with patch("forge.workflow.nodes.qa_handler.ForgeAgent", return_value=mock_forge_agent):
                result = await answer_question(state)

        # Should post answer to Jira
        mock_jira_client.add_comment.assert_called_once()
        comment_text = mock_jira_client.add_comment.call_args[0][1]
        assert "REST was chosen" in comment_text

    @pytest.mark.asyncio
    async def test_answer_question_stays_paused(self, mock_jira_client, mock_forge_agent):
        """Workflow stays paused after answering question."""
        state = create_initial_feature_state("TEST-123")
        state["current_node"] = "prd_approval_gate"
        state["is_paused"] = True
        state["prd_content"] = "# PRD"
        state["feedback_comment"] = "?Why this?"

        mock_forge_agent.answer_question = AsyncMock(return_value="Because...")

        with patch("forge.workflow.nodes.qa_handler.JiraClient", return_value=mock_jira_client):
            with patch("forge.workflow.nodes.qa_handler.ForgeAgent", return_value=mock_forge_agent):
                result = await answer_question(state)

        # Should stay at same node and remain paused
        assert result["current_node"] == "prd_approval_gate"
        assert result["is_paused"] is True

    @pytest.mark.asyncio
    async def test_answer_question_records_history(self, mock_jira_client, mock_forge_agent):
        """Q&A exchange is recorded in state."""
        state = create_initial_feature_state("TEST-123")
        state["current_node"] = "prd_approval_gate"
        state["is_paused"] = True
        state["prd_content"] = "# PRD"
        state["feedback_comment"] = "?Why REST?"
        state["qa_history"] = []

        mock_forge_agent.answer_question = AsyncMock(return_value="Because of X")

        with patch("forge.workflow.nodes.qa_handler.JiraClient", return_value=mock_jira_client):
            with patch("forge.workflow.nodes.qa_handler.ForgeAgent", return_value=mock_forge_agent):
                result = await answer_question(state)

        # Should record Q&A in history
        assert len(result["qa_history"]) == 1
        assert result["qa_history"][0]["question"] == "Why REST?"
        assert result["qa_history"][0]["answer"] == "Because of X"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/workflow/nodes/test_qa_handler.py -v`
Expected: FAIL with "No module named"

- [ ] **Step 3: Create the Q&A handler node**

```python
# src/forge/workflow/nodes/qa_handler.py
"""Q&A handler node for answering questions about generated artifacts."""

import logging
from datetime import datetime
from typing import Any

from forge.config import get_settings
from forge.integrations.agents import ForgeAgent
from forge.integrations.jira.client import JiraClient
from forge.workflow.feature.state import FeatureState as WorkflowState
from forge.workflow.utils import update_state_timestamp

logger = logging.getLogger(__name__)


def extract_question_text(comment: str) -> str:
    """Extract the actual question from a comment with Q&A prefix.

    Args:
        comment: Raw comment text with ? or @forge ask prefix.

    Returns:
        The question text without the prefix.
    """
    text = comment.strip()

    if text.startswith("?"):
        return text[1:].strip()

    lower = text.lower()
    if lower.startswith("@forge ask"):
        return text[10:].strip()

    return text


async def answer_question(state: WorkflowState) -> WorkflowState:
    """Answer a question about a generated artifact without advancing workflow.

    This node:
    1. Extracts the question from feedback_comment
    2. Loads generation context and current artifact
    3. Uses Claude to generate an answer
    4. Posts answer as Jira comment
    5. Records Q&A in state history
    6. Returns to the same gate (stays paused)

    Args:
        state: Current workflow state with feedback_comment containing question.

    Returns:
        Updated state with Q&A recorded, still paused at current gate.
    """
    ticket_key = state["ticket_key"]
    current_node = state.get("current_node", "")
    question_raw = state.get("feedback_comment", "")

    if not question_raw:
        logger.warning(f"No question found for {ticket_key}")
        return state

    question = extract_question_text(question_raw)
    logger.info(f"Answering question for {ticket_key}: {question[:100]}...")

    jira = JiraClient()
    agent = ForgeAgent()

    try:
        # Determine which artifact we're discussing
        artifact_type = _determine_artifact_type(current_node)
        artifact_content = _get_artifact_content(state, artifact_type)
        generation_context = state.get("generation_context", {}).get(artifact_type, {})

        # Build prompt context
        prompt_context = {
            "artifact_type": artifact_type,
            "artifact_content": artifact_content,
            "generation_context": generation_context,
            "question": question,
            "ticket_key": ticket_key,
        }

        # Generate answer
        answer = await agent.answer_question(
            question=question,
            artifact_content=artifact_content,
            context=prompt_context,
        )

        # Post answer to Jira
        formatted_answer = f"*Q: {question}*\n\n{answer}"
        await jira.add_comment(ticket_key, formatted_answer)

        # Record in Q&A history
        qa_history = state.get("qa_history", [])
        qa_history.append({
            "question": question,
            "answer": answer,
            "artifact_type": artifact_type,
            "timestamp": datetime.utcnow().isoformat(),
        })

        logger.info(f"Answered question for {ticket_key}")

        # Stay at current gate, remain paused
        return update_state_timestamp({
            **state,
            "qa_history": qa_history,
            "feedback_comment": None,  # Clear the question
            "revision_requested": False,  # This wasn't a revision request
            "is_paused": True,
            "current_node": current_node,
        })

    except Exception as e:
        logger.error(f"Failed to answer question for {ticket_key}: {e}")
        # On error, post apology and stay paused
        try:
            await jira.add_comment(
                ticket_key,
                f"I wasn't able to answer that question. Error: {e}\n\n"
                "Please try rephrasing or ask a different question.",
            )
        except Exception:
            pass

        return update_state_timestamp({
            **state,
            "feedback_comment": None,
            "revision_requested": False,
            "is_paused": True,
            "current_node": current_node,
        })
    finally:
        await jira.close()
        await agent.close()


def _determine_artifact_type(current_node: str) -> str:
    """Determine which artifact type based on current workflow node.

    Args:
        current_node: Current workflow node name.

    Returns:
        Artifact type: 'prd', 'spec', 'rca', etc.
    """
    if "prd" in current_node.lower():
        return "prd"
    elif "spec" in current_node.lower():
        return "spec"
    elif "rca" in current_node.lower():
        return "rca"
    elif "plan" in current_node.lower():
        return "plan"
    else:
        return "unknown"


def _get_artifact_content(state: WorkflowState, artifact_type: str) -> str:
    """Get the content of the relevant artifact.

    Args:
        state: Current workflow state.
        artifact_type: Type of artifact to get.

    Returns:
        Artifact content string.
    """
    mapping = {
        "prd": "prd_content",
        "spec": "spec_content",
        "rca": "rca_content",
    }
    field = mapping.get(artifact_type)
    if field:
        return state.get(field, "")
    return ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/workflow/nodes/test_qa_handler.py -v`
Expected: PASS

- [ ] **Step 5: Export from nodes package**

Update `src/forge/workflow/nodes/__init__.py` to add:
```python
from forge.workflow.nodes.qa_handler import answer_question
```

- [ ] **Step 6: Commit**

```bash
git add src/forge/workflow/nodes/qa_handler.py tests/unit/workflow/nodes/test_qa_handler.py src/forge/workflow/nodes/__init__.py
git commit -m "feat(qa-mode): add answer_question node for Q&A handling"
```

---

## Task 5: Add answer_question Method to ForgeAgent

**Files:**
- Modify: `src/forge/integrations/agents/agent.py`
- Create: `src/forge/prompts/v1/answer-question.md`
- Test: `tests/unit/integrations/test_agent.py`

- [ ] **Step 1: Create the prompt template**

```markdown
# src/forge/prompts/v1/answer-question.md
You are answering a question about a {artifact_type} document you previously generated.

## The {artifact_type}

{artifact_content}

## Generation Context

When generating this document, the original requirements were:
{raw_requirements}

## Question

{question}

## Instructions

Answer the question based on:
1. The content of the document itself
2. Your reasoning during generation
3. Standard software engineering principles

Be concise but thorough. If you made a specific tradeoff, explain why.
If the question asks about something not covered in the document, say so.

Format your answer in clear prose. Do not use excessive formatting.
```

- [ ] **Step 2: Add answer_question method to ForgeAgent**

In `src/forge/integrations/agents/agent.py`, add:

```python
    async def answer_question(
        self,
        question: str,
        artifact_content: str,
        context: dict[str, Any],
    ) -> str:
        """Answer a question about a generated artifact.

        Args:
            question: The user's question.
            artifact_content: The content of the artifact being discussed.
            context: Additional context including generation history.

        Returns:
            The answer to the question.
        """
        artifact_type = context.get("artifact_type", "document")
        generation_context = context.get("generation_context", {})
        raw_requirements = generation_context.get("raw_requirements", "Not available")

        prompt = load_prompt(
            "answer-question",
            artifact_type=artifact_type,
            artifact_content=artifact_content,
            raw_requirements=raw_requirements,
            question=question,
        )

        response = await self._run_completion(prompt)
        return response.strip()
```

- [ ] **Step 3: Write test for answer_question**

```python
# Add to tests/unit/integrations/test_agent.py

@pytest.mark.asyncio
async def test_answer_question():
    """ForgeAgent can answer questions about artifacts."""
    agent = ForgeAgent()

    with patch.object(agent, "_run_completion", return_value="Because of X"):
        answer = await agent.answer_question(
            question="Why REST?",
            artifact_content="# PRD\n\nWe use REST",
            context={"artifact_type": "prd", "generation_context": {}},
        )

    assert answer == "Because of X"
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/integrations/test_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/forge/integrations/agents/agent.py src/forge/prompts/v1/answer-question.md tests/unit/integrations/test_agent.py
git commit -m "feat(qa-mode): add answer_question method to ForgeAgent"
```

---

## Task 6: Update Worker to Detect Questions and Route Appropriately

**Files:**
- Modify: `src/forge/orchestrator/worker.py`
- Test: `tests/unit/orchestrator/test_worker.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/orchestrator/test_worker.py

class TestQuestionDetection:
    """Tests for Q&A mode question detection."""

    @pytest.mark.asyncio
    async def test_question_comment_sets_is_question_flag(self):
        """Comments starting with ? set is_question flag."""
        worker = OrchestratorWorker()

        current_state = {
            "ticket_key": "TEST-123",
            "current_node": "prd_approval_gate",
            "is_paused": True,
        }

        message = QueueMessage(
            event_id="evt-1",
            source=EventSource.JIRA,
            event_type="comment_created",
            ticket_key="TEST-123",
            payload={
                "comment": {"body": "?Why did you choose REST?"}
            },
            retry_count=0,
        )

        result = await worker._handle_resume_event(message, current_state)

        assert result.get("is_question") is True
        assert result.get("revision_requested") is False

    @pytest.mark.asyncio
    async def test_forge_ask_comment_sets_is_question_flag(self):
        """Comments starting with @forge ask set is_question flag."""
        worker = OrchestratorWorker()

        current_state = {
            "ticket_key": "TEST-123",
            "current_node": "prd_approval_gate",
            "is_paused": True,
        }

        message = QueueMessage(
            event_id="evt-1",
            source=EventSource.JIRA,
            event_type="comment_created",
            ticket_key="TEST-123",
            payload={
                "comment": {"body": "@forge ask explain this"}
            },
            retry_count=0,
        )

        result = await worker._handle_resume_event(message, current_state)

        assert result.get("is_question") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/orchestrator/test_worker.py::TestQuestionDetection -v`
Expected: FAIL

- [ ] **Step 3: Update _handle_resume_event to detect questions**

In `src/forge/orchestrator/worker.py`, in the `_handle_resume_event` method, add question detection after extracting the comment:

```python
        from forge.workflow.utils.comment_classifier import classify_comment, CommentType

        # Check for comment and classify it
        is_question = False
        if comment:
            comment_body = comment.get("body", "")
            if isinstance(comment_body, dict):
                comment_body = self._extract_text_from_adf(comment_body)

            if comment_body.strip():
                comment_type = classify_comment(comment_body)

                if comment_type == CommentType.QUESTION:
                    is_question = True
                    feedback = comment_body  # Keep full text for question
                    logger.info(f"Detected question comment: {feedback[:100]}...")
                elif comment_type == CommentType.APPROVAL:
                    # Handle as approval (existing logic)
                    pass
                else:
                    # Treat as feedback for rejection (existing logic)
                    is_rejected = True
                    feedback = comment_body
```

And in the updated_state building:

```python
        if is_question:
            updated_state["is_question"] = True
            updated_state["feedback_comment"] = feedback
            updated_state["revision_requested"] = False
            updated_state["is_paused"] = False  # Unpause to process question
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/orchestrator/test_worker.py::TestQuestionDetection -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/forge/orchestrator/worker.py tests/unit/orchestrator/test_worker.py
git commit -m "feat(qa-mode): detect question comments in worker"
```

---

## Task 7: Add Routing for Questions in Approval Gates

**Files:**
- Modify: `src/forge/workflow/gates/prd_approval.py`
- Modify: `src/forge/workflow/gates/spec_approval.py`
- Modify: `src/forge/workflow/gates/plan_approval.py`
- Test: `tests/unit/workflow/gates/test_prd_approval.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/workflow/gates/test_prd_approval.py

class TestRouteWithQuestions:
    """Tests for Q&A routing in PRD approval gate."""

    def test_routes_to_answer_question_when_is_question(self):
        """Questions route to answer_question node."""
        state = create_initial_feature_state("TEST-123")
        state["current_node"] = "prd_approval_gate"
        state["is_question"] = True
        state["feedback_comment"] = "?Why REST?"

        result = route_prd_approval(state)

        assert result == "answer_question"

    def test_routes_to_regenerate_when_feedback(self):
        """Normal feedback still routes to regenerate."""
        state = create_initial_feature_state("TEST-123")
        state["current_node"] = "prd_approval_gate"
        state["revision_requested"] = True
        state["feedback_comment"] = "Add more detail"

        result = route_prd_approval(state)

        assert result == "regenerate_prd"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/workflow/gates/test_prd_approval.py::TestRouteWithQuestions -v`
Expected: FAIL

- [ ] **Step 3: Update route_prd_approval to handle questions**

In `src/forge/workflow/gates/prd_approval.py`, update `route_prd_approval`:

```python
def route_prd_approval(state: WorkflowState) -> str:
    """Route based on PRD approval status."""
    # Check if this is a question (Q&A mode)
    if state.get("is_question") and state.get("feedback_comment"):
        logger.info(f"Q&A mode: routing to answer_question for {state['ticket_key']}")
        return "answer_question"

    # Check if revision was requested via comment
    if state.get("revision_requested") and state.get("feedback_comment"):
        logger.info(f"PRD revision requested for {state['ticket_key']}")
        record_revision_requested("prd")
        return "regenerate_prd"

    # ... rest of existing logic
```

- [ ] **Step 4: Apply same pattern to spec_approval.py and plan_approval.py**

Update `route_spec_approval` and `route_plan_approval` similarly.

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/unit/workflow/gates/ -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/forge/workflow/gates/prd_approval.py src/forge/workflow/gates/spec_approval.py src/forge/workflow/gates/plan_approval.py tests/unit/workflow/gates/
git commit -m "feat(qa-mode): add question routing to approval gates"
```

---

## Task 8: Wire answer_question Node into Workflow Graphs

**Files:**
- Modify: `src/forge/workflow/feature/graph.py`
- Modify: `src/forge/workflow/bug/graph.py`

- [ ] **Step 1: Add answer_question node to feature graph**

In `src/forge/workflow/feature/graph.py`:

1. Import the node:
```python
from forge.workflow.nodes.qa_handler import answer_question
```

2. Add the node to the graph:
```python
graph.add_node("answer_question", answer_question)
```

3. Add edges from answer_question back to each gate:
```python
# Q&A routing: answer_question returns to the gate it came from
graph.add_conditional_edges(
    "answer_question",
    _route_after_answer,
    {
        "prd_approval_gate": "prd_approval_gate",
        "spec_approval_gate": "spec_approval_gate",
        "plan_approval_gate": "plan_approval_gate",
        "task_approval_gate": "task_approval_gate",
    },
)
```

4. Add routing function:
```python
def _route_after_answer(state: FeatureState) -> str:
    """Route back to the original gate after answering a question."""
    current_node = state.get("current_node", "")
    # answer_question preserves current_node as the gate to return to
    if current_node and "gate" in current_node:
        return current_node
    # Fallback
    return "prd_approval_gate"
```

- [ ] **Step 2: Add answer_question node to bug graph**

Apply similar changes to `src/forge/workflow/bug/graph.py` for `rca_approval_gate`.

- [ ] **Step 3: Run workflow tests**

Run: `uv run pytest tests/unit/workflow/ -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/forge/workflow/feature/graph.py src/forge/workflow/bug/graph.py
git commit -m "feat(qa-mode): wire answer_question into workflow graphs"
```

---

## Task 9: Post Q&A Summary on Approval

**Files:**
- Modify: `src/forge/workflow/gates/prd_approval.py` (and others)
- Create: `src/forge/workflow/utils/qa_summary.py`

- [ ] **Step 1: Create Q&A summary utility**

```python
# src/forge/workflow/utils/qa_summary.py
"""Utility for posting Q&A summary to Jira on approval."""

import logging
from forge.integrations.jira.client import JiraClient

logger = logging.getLogger(__name__)


async def post_qa_summary_if_needed(
    ticket_key: str,
    qa_history: list[dict],
    artifact_type: str,
) -> None:
    """Post a summary of Q&A exchanges when an artifact is approved.

    Args:
        ticket_key: Jira ticket key.
        qa_history: List of Q&A exchanges from state.
        artifact_type: Type of artifact that was approved.
    """
    # Filter Q&A for this artifact type
    relevant_qa = [
        qa for qa in qa_history
        if qa.get("artifact_type") == artifact_type
    ]

    if not relevant_qa:
        return

    logger.info(f"Posting Q&A summary for {ticket_key} ({len(relevant_qa)} exchanges)")

    jira = JiraClient()
    try:
        lines = [f"*Q&A Summary for {artifact_type.upper()}*\n"]
        for i, qa in enumerate(relevant_qa, 1):
            lines.append(f"*Q{i}:* {qa['question']}")
            lines.append(f"*A{i}:* {qa['answer']}\n")

        summary = "\n".join(lines)
        await jira.add_comment(ticket_key, summary)
    except Exception as e:
        logger.warning(f"Failed to post Q&A summary for {ticket_key}: {e}")
    finally:
        await jira.close()
```

- [ ] **Step 2: Call summary posting on approval**

In the routing functions, when approved, check for Q&A history:

```python
# In route_prd_approval, after detecting approval:
if not state.get("is_paused"):
    # Approved - post Q&A summary if any
    qa_history = state.get("qa_history", [])
    if qa_history:
        from forge.workflow.utils.qa_summary import post_qa_summary_if_needed
        import asyncio
        asyncio.create_task(
            post_qa_summary_if_needed(state["ticket_key"], qa_history, "prd")
        )
```

- [ ] **Step 3: Commit**

```bash
git add src/forge/workflow/utils/qa_summary.py src/forge/workflow/gates/
git commit -m "feat(qa-mode): post Q&A summary on artifact approval"
```

---

## Task 10: Clear Generation Context on Workflow Completion

**Files:**
- Modify: `src/forge/workflow/nodes/completion.py` (or equivalent)

- [ ] **Step 1: Add cleanup logic**

In the node that handles workflow completion (e.g., `aggregate_feature_status` or completion handlers), clear the generation context to save storage:

```python
# Clear generation context on completion
return update_state_timestamp({
    **state,
    "generation_context": {},  # Clear - no longer needed
    "qa_history": [],  # Already posted as summary
    "feature_completed": True,
    # ... rest
})
```

- [ ] **Step 2: Commit**

```bash
git add src/forge/workflow/nodes/
git commit -m "feat(qa-mode): clear generation context on workflow completion"
```

---

## Task 11: Update Proposal Status and Documentation

**Files:**
- Modify: `proposals/001-qa-mode-for-generated-artifacts.md`
- Modify: `README.md`

- [ ] **Step 1: Update proposal status**

Change status from "Draft" to "Implemented" and add implementation date.

- [ ] **Step 2: Add Q&A mode to README usage section**

Add a section explaining how to use Q&A mode:

```markdown
### Asking Questions About Generated Artifacts

While reviewing a PRD or Spec, you can ask clarifying questions without triggering regeneration:

- Start your comment with `?` - e.g., "?Why did you choose REST over GraphQL?"
- Or use `@forge ask` - e.g., "@forge ask explain the auth approach"

Forge will answer based on the artifact content and generation context, then keep the workflow paused for your approval decision.
```

- [ ] **Step 3: Commit**

```bash
git add proposals/001-qa-mode-for-generated-artifacts.md README.md
git commit -m "docs: update proposal status and add Q&A mode to README"
```

---

## Task 12: Integration Testing

**Files:**
- Create: `tests/integration/test_qa_mode.py`

- [ ] **Step 1: Create integration test**

```python
# tests/integration/test_qa_mode.py
"""Integration tests for Q&A mode."""

import pytest
from unittest.mock import patch, AsyncMock

from forge.orchestrator.worker import OrchestratorWorker
from forge.queue.models import QueueMessage
from forge.models.events import EventSource


@pytest.mark.integration
@pytest.mark.asyncio
async def test_question_comment_triggers_answer_not_regeneration():
    """End-to-end: question comment answers without regenerating."""
    # This test would use actual workflow execution with mocked externals
    # to verify the full flow works correctly
    pass
```

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Final commit**

```bash
git add tests/integration/test_qa_mode.py
git commit -m "test(qa-mode): add integration tests for Q&A flow"
```

---

## Summary

This plan implements Q&A mode in 12 tasks:

1. Comment classification function
2. Q&A state fields
3. Generation context storage
4. Answer question node
5. ForgeAgent answer_question method
6. Worker question detection
7. Gate routing for questions
8. Graph wiring
9. Q&A summary on approval
10. Context cleanup on completion
11. Documentation updates
12. Integration testing

Each task is self-contained with tests, making it suitable for incremental implementation.
