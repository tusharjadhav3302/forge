# Pluggable Workflows Design

**Date:** 2026-04-14  
**Status:** Approved  
**Author:** eshulman  

## Summary

Refactor the monolithic `graph.py` into modular, self-contained workflow classes. Each workflow owns its graph definition and state schema. A router selects the appropriate workflow based on ticket type and labels. This establishes clean boundaries for future extensibility without over-engineering a full plugin system.

## Goals

1. **Modularity** - Each workflow is self-contained with its own state, graph, and matching logic
2. **Reusability** - Shared nodes (PR creation, CI evaluation) can be used across workflows
3. **Extensibility** - Adding new workflows (Docs, E2E, Refactor) doesn't require modifying existing code
4. **Backward Compatibility** - Existing behavior preserved; this is a refactor, not a rewrite

## Non-Goals (Explicit Exclusions)

- Expression-based routing config (YAML/JSON)
- Entry point plugin discovery
- Hot-reloading of workflows
- Visual workflow builder
- Workflow validation/schema enforcement

These can be added later with real requirements to guide the design.

## Architecture

### Before

```
┌─────────────────────┐
│      graph.py       │
│  (700 lines, all    │
│   workflows mixed)  │
└─────────────────────┘
```

### After

```
┌─────────────────────┐
│   workflow/base.py  │
│   - BaseWorkflow    │
│   - BaseState       │
└─────────────────────┘
         │
┌────────┴────────┐
▼                 ▼
┌──────────────┐  ┌──────────────┐
│ feature/     │  │ bug/         │
│ - FeatureWf  │  │ - BugWf      │
│ - FeatureState│ │ - BugState   │
└──────────────┘  └──────────────┘
         │
         ▼
┌──────────────────────┐
│   router.py          │
│   - matches ticket   │
│   - loads workflow   │
│   - executes graph   │
└──────────────────────┘
```

## Directory Structure

```
src/forge/
├── workflow/
│   ├── base.py              # BaseWorkflow, BaseState
│   ├── router.py            # WorkflowRouter
│   ├── registry.py          # create_default_router()
│   │
│   ├── feature/
│   │   ├── __init__.py      # FeatureWorkflow class
│   │   ├── state.py         # FeatureState
│   │   └── graph.py         # build_graph() wiring
│   │
│   ├── bug/
│   │   ├── __init__.py      # BugWorkflow class
│   │   ├── state.py         # BugState
│   │   └── graph.py         # build_graph() wiring
│   │
│   ├── nodes/               # All nodes as separate files
│   │   ├── prd_generation.py
│   │   ├── spec_generation.py
│   │   ├── epic_decomposition.py
│   │   ├── task_generation.py
│   │   ├── task_router.py
│   │   ├── implementation.py
│   │   ├── pr_creation.py
│   │   ├── ci_evaluator.py
│   │   ├── ai_reviewer.py
│   │   ├── human_review.py
│   │   ├── workspace_setup.py
│   │   ├── bug_workflow.py
│   │   └── error_handler.py
│   │
│   └── gates/               # Gates as separate files
│       ├── prd_approval.py
│       ├── spec_approval.py
│       ├── plan_approval.py
│       └── task_approval.py
│
├── orchestrator/
│   ├── worker.py            # Event loop, uses router
│   └── checkpointer.py      # Redis checkpointing
```

## State Model

### Base State (All Workflows)

```python
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
```

### Integration Mixins

```python
class PRIntegrationState(TypedDict, total=False):
    """Mixin for workflows that create PRs."""
    workspace_path: str | None
    pr_urls: list[str]
    current_pr_url: str | None
    current_pr_number: int | None
    current_repo: str | None
    repos_to_process: list[str]
    repos_completed: list[str]

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
```

### Workflow-Specific State

```python
class FeatureState(BaseState, PRIntegrationState, CIIntegrationState, ReviewIntegrationState, total=False):
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
    implemented_tasks: list[str]
    current_task_key: str | None
    
    # Completion tracking
    tasks_completed: bool
    epics_completed: bool
    feature_completed: bool
    
    # Parallel execution
    parallel_execution_enabled: bool
    parallel_branch_id: int | None
    parallel_total_branches: int | None


class BugState(BaseState, PRIntegrationState, CIIntegrationState, ReviewIntegrationState, total=False):
    """State specific to Bug workflow."""
    ticket_type: TicketType
    
    # Bug-specific
    rca_content: str | None
    bug_fix_implemented: bool
```

## Workflow Interface

```python
from abc import ABC, abstractmethod
from langgraph.graph import StateGraph

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
    def matches(self, ticket_type: TicketType, labels: list[str], event: dict) -> bool:
        """Return True if this workflow should handle the given ticket/event."""
        ...
    
    @abstractmethod
    def build_graph(self) -> StateGraph:
        """Construct and return the LangGraph StateGraph."""
        ...
    
    def create_initial_state(self, ticket_key: str, **kwargs) -> dict:
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

## Router

```python
class WorkflowRouter:
    """Routes incoming tickets to appropriate workflows."""
    
    def __init__(self):
        self._workflows: list[Type[BaseWorkflow]] = []
    
    def register(self, workflow_class: Type[BaseWorkflow]) -> None:
        """Register a workflow class. First match wins."""
        self._workflows.append(workflow_class)
    
    def resolve(
        self, 
        ticket_type: TicketType, 
        labels: list[str], 
        event: dict
    ) -> BaseWorkflow | None:
        """Find the first matching workflow for given ticket/event."""
        for workflow_class in self._workflows:
            instance = workflow_class()
            if instance.matches(ticket_type, labels, event):
                return instance
        return None
    
    def list_workflows(self) -> list[dict]:
        """List all registered workflows (for health/debug endpoints)."""
        return [
            {"name": w.name, "description": w.description}
            for w in self._workflows
        ]


def create_default_router() -> WorkflowRouter:
    """Create router with built-in workflows."""
    router = WorkflowRouter()
    router.register(FeatureWorkflow)
    router.register(BugWorkflow)
    return router
```

## Worker Integration

```python
class OrchestratorWorker:
    def __init__(self, router: WorkflowRouter = None):
        self.router = router or create_default_router()
    
    async def process_event(self, event: QueueMessage):
        ticket = await self.jira.get_issue(event.ticket_key)
        
        workflow = self.router.resolve(
            ticket_type=ticket.ticket_type,
            labels=ticket.labels,
            event=event.payload,
        )
        
        if workflow is None:
            logger.warning(f"No workflow matched for {event.ticket_key}")
            return
        
        graph = workflow.build_graph()
        compiled = graph.compile(checkpointer=self.checkpointer)
        
        initial_state = workflow.create_initial_state(
            ticket_key=event.ticket_key,
        )
        
        await compiled.ainvoke(initial_state, config=...)
```

## Migration Plan

### Phase 1: Create Structure, Preserve Behavior

1. Create `workflow/` directory with `base.py`, `router.py`
2. Split `orchestrator/state.py` into `workflow/base.py` (BaseState) and `workflow/feature/state.py` (FeatureState)
3. Move `orchestrator/nodes/` to `workflow/nodes/`
4. Move `orchestrator/gates/` to `workflow/gates/`
5. Update imports throughout

### Phase 2: Extract Workflows

1. Create `workflow/feature/` with FeatureWorkflow class
2. Move graph building logic from `graph.py` to `workflow/feature/graph.py`
3. Create `workflow/bug/` with BugWorkflow class
4. Extract bug workflow from `graph.py` to `workflow/bug/graph.py`

### Phase 3: Wire Up Router

1. Create `workflow/registry.py` with default router
2. Update `worker.py` to use router instead of calling `graph.py` directly
3. Delete old `graph.py`

## Backward Compatibility

- No config changes required - default router registers same workflows
- Same webhook behavior - tickets route to same workflows
- Checkpoints remain valid - state field names unchanged

## Future Extensibility

This design enables future plugin support without additional refactoring:

```python
# Future: entry point discovery
def create_router_with_plugins() -> WorkflowRouter:
    router = WorkflowRouter()
    
    # Load from entry points
    for ep in importlib.metadata.entry_points(group="forge.workflows"):
        workflow_class = ep.load()
        router.register(workflow_class)
    
    # Built-ins last (can be overridden)
    router.register(FeatureWorkflow)
    router.register(BugWorkflow)
    
    return router
```

## Testing Strategy

1. **Unit tests for router** - Verify matching logic, registration order
2. **Unit tests for state** - Verify inheritance, field defaults
3. **Integration tests** - Run existing workflow tests against new structure
4. **Migration tests** - Verify old checkpoints can be resumed

## Open Questions

None - all questions resolved during design discussion.
