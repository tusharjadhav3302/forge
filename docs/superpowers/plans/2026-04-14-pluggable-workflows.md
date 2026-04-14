# Pluggable Workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor monolithic graph.py into modular workflow classes with a router-based architecture.

**Architecture:** Each workflow is a self-contained class with its own state schema and graph definition. A WorkflowRouter matches incoming tickets to workflows. Existing nodes/gates move to `workflow/nodes/` and `workflow/gates/` directories.

**Tech Stack:** Python 3.11+, LangGraph, TypedDict inheritance

---

## Phase 1: Create Foundation

### Task 1: Create BaseState and State Mixins

**Files:**
- Create: `src/forge/workflow/__init__.py`
- Create: `src/forge/workflow/base.py`
- Test: `tests/unit/workflow/test_base.py`

- [ ] **Step 1: Create workflow package**

```bash
mkdir -p src/forge/workflow
touch src/forge/workflow/__init__.py
```

- [ ] **Step 2: Write failing test for BaseState**

Create `tests/unit/workflow/__init__.py`:
```python
"""Unit tests for workflow module."""
```

Create `tests/unit/workflow/test_base.py`:
```python
"""Tests for BaseState and mixins."""

import pytest
from typing import get_type_hints


class TestBaseState:
    """Tests for BaseState TypedDict."""

    def test_base_state_has_required_fields(self):
        """BaseState includes all shared workflow fields."""
        from forge.workflow.base import BaseState

        hints = get_type_hints(BaseState)

        # Identity fields
        assert "thread_id" in hints
        assert "ticket_key" in hints

        # Execution control
        assert "current_node" in hints
        assert "is_paused" in hints
        assert "retry_count" in hints
        assert "last_error" in hints

        # Timestamps
        assert "created_at" in hints
        assert "updated_at" in hints

        # Feedback
        assert "feedback_comment" in hints
        assert "revision_requested" in hints

    def test_base_state_is_total_false(self):
        """BaseState allows partial initialization."""
        from forge.workflow.base import BaseState

        # Should not raise - all fields optional
        state: BaseState = {"thread_id": "test", "ticket_key": "TEST-1"}
        assert state["thread_id"] == "test"


class TestPRIntegrationState:
    """Tests for PR integration mixin."""

    def test_pr_state_has_required_fields(self):
        """PRIntegrationState includes PR-related fields."""
        from forge.workflow.base import PRIntegrationState

        hints = get_type_hints(PRIntegrationState)

        assert "workspace_path" in hints
        assert "pr_urls" in hints
        assert "current_pr_url" in hints
        assert "current_repo" in hints
        assert "repos_to_process" in hints
        assert "repos_completed" in hints


class TestCIIntegrationState:
    """Tests for CI integration mixin."""

    def test_ci_state_has_required_fields(self):
        """CIIntegrationState includes CI-related fields."""
        from forge.workflow.base import CIIntegrationState

        hints = get_type_hints(CIIntegrationState)

        assert "ci_status" in hints
        assert "ci_failed_checks" in hints
        assert "ci_fix_attempts" in hints


class TestReviewIntegrationState:
    """Tests for review integration mixin."""

    def test_review_state_has_required_fields(self):
        """ReviewIntegrationState includes review-related fields."""
        from forge.workflow.base import ReviewIntegrationState

        hints = get_type_hints(ReviewIntegrationState)

        assert "ai_review_status" in hints
        assert "ai_review_results" in hints
        assert "human_review_status" in hints
        assert "pr_merged" in hints
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/workflow/test_base.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'forge.workflow'"

- [ ] **Step 4: Implement BaseState and mixins**

Create `src/forge/workflow/base.py`:
```python
"""Base workflow classes and state definitions."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Annotated, Any, TypedDict

from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages

from forge.models.workflow import TicketType


class BaseState(TypedDict, total=False):
    """State shared by ALL workflows."""

    # Identity
    thread_id: str
    ticket_key: str

    # Execution control
    current_node: str
    is_paused: bool
    retry_count: int
    last_error: str | None

    # Timestamps
    created_at: str
    updated_at: str

    # Feedback (human-in-the-loop)
    feedback_comment: str | None
    revision_requested: bool

    # Message history
    messages: Annotated[list[Any], add_messages]
    context: dict[str, Any]


class PRIntegrationState(TypedDict, total=False):
    """Mixin for workflows that create PRs."""

    workspace_path: str | None
    pr_urls: list[str]
    current_pr_url: str | None
    current_pr_number: int | None
    current_repo: str | None
    repos_to_process: list[str]
    repos_completed: list[str]
    implemented_tasks: list[str]
    current_task_key: str | None


class CIIntegrationState(TypedDict, total=False):
    """Mixin for workflows that use CI."""

    ci_status: str | None
    ci_failed_checks: list[dict[str, Any]]
    ci_fix_attempts: int


class ReviewIntegrationState(TypedDict, total=False):
    """Mixin for workflows with review stages."""

    ai_review_status: str | None
    ai_review_results: list[dict[str, Any]]
    human_review_status: str | None
    pr_merged: bool


class BaseWorkflow(ABC):
    """Base class all workflows must extend."""

    name: str
    description: str

    @property
    @abstractmethod
    def state_schema(self) -> type:
        """Return the TypedDict state class for this workflow."""
        ...

    @abstractmethod
    def matches(
        self, ticket_type: TicketType, labels: list[str], event: dict[str, Any]
    ) -> bool:
        """Return True if this workflow should handle the given ticket/event."""
        ...

    @abstractmethod
    def build_graph(self) -> StateGraph:
        """Construct and return the LangGraph StateGraph."""
        ...

    def create_initial_state(self, ticket_key: str, **kwargs: Any) -> dict[str, Any]:
        """Create initial state for a new workflow run."""
        now = datetime.utcnow().isoformat()
        return {
            "thread_id": ticket_key,
            "ticket_key": ticket_key,
            "current_node": "start",
            "is_paused": False,
            "retry_count": 0,
            "last_error": None,
            "created_at": now,
            "updated_at": now,
            "messages": [],
            "context": {},
            **kwargs,
        }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/workflow/test_base.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/forge/workflow/ tests/unit/workflow/
git commit -m "feat(workflow): add BaseState and integration mixins"
```

---

### Task 2: Create WorkflowRouter

**Files:**
- Create: `src/forge/workflow/router.py`
- Test: `tests/unit/workflow/test_router.py`

- [ ] **Step 1: Write failing test for WorkflowRouter**

Create `tests/unit/workflow/test_router.py`:
```python
"""Tests for WorkflowRouter."""

import pytest
from langgraph.graph import StateGraph

from forge.models.workflow import TicketType
from forge.workflow.base import BaseState, BaseWorkflow


class MockWorkflow(BaseWorkflow):
    """Test workflow that matches Features."""

    name = "mock"
    description = "Mock workflow for testing"

    @property
    def state_schema(self) -> type:
        return BaseState

    def matches(
        self, ticket_type: TicketType, labels: list[str], event: dict
    ) -> bool:
        return ticket_type == TicketType.FEATURE

    def build_graph(self) -> StateGraph:
        graph = StateGraph(BaseState)
        graph.add_node("start", lambda s: s)
        graph.set_entry_point("start")
        return graph


class MockBugWorkflow(BaseWorkflow):
    """Test workflow that matches Bugs."""

    name = "mock_bug"
    description = "Mock bug workflow for testing"

    @property
    def state_schema(self) -> type:
        return BaseState

    def matches(
        self, ticket_type: TicketType, labels: list[str], event: dict
    ) -> bool:
        return ticket_type == TicketType.BUG

    def build_graph(self) -> StateGraph:
        graph = StateGraph(BaseState)
        graph.add_node("start", lambda s: s)
        graph.set_entry_point("start")
        return graph


class TestWorkflowRouter:
    """Tests for WorkflowRouter."""

    def test_register_workflow(self):
        """Can register a workflow class."""
        from forge.workflow.router import WorkflowRouter

        router = WorkflowRouter()
        router.register(MockWorkflow)

        assert len(router._workflows) == 1

    def test_resolve_returns_matching_workflow(self):
        """Resolve returns workflow that matches ticket."""
        from forge.workflow.router import WorkflowRouter

        router = WorkflowRouter()
        router.register(MockWorkflow)
        router.register(MockBugWorkflow)

        workflow = router.resolve(
            ticket_type=TicketType.FEATURE,
            labels=[],
            event={},
        )

        assert workflow is not None
        assert workflow.name == "mock"

    def test_resolve_returns_none_when_no_match(self):
        """Resolve returns None when no workflow matches."""
        from forge.workflow.router import WorkflowRouter

        router = WorkflowRouter()
        router.register(MockWorkflow)

        workflow = router.resolve(
            ticket_type=TicketType.BUG,
            labels=[],
            event={},
        )

        assert workflow is None

    def test_resolve_first_match_wins(self):
        """First registered workflow that matches is returned."""
        from forge.workflow.router import WorkflowRouter

        class AnotherFeatureWorkflow(MockWorkflow):
            name = "another_feature"

        router = WorkflowRouter()
        router.register(MockWorkflow)
        router.register(AnotherFeatureWorkflow)

        workflow = router.resolve(
            ticket_type=TicketType.FEATURE,
            labels=[],
            event={},
        )

        assert workflow.name == "mock"

    def test_list_workflows(self):
        """List returns all registered workflows."""
        from forge.workflow.router import WorkflowRouter

        router = WorkflowRouter()
        router.register(MockWorkflow)
        router.register(MockBugWorkflow)

        workflows = router.list_workflows()

        assert len(workflows) == 2
        assert workflows[0]["name"] == "mock"
        assert workflows[1]["name"] == "mock_bug"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/workflow/test_router.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'forge.workflow.router'"

- [ ] **Step 3: Implement WorkflowRouter**

Create `src/forge/workflow/router.py`:
```python
"""Workflow router for matching tickets to workflows."""

from typing import Any, Type

from forge.models.workflow import TicketType
from forge.workflow.base import BaseWorkflow


class WorkflowRouter:
    """Routes incoming tickets to appropriate workflows."""

    def __init__(self) -> None:
        self._workflows: list[Type[BaseWorkflow]] = []

    def register(self, workflow_class: Type[BaseWorkflow]) -> None:
        """Register a workflow class. First match wins."""
        self._workflows.append(workflow_class)

    def resolve(
        self,
        ticket_type: TicketType,
        labels: list[str],
        event: dict[str, Any],
    ) -> BaseWorkflow | None:
        """Find the first matching workflow for given ticket/event."""
        for workflow_class in self._workflows:
            instance = workflow_class()
            if instance.matches(ticket_type, labels, event):
                return instance
        return None

    def list_workflows(self) -> list[dict[str, str]]:
        """List all registered workflows (for health/debug endpoints)."""
        return [
            {"name": wf.name, "description": wf.description}
            for wf in self._workflows
        ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/workflow/test_router.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/forge/workflow/router.py tests/unit/workflow/test_router.py
git commit -m "feat(workflow): add WorkflowRouter"
```

---

### Task 3: Move Nodes to workflow/nodes/

**Files:**
- Move: `src/forge/orchestrator/nodes/*.py` → `src/forge/workflow/nodes/`
- Modify: All node files to update internal imports

- [ ] **Step 1: Create workflow/nodes directory and move files**

```bash
mkdir -p src/forge/workflow/nodes
cp src/forge/orchestrator/nodes/*.py src/forge/workflow/nodes/
```

- [ ] **Step 2: Update imports in moved node files**

For each file in `src/forge/workflow/nodes/`, update imports from:
- `from forge.orchestrator.state import ...` → `from forge.workflow.base import BaseState` (or keep using orchestrator.state for now)
- `from forge.orchestrator.nodes.X import ...` → `from forge.workflow.nodes.X import ...`

Note: Keep `from forge.orchestrator.state import WorkflowState` for now - we'll update this after creating FeatureState.

- [ ] **Step 3: Run existing tests to verify nodes still work**

Run: `uv run pytest tests/unit/orchestrator/nodes/ -v`
Expected: All existing node tests PASS

- [ ] **Step 4: Update orchestrator/nodes to re-export from workflow/nodes**

Modify `src/forge/orchestrator/nodes/__init__.py` to re-export from new location:
```python
"""Node implementations - re-exported from workflow.nodes for backward compatibility."""

# Re-export all nodes from workflow.nodes
from forge.workflow.nodes.prd_generation import *
from forge.workflow.nodes.spec_generation import *
from forge.workflow.nodes.epic_decomposition import *
from forge.workflow.nodes.task_generation import *
from forge.workflow.nodes.task_router import *
from forge.workflow.nodes.implementation import *
from forge.workflow.nodes.pr_creation import *
from forge.workflow.nodes.ci_evaluator import *
from forge.workflow.nodes.ai_reviewer import *
from forge.workflow.nodes.human_review import *
from forge.workflow.nodes.workspace_setup import *
from forge.workflow.nodes.bug_workflow import *
from forge.workflow.nodes.error_handler import *
```

- [ ] **Step 5: Run all tests to verify backward compatibility**

Run: `uv run pytest tests/ -v --ignore=tests/e2e/`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/forge/workflow/nodes/ src/forge/orchestrator/nodes/__init__.py
git commit -m "refactor: move nodes to workflow/nodes/"
```

---

### Task 4: Move Gates to workflow/gates/

**Files:**
- Move: `src/forge/orchestrator/gates/*.py` → `src/forge/workflow/gates/`
- Modify: Gate files to update internal imports

- [ ] **Step 1: Create workflow/gates directory and move files**

```bash
mkdir -p src/forge/workflow/gates
cp src/forge/orchestrator/gates/*.py src/forge/workflow/gates/
```

- [ ] **Step 2: Update imports in moved gate files**

For each file in `src/forge/workflow/gates/`, update imports from:
- `from forge.orchestrator.nodes.X import ...` → `from forge.workflow.nodes.X import ...`

- [ ] **Step 3: Update orchestrator/gates to re-export from workflow/gates**

Modify `src/forge/orchestrator/gates/__init__.py` to re-export from new location:
```python
"""Gate implementations - re-exported from workflow.gates for backward compatibility."""

from forge.workflow.gates.prd_approval import *
from forge.workflow.gates.spec_approval import *
from forge.workflow.gates.plan_approval import *
from forge.workflow.gates.task_approval import *
```

- [ ] **Step 4: Run all tests to verify backward compatibility**

Run: `uv run pytest tests/ -v --ignore=tests/e2e/`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/forge/workflow/gates/ src/forge/orchestrator/gates/__init__.py
git commit -m "refactor: move gates to workflow/gates/"
```

---

## Phase 2: Extract Workflows

### Task 5: Create FeatureState

**Files:**
- Create: `src/forge/workflow/feature/__init__.py`
- Create: `src/forge/workflow/feature/state.py`
- Test: `tests/unit/workflow/feature/test_state.py`

- [ ] **Step 1: Create feature workflow package**

```bash
mkdir -p src/forge/workflow/feature
touch src/forge/workflow/feature/__init__.py
mkdir -p tests/unit/workflow/feature
touch tests/unit/workflow/feature/__init__.py
```

- [ ] **Step 2: Write failing test for FeatureState**

Create `tests/unit/workflow/feature/test_state.py`:
```python
"""Tests for FeatureState."""

import pytest
from typing import get_type_hints


class TestFeatureState:
    """Tests for FeatureState TypedDict."""

    def test_feature_state_inherits_base_state(self):
        """FeatureState includes BaseState fields."""
        from forge.workflow.feature.state import FeatureState

        hints = get_type_hints(FeatureState)

        # BaseState fields
        assert "thread_id" in hints
        assert "ticket_key" in hints
        assert "current_node" in hints

    def test_feature_state_has_artifact_fields(self):
        """FeatureState includes PRD and spec content."""
        from forge.workflow.feature.state import FeatureState

        hints = get_type_hints(FeatureState)

        assert "prd_content" in hints
        assert "spec_content" in hints

    def test_feature_state_has_epic_task_tracking(self):
        """FeatureState includes epic and task tracking."""
        from forge.workflow.feature.state import FeatureState

        hints = get_type_hints(FeatureState)

        assert "epic_keys" in hints
        assert "task_keys" in hints
        assert "tasks_by_repo" in hints

    def test_feature_state_has_pr_fields(self):
        """FeatureState includes PR integration fields."""
        from forge.workflow.feature.state import FeatureState

        hints = get_type_hints(FeatureState)

        assert "workspace_path" in hints
        assert "pr_urls" in hints

    def test_create_initial_feature_state(self):
        """Can create initial feature state."""
        from forge.workflow.feature.state import create_initial_feature_state

        state = create_initial_feature_state("TEST-123")

        assert state["ticket_key"] == "TEST-123"
        assert state["prd_content"] == ""
        assert state["epic_keys"] == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/workflow/feature/test_state.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 4: Implement FeatureState**

Create `src/forge/workflow/feature/state.py`:
```python
"""Feature workflow state definition."""

from datetime import datetime
from typing import Any

from forge.models.workflow import TicketType
from forge.workflow.base import (
    BaseState,
    CIIntegrationState,
    PRIntegrationState,
    ReviewIntegrationState,
)


class FeatureState(
    BaseState, PRIntegrationState, CIIntegrationState, ReviewIntegrationState, total=False
):
    """State specific to Feature workflow."""

    ticket_type: TicketType

    # Artifacts
    prd_content: str
    spec_content: str

    # Epic/Task tracking
    epic_keys: list[str]
    current_epic_key: str | None
    task_keys: list[str]
    tasks_by_repo: dict[str, list[str]]

    # Completion tracking
    tasks_completed: bool
    epics_completed: bool
    feature_completed: bool

    # Parallel execution
    parallel_execution_enabled: bool
    parallel_branch_id: int | None
    parallel_total_branches: int | None


def create_initial_feature_state(ticket_key: str, **kwargs: Any) -> FeatureState:
    """Create initial state for a new Feature workflow run."""
    now = datetime.utcnow().isoformat()
    return FeatureState(
        thread_id=ticket_key,
        ticket_key=ticket_key,
        ticket_type=TicketType.FEATURE,
        current_node="start",
        is_paused=False,
        retry_count=0,
        last_error=None,
        created_at=now,
        updated_at=now,
        prd_content="",
        spec_content="",
        epic_keys=[],
        current_epic_key=None,
        task_keys=[],
        tasks_by_repo={},
        workspace_path=None,
        pr_urls=[],
        ci_status=None,
        current_pr_url=None,
        current_pr_number=None,
        current_repo=None,
        repos_to_process=[],
        repos_completed=[],
        implemented_tasks=[],
        current_task_key=None,
        parallel_execution_enabled=True,
        parallel_branch_id=None,
        parallel_total_branches=None,
        ci_failed_checks=[],
        ci_fix_attempts=0,
        ai_review_status=None,
        ai_review_results=[],
        human_review_status=None,
        pr_merged=False,
        tasks_completed=False,
        epics_completed=False,
        feature_completed=False,
        feedback_comment=None,
        revision_requested=False,
        messages=[],
        context={},
        **kwargs,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/workflow/feature/test_state.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/forge/workflow/feature/ tests/unit/workflow/feature/
git commit -m "feat(workflow): add FeatureState"
```

---

### Task 6: Create FeatureWorkflow Class

**Files:**
- Modify: `src/forge/workflow/feature/__init__.py`
- Create: `src/forge/workflow/feature/graph.py`
- Test: `tests/unit/workflow/feature/test_workflow.py`

- [ ] **Step 1: Write failing test for FeatureWorkflow**

Create `tests/unit/workflow/feature/test_workflow.py`:
```python
"""Tests for FeatureWorkflow."""

import pytest

from forge.models.workflow import TicketType


class TestFeatureWorkflow:
    """Tests for FeatureWorkflow class."""

    def test_workflow_has_name(self):
        """FeatureWorkflow has name attribute."""
        from forge.workflow.feature import FeatureWorkflow

        workflow = FeatureWorkflow()
        assert workflow.name == "feature"

    def test_workflow_has_description(self):
        """FeatureWorkflow has description."""
        from forge.workflow.feature import FeatureWorkflow

        workflow = FeatureWorkflow()
        assert "PRD" in workflow.description

    def test_matches_feature_type(self):
        """Matches Feature ticket type."""
        from forge.workflow.feature import FeatureWorkflow

        workflow = FeatureWorkflow()

        assert workflow.matches(TicketType.FEATURE, [], {}) is True

    def test_matches_story_type(self):
        """Matches Story ticket type."""
        from forge.workflow.feature import FeatureWorkflow

        workflow = FeatureWorkflow()

        assert workflow.matches(TicketType.STORY, [], {}) is True

    def test_does_not_match_bug(self):
        """Does not match Bug ticket type."""
        from forge.workflow.feature import FeatureWorkflow

        workflow = FeatureWorkflow()

        assert workflow.matches(TicketType.BUG, [], {}) is False

    def test_state_schema_returns_feature_state(self):
        """state_schema returns FeatureState."""
        from forge.workflow.feature import FeatureWorkflow
        from forge.workflow.feature.state import FeatureState

        workflow = FeatureWorkflow()

        assert workflow.state_schema is FeatureState

    def test_build_graph_returns_state_graph(self):
        """build_graph returns a StateGraph."""
        from langgraph.graph import StateGraph
        from forge.workflow.feature import FeatureWorkflow

        workflow = FeatureWorkflow()
        graph = workflow.build_graph()

        assert isinstance(graph, StateGraph)

    def test_create_initial_state(self):
        """create_initial_state returns FeatureState with defaults."""
        from forge.workflow.feature import FeatureWorkflow

        workflow = FeatureWorkflow()
        state = workflow.create_initial_state("TEST-123")

        assert state["ticket_key"] == "TEST-123"
        assert state["ticket_type"] == TicketType.FEATURE
        assert state["prd_content"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/workflow/feature/test_workflow.py -v`
Expected: FAIL with import error

- [ ] **Step 3: Create FeatureWorkflow graph module**

Create `src/forge/workflow/feature/graph.py`:
```python
"""Feature workflow graph definition."""

from langgraph.graph import END, StateGraph

from forge.workflow.feature.state import FeatureState
from forge.workflow.gates.prd_approval import prd_approval_gate, route_prd_approval
from forge.workflow.gates.spec_approval import spec_approval_gate, route_spec_approval
from forge.workflow.gates.plan_approval import plan_approval_gate, route_plan_approval
from forge.workflow.gates.task_approval import task_approval_gate, route_task_approval
from forge.workflow.nodes.prd_generation import generate_prd, regenerate_prd_with_feedback
from forge.workflow.nodes.spec_generation import generate_spec, regenerate_spec_with_feedback
from forge.workflow.nodes.epic_decomposition import (
    decompose_epics,
    regenerate_all_epics,
    update_single_epic,
)
from forge.workflow.nodes.task_generation import (
    generate_tasks,
    regenerate_all_tasks,
    update_single_task,
)
from forge.workflow.nodes.task_router import (
    aggregate_parallel_results,
    route_tasks_by_repo,
    route_tasks_parallel,
)
from forge.workflow.nodes.workspace_setup import setup_workspace
from forge.workflow.nodes.implementation import implement_task
from forge.workflow.nodes.pr_creation import create_pull_request, teardown_and_route
from forge.workflow.nodes.ci_evaluator import (
    evaluate_ci_status,
    attempt_ci_fix,
    escalate_to_blocked,
)
from forge.workflow.nodes.ai_reviewer import review_code
from forge.workflow.nodes.human_review import (
    human_review_gate,
    route_human_review,
    complete_tasks,
    aggregate_epic_status,
    aggregate_feature_status,
)


def build_feature_graph() -> StateGraph:
    """Build the Feature workflow StateGraph.
    
    This is extracted from the original graph.py create_workflow_graph() function,
    containing only the Feature workflow nodes and edges.
    """
    graph = StateGraph(FeatureState)

    # Entry node
    graph.add_node("route_entry", lambda state: state)

    # PRD Generation nodes
    graph.add_node("generate_prd", generate_prd)
    graph.add_node("prd_approval_gate", prd_approval_gate)
    graph.add_node("regenerate_prd", regenerate_prd_with_feedback)

    # Spec Generation nodes
    graph.add_node("generate_spec", generate_spec)
    graph.add_node("spec_approval_gate", spec_approval_gate)
    graph.add_node("regenerate_spec", regenerate_spec_with_feedback)

    # Epic Decomposition nodes
    graph.add_node("decompose_epics", decompose_epics)
    graph.add_node("plan_approval_gate", plan_approval_gate)
    graph.add_node("regenerate_all_epics", regenerate_all_epics)
    graph.add_node("update_single_epic", update_single_epic)

    # Task Generation nodes
    graph.add_node("generate_tasks", generate_tasks)
    graph.add_node("task_approval_gate", task_approval_gate)
    graph.add_node("regenerate_all_tasks", regenerate_all_tasks)
    graph.add_node("update_single_task", update_single_task)

    # Parallel Execution aggregation node
    graph.add_node("aggregate_pr_results", aggregate_parallel_results)

    # Execution nodes
    graph.add_node("task_router", route_tasks_by_repo)
    graph.add_node("setup_workspace", setup_workspace)
    graph.add_node("implement_task", implement_task)
    graph.add_node("create_pr", create_pull_request)
    graph.add_node("teardown_workspace", teardown_and_route)

    # CI/CD Validation nodes
    graph.add_node("ci_evaluator", evaluate_ci_status)
    graph.add_node("attempt_ci_fix", attempt_ci_fix)
    graph.add_node("escalate_blocked", escalate_to_blocked)

    # AI Code Review nodes
    graph.add_node("ai_review", review_code)

    # Human Review nodes
    graph.add_node("human_review_gate", human_review_gate)
    graph.add_node("complete_tasks", complete_tasks)
    graph.add_node("aggregate_epic_status", aggregate_epic_status)
    graph.add_node("aggregate_feature_status", aggregate_feature_status)

    # Set entry point
    graph.set_entry_point("route_entry")

    # Route from entry to generate_prd (Feature workflow always starts here)
    graph.add_edge("route_entry", "generate_prd")

    # PRD generation flow
    graph.add_edge("generate_prd", "prd_approval_gate")
    graph.add_conditional_edges(
        "prd_approval_gate",
        route_prd_approval,
        {
            "generate_spec": "generate_spec",
            "regenerate_prd": "regenerate_prd",
            END: END,
        },
    )
    graph.add_edge("regenerate_prd", "prd_approval_gate")

    # Spec generation flow
    graph.add_edge("generate_spec", "spec_approval_gate")
    graph.add_conditional_edges(
        "spec_approval_gate",
        route_spec_approval,
        {
            "decompose_epics": "decompose_epics",
            "regenerate_spec": "regenerate_spec",
            END: END,
        },
    )
    graph.add_edge("regenerate_spec", "spec_approval_gate")

    # Epic decomposition flow
    graph.add_edge("decompose_epics", "plan_approval_gate")
    graph.add_conditional_edges(
        "plan_approval_gate",
        route_plan_approval,
        {
            "generate_tasks": "generate_tasks",
            "regenerate_all_epics": "regenerate_all_epics",
            "update_single_epic": "update_single_epic",
            END: END,
        },
    )
    graph.add_edge("regenerate_all_epics", "plan_approval_gate")
    graph.add_edge("update_single_epic", "plan_approval_gate")

    # Task generation flow
    graph.add_edge("generate_tasks", "task_approval_gate")
    graph.add_conditional_edges(
        "task_approval_gate",
        route_task_approval,
        {
            "task_router": "task_router",
            "regenerate_all_tasks": "regenerate_all_tasks",
            "update_single_task": "update_single_task",
            END: END,
        },
    )
    graph.add_edge("regenerate_all_tasks", "task_approval_gate")
    graph.add_edge("update_single_task", "task_approval_gate")

    # Execution flow
    graph.add_conditional_edges("task_router", route_tasks_parallel)
    graph.add_edge("setup_workspace", "implement_task")
    graph.add_edge("implement_task", "create_pr")
    graph.add_edge("create_pr", "teardown_workspace")
    graph.add_edge("teardown_workspace", "ci_evaluator")

    # CI/CD flow
    graph.add_edge("ci_evaluator", "ai_review")
    graph.add_edge("attempt_ci_fix", "ci_evaluator")
    graph.add_edge("escalate_blocked", END)

    # AI Review flow
    graph.add_edge("ai_review", "human_review_gate")

    # Human Review flow
    graph.add_conditional_edges(
        "human_review_gate",
        route_human_review,
        {
            "implement_task": "implement_task",
            "complete_tasks": "complete_tasks",
            END: END,
        },
    )
    graph.add_edge("complete_tasks", "aggregate_epic_status")
    graph.add_edge("aggregate_epic_status", "aggregate_feature_status")
    graph.add_edge("aggregate_feature_status", END)

    return graph
```

- [ ] **Step 4: Create FeatureWorkflow class**

Modify `src/forge/workflow/feature/__init__.py`:
```python
"""Feature workflow implementation."""

from typing import Any

from langgraph.graph import StateGraph

from forge.models.workflow import TicketType
from forge.workflow.base import BaseWorkflow
from forge.workflow.feature.graph import build_feature_graph
from forge.workflow.feature.state import FeatureState, create_initial_feature_state


class FeatureWorkflow(BaseWorkflow):
    """Full SDLC workflow for Feature tickets."""

    name = "feature"
    description = "Full SDLC workflow: PRD -> Spec -> Epic -> Task -> Implementation"

    @property
    def state_schema(self) -> type:
        return FeatureState

    def matches(
        self, ticket_type: TicketType, labels: list[str], event: dict[str, Any]
    ) -> bool:
        return ticket_type in (TicketType.FEATURE, TicketType.STORY)

    def build_graph(self) -> StateGraph:
        return build_feature_graph()

    def create_initial_state(self, ticket_key: str, **kwargs: Any) -> FeatureState:
        return create_initial_feature_state(ticket_key, **kwargs)


__all__ = ["FeatureWorkflow", "FeatureState", "create_initial_feature_state"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/workflow/feature/test_workflow.py -v`
Expected: All tests PASS (or some may need adjustment based on actual graph structure)

- [ ] **Step 6: Commit**

```bash
git add src/forge/workflow/feature/
git commit -m "feat(workflow): add FeatureWorkflow class"
```

---

### Task 7: Create BugState and BugWorkflow

**Files:**
- Create: `src/forge/workflow/bug/__init__.py`
- Create: `src/forge/workflow/bug/state.py`
- Create: `src/forge/workflow/bug/graph.py`
- Test: `tests/unit/workflow/bug/test_workflow.py`

- [ ] **Step 1: Create bug workflow package**

```bash
mkdir -p src/forge/workflow/bug
touch src/forge/workflow/bug/__init__.py
mkdir -p tests/unit/workflow/bug
touch tests/unit/workflow/bug/__init__.py
```

- [ ] **Step 2: Write failing test for BugWorkflow**

Create `tests/unit/workflow/bug/test_workflow.py`:
```python
"""Tests for BugWorkflow."""

import pytest

from forge.models.workflow import TicketType


class TestBugWorkflow:
    """Tests for BugWorkflow class."""

    def test_workflow_has_name(self):
        """BugWorkflow has name attribute."""
        from forge.workflow.bug import BugWorkflow

        workflow = BugWorkflow()
        assert workflow.name == "bug"

    def test_matches_bug_type(self):
        """Matches Bug ticket type."""
        from forge.workflow.bug import BugWorkflow

        workflow = BugWorkflow()

        assert workflow.matches(TicketType.BUG, [], {}) is True

    def test_does_not_match_feature(self):
        """Does not match Feature ticket type."""
        from forge.workflow.bug import BugWorkflow

        workflow = BugWorkflow()

        assert workflow.matches(TicketType.FEATURE, [], {}) is False

    def test_state_schema_returns_bug_state(self):
        """state_schema returns BugState."""
        from forge.workflow.bug import BugWorkflow
        from forge.workflow.bug.state import BugState

        workflow = BugWorkflow()

        assert workflow.state_schema is BugState

    def test_build_graph_returns_state_graph(self):
        """build_graph returns a StateGraph."""
        from langgraph.graph import StateGraph
        from forge.workflow.bug import BugWorkflow

        workflow = BugWorkflow()
        graph = workflow.build_graph()

        assert isinstance(graph, StateGraph)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/workflow/bug/test_workflow.py -v`
Expected: FAIL with import error

- [ ] **Step 4: Implement BugState**

Create `src/forge/workflow/bug/state.py`:
```python
"""Bug workflow state definition."""

from datetime import datetime
from typing import Any

from forge.models.workflow import TicketType
from forge.workflow.base import (
    BaseState,
    CIIntegrationState,
    PRIntegrationState,
    ReviewIntegrationState,
)


class BugState(
    BaseState, PRIntegrationState, CIIntegrationState, ReviewIntegrationState, total=False
):
    """State specific to Bug workflow."""

    ticket_type: TicketType

    # Bug-specific
    rca_content: str | None
    bug_fix_implemented: bool


def create_initial_bug_state(ticket_key: str, **kwargs: Any) -> BugState:
    """Create initial state for a new Bug workflow run."""
    now = datetime.utcnow().isoformat()
    return BugState(
        thread_id=ticket_key,
        ticket_key=ticket_key,
        ticket_type=TicketType.BUG,
        current_node="start",
        is_paused=False,
        retry_count=0,
        last_error=None,
        created_at=now,
        updated_at=now,
        rca_content=None,
        bug_fix_implemented=False,
        workspace_path=None,
        pr_urls=[],
        ci_status=None,
        current_pr_url=None,
        current_pr_number=None,
        current_repo=None,
        repos_to_process=[],
        repos_completed=[],
        implemented_tasks=[],
        current_task_key=None,
        ci_failed_checks=[],
        ci_fix_attempts=0,
        ai_review_status=None,
        ai_review_results=[],
        human_review_status=None,
        pr_merged=False,
        feedback_comment=None,
        revision_requested=False,
        messages=[],
        context={},
        **kwargs,
    )
```

- [ ] **Step 5: Implement BugWorkflow graph**

Create `src/forge/workflow/bug/graph.py`:
```python
"""Bug workflow graph definition."""

from langgraph.graph import END, StateGraph

from forge.workflow.bug.state import BugState
from forge.workflow.nodes.bug_workflow import (
    analyze_bug,
    implement_bug_fix,
    rca_approval_gate,
    regenerate_rca,
    route_rca_approval,
)
from forge.workflow.nodes.pr_creation import create_pull_request, teardown_and_route
from forge.workflow.nodes.ci_evaluator import evaluate_ci_status
from forge.workflow.nodes.ai_reviewer import review_code
from forge.workflow.nodes.human_review import human_review_gate, route_human_review


def build_bug_graph() -> StateGraph:
    """Build the Bug workflow StateGraph."""
    graph = StateGraph(BugState)

    # Entry node
    graph.add_node("route_entry", lambda state: state)

    # Bug workflow nodes
    graph.add_node("analyze_bug", analyze_bug)
    graph.add_node("rca_approval_gate", rca_approval_gate)
    graph.add_node("regenerate_rca", regenerate_rca)
    graph.add_node("implement_bug_fix", implement_bug_fix)

    # Shared nodes
    graph.add_node("create_pr", create_pull_request)
    graph.add_node("ci_evaluator", evaluate_ci_status)
    graph.add_node("ai_review", review_code)
    graph.add_node("human_review_gate", human_review_gate)

    # Set entry point
    graph.set_entry_point("route_entry")

    # Route from entry to analyze_bug
    graph.add_edge("route_entry", "analyze_bug")

    # Bug workflow flow
    graph.add_edge("analyze_bug", "rca_approval_gate")
    graph.add_conditional_edges(
        "rca_approval_gate",
        route_rca_approval,
        {
            "implement_bug_fix": "implement_bug_fix",
            "regenerate_rca": "regenerate_rca",
            END: END,
        },
    )
    graph.add_edge("regenerate_rca", "rca_approval_gate")
    graph.add_edge("implement_bug_fix", "create_pr")

    # PR -> CI -> Review flow
    graph.add_edge("create_pr", "ci_evaluator")
    graph.add_edge("ci_evaluator", "ai_review")
    graph.add_edge("ai_review", "human_review_gate")
    graph.add_conditional_edges(
        "human_review_gate",
        route_human_review,
        {
            "implement_bug_fix": "implement_bug_fix",
            END: END,
        },
    )

    return graph
```

- [ ] **Step 6: Implement BugWorkflow class**

Modify `src/forge/workflow/bug/__init__.py`:
```python
"""Bug workflow implementation."""

from typing import Any

from langgraph.graph import StateGraph

from forge.models.workflow import TicketType
from forge.workflow.base import BaseWorkflow
from forge.workflow.bug.graph import build_bug_graph
from forge.workflow.bug.state import BugState, create_initial_bug_state


class BugWorkflow(BaseWorkflow):
    """Workflow for Bug tickets."""

    name = "bug"
    description = "Bug workflow: Analyze -> RCA -> Fix -> PR -> Review"

    @property
    def state_schema(self) -> type:
        return BugState

    def matches(
        self, ticket_type: TicketType, labels: list[str], event: dict[str, Any]
    ) -> bool:
        return ticket_type == TicketType.BUG

    def build_graph(self) -> StateGraph:
        return build_bug_graph()

    def create_initial_state(self, ticket_key: str, **kwargs: Any) -> BugState:
        return create_initial_bug_state(ticket_key, **kwargs)


__all__ = ["BugWorkflow", "BugState", "create_initial_bug_state"]
```

- [ ] **Step 7: Run test to verify it passes**

Run: `uv run pytest tests/unit/workflow/bug/test_workflow.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/forge/workflow/bug/ tests/unit/workflow/bug/
git commit -m "feat(workflow): add BugWorkflow class"
```

---

## Phase 3: Wire Up Router

### Task 8: Create Default Registry

**Files:**
- Create: `src/forge/workflow/registry.py`
- Test: `tests/unit/workflow/test_registry.py`

- [ ] **Step 1: Write failing test for registry**

Create `tests/unit/workflow/test_registry.py`:
```python
"""Tests for workflow registry."""

import pytest

from forge.models.workflow import TicketType


class TestDefaultRouter:
    """Tests for create_default_router."""

    def test_creates_router_with_workflows(self):
        """create_default_router returns router with workflows."""
        from forge.workflow.registry import create_default_router

        router = create_default_router()
        workflows = router.list_workflows()

        assert len(workflows) >= 2

    def test_resolves_feature_to_feature_workflow(self):
        """Feature tickets resolve to FeatureWorkflow."""
        from forge.workflow.registry import create_default_router

        router = create_default_router()
        workflow = router.resolve(TicketType.FEATURE, [], {})

        assert workflow is not None
        assert workflow.name == "feature"

    def test_resolves_bug_to_bug_workflow(self):
        """Bug tickets resolve to BugWorkflow."""
        from forge.workflow.registry import create_default_router

        router = create_default_router()
        workflow = router.resolve(TicketType.BUG, [], {})

        assert workflow is not None
        assert workflow.name == "bug"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/workflow/test_registry.py -v`
Expected: FAIL with import error

- [ ] **Step 3: Implement registry**

Create `src/forge/workflow/registry.py`:
```python
"""Default workflow registry."""

from forge.workflow.router import WorkflowRouter
from forge.workflow.feature import FeatureWorkflow
from forge.workflow.bug import BugWorkflow


def create_default_router() -> WorkflowRouter:
    """Create router with built-in workflows."""
    router = WorkflowRouter()
    router.register(FeatureWorkflow)
    router.register(BugWorkflow)
    return router
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/workflow/test_registry.py -v`
Expected: All tests PASS

- [ ] **Step 5: Update workflow __init__.py exports**

Modify `src/forge/workflow/__init__.py`:
```python
"""Workflow module - pluggable workflow definitions."""

from forge.workflow.base import (
    BaseState,
    BaseWorkflow,
    CIIntegrationState,
    PRIntegrationState,
    ReviewIntegrationState,
)
from forge.workflow.router import WorkflowRouter
from forge.workflow.registry import create_default_router

__all__ = [
    "BaseState",
    "BaseWorkflow",
    "CIIntegrationState",
    "PRIntegrationState",
    "ReviewIntegrationState",
    "WorkflowRouter",
    "create_default_router",
]
```

- [ ] **Step 6: Commit**

```bash
git add src/forge/workflow/registry.py src/forge/workflow/__init__.py tests/unit/workflow/test_registry.py
git commit -m "feat(workflow): add default workflow registry"
```

---

### Task 9: Update Worker to Use Router

**Files:**
- Modify: `src/forge/orchestrator/worker.py`
- Test: Existing worker tests should pass

- [ ] **Step 1: Read current worker implementation**

Review `src/forge/orchestrator/worker.py` to understand current `process_event` flow.

- [ ] **Step 2: Update worker to use router**

Modify `src/forge/orchestrator/worker.py`:

Add import at top:
```python
from forge.workflow.registry import create_default_router
from forge.workflow.router import WorkflowRouter
```

Modify `__init__` to accept router:
```python
def __init__(
    self,
    consumer_name: str | None = None,
    router: WorkflowRouter | None = None,
):
    # ... existing init code ...
    self.router = router or create_default_router()
```

Update `process_event` method to use router for workflow selection (integrate with existing event processing logic).

- [ ] **Step 3: Run existing worker tests**

Run: `uv run pytest tests/unit/orchestrator/test_worker.py -v`
Expected: All tests PASS

- [ ] **Step 4: Run integration tests**

Run: `uv run pytest tests/integration/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/forge/orchestrator/worker.py
git commit -m "feat(orchestrator): integrate WorkflowRouter into worker"
```

---

### Task 10: Backward Compatibility Layer

**Files:**
- Modify: `src/forge/orchestrator/graph.py`
- Modify: `src/forge/orchestrator/state.py`

- [ ] **Step 1: Update orchestrator/state.py to re-export from workflow**

Modify `src/forge/orchestrator/state.py`:
```python
"""Workflow state definitions - re-exported from workflow module for backward compatibility."""

# Re-export everything from workflow.base for backward compatibility
from forge.workflow.base import BaseState

# Re-export FeatureState as WorkflowState for backward compatibility
from forge.workflow.feature.state import FeatureState as WorkflowState
from forge.workflow.feature.state import create_initial_feature_state as create_initial_state

# Keep utility functions
from datetime import datetime


def update_state_timestamp(state: WorkflowState) -> WorkflowState:
    """Update the state timestamp."""
    return {**state, "updated_at": datetime.utcnow().isoformat()}


def set_paused(state: WorkflowState, node_name: str) -> WorkflowState:
    """Set the state to paused at a specific node."""
    return {
        **state,
        "current_node": node_name,
        "is_paused": True,
        "updated_at": datetime.utcnow().isoformat(),
    }


def resume_state(state: WorkflowState) -> WorkflowState:
    """Resume a paused state."""
    return {
        **state,
        "is_paused": False,
        "updated_at": datetime.utcnow().isoformat(),
    }


def set_error(state: WorkflowState, error: str) -> WorkflowState:
    """Record an error in the state."""
    return {
        **state,
        "last_error": error,
        "retry_count": state.get("retry_count", 0) + 1,
        "updated_at": datetime.utcnow().isoformat(),
    }


__all__ = [
    "WorkflowState",
    "create_initial_state",
    "update_state_timestamp",
    "set_paused",
    "resume_state",
    "set_error",
]
```

- [ ] **Step 2: Update graph.py to use workflow module**

Modify `src/forge/orchestrator/graph.py` to import from workflow module and add deprecation notice:
```python
"""LangGraph workflow definition - DEPRECATED.

This module is maintained for backward compatibility.
Use forge.workflow.feature or forge.workflow.bug instead.
"""

import warnings
from forge.workflow.feature.graph import build_feature_graph
from forge.workflow.bug.graph import build_bug_graph
from forge.workflow.registry import create_default_router

# ... keep existing functions but mark as deprecated ...

def get_workflow(checkpointer=None):
    """Get a compiled workflow instance.
    
    DEPRECATED: Use WorkflowRouter.resolve() and workflow.build_graph() instead.
    """
    warnings.warn(
        "get_workflow() is deprecated. Use create_default_router() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Return Feature workflow for backward compatibility
    from forge.workflow.feature import FeatureWorkflow
    workflow = FeatureWorkflow()
    graph = workflow.build_graph()
    return graph.compile(checkpointer=checkpointer)
```

- [ ] **Step 3: Run all tests**

Run: `uv run pytest tests/ -v --ignore=tests/e2e/`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/forge/orchestrator/state.py src/forge/orchestrator/graph.py
git commit -m "refactor: add backward compatibility layer for workflow module"
```

---

### Task 11: Clean Up Old Code

**Files:**
- Delete: Original files from `src/forge/orchestrator/nodes/` (after verifying workflow/nodes works)
- Delete: Original files from `src/forge/orchestrator/gates/` (after verifying workflow/gates works)

- [ ] **Step 1: Verify all imports work from new locations**

Run: `uv run python -c "from forge.workflow.nodes.prd_generation import generate_prd; print('OK')"`
Run: `uv run python -c "from forge.workflow.gates.prd_approval import prd_approval_gate; print('OK')"`

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Remove original node/gate files (keep __init__.py re-exports)**

```bash
# Remove original files but keep __init__.py for backward compatibility
rm src/forge/orchestrator/nodes/prd_generation.py
rm src/forge/orchestrator/nodes/spec_generation.py
# ... etc for all node files except __init__.py
```

- [ ] **Step 4: Run tests again to verify backward compatibility**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove duplicate node/gate files after migration"
```

---

### Task 12: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run linting**

Run: `uv run ruff check src/forge/workflow/`
Expected: No errors

- [ ] **Step 3: Type check**

Run: `uv run mypy src/forge/workflow/ --ignore-missing-imports`
Expected: No critical errors

- [ ] **Step 4: Manual verification**

Start worker and verify it processes events:
```bash
uv run forge worker
```

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete pluggable workflows refactor"
```

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1-4 | Create foundation: BaseState, mixins, router, move nodes/gates |
| 2 | 5-7 | Extract workflows: FeatureState, FeatureWorkflow, BugWorkflow |
| 3 | 8-12 | Wire up: registry, worker integration, backward compat, cleanup |

Total: 12 tasks, ~60 steps
