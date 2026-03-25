# Claude Code Instructions - Forge

This document provides instructions for Claude Code when working on the Forge project.

---

## Project Overview

**Forge** is an AI-powered orchestration system that automates PRD, Epic, User Story, Spec, and Implementation Plan generation using LangGraph workflows triggered by Jira webhooks. It's designed to work with any Jira project through webhook integration.

**Key Components**:
- **FastAPI webhook gateway**: Validates HMAC, deduplicates, queues ticket_id (< 100ms, NO routing)
- **Celery workers**: Stateless - fetch ticket from Jira, invoke LangGraph with fresh data
- **LangGraph checkpointer**: Automatic state management (load from Redis, merge input, save after node)
- **LangGraph workflow**: Conditional edges route to nodes based on `state.current_status`
- **Redis**: State persistence (DB 3), broker (DB 0), locks (DB 1), deduplication (DB 2)
- **Jira MCP**: Bidirectional sync (read ticket, create/update issues, transition status)

**Critical Understanding - Checkpointer Pattern**:
- Worker provides **minimal input** (just current Jira data)
- Checkpointer **loads existing state** from Redis automatically
- Checkpointer **merges input** into loaded state
- Node executes with **full state** (preserved + fresh data)
- Checkpointer **saves updated state** after node completes

This means worker is **stateless** - it doesn't manage state, just provides fresh input.

---

## Constitution Compliance

**MUST READ FIRST**: [`constitution.md`](constitution.md) defines mandatory technical constraints.

**Critical Rules**:
- ✅ Python 3.11+, FastAPI, Celery, Redis, LangGraph
- ✅ Use Jira MCP tools only (never direct REST API calls)
- ✅ Structured logging via structlog (no print statements)
- ✅ Redis for all state (no file-based persistence)
- ❌ No hardcoded credentials (env vars only)
- ❌ No sync calls in async routes
- ❌ No PII in logs

**Before implementing any feature, verify it complies with constitution.md.**

---

## Project Structure

```
src/forge/
├── api/              # FastAPI webhook gateway
│   ├── main.py      # App entry point
│   ├── routes/      # Endpoint definitions
│   └── middleware/  # HMAC validation, logging
│
├── workers/         # Celery task workers
│   ├── main.py     # Celery app
│   └── tasks.py    # Task definitions (fetch ticket, invoke workflow)
│
├── nodes/          # LangGraph workflow nodes
│   ├── node_1_ideation.py    # PRD generation
│   ├── node_3_epic.py        # Epic breakdown
│   ├── node_4_story.py       # Story + Spec
│   ├── node_5_context.py     # Repo analysis
│   └── node_6_plan.py        # Implementation plan
│
├── core/           # Core services
│   ├── config.py       # Settings (Pydantic)
│   ├── logging.py      # Structured logging
│   ├── redis_client.py # Redis connections
│   ├── jira_client.py  # Jira MCP wrapper
│   └── workflow.py     # LangGraph definition with conditional routing
│
├── prompts/        # LLM templates
│   ├── prd_template.py
│   ├── spec_template.py
│   └── plan_template.py
│
└── schemas/        # Pydantic models
    ├── webhook.py  # Webhook events
    ├── state.py    # WorkflowState
    └── jira.py     # Jira models
```

---

## Skills Reference

The [`skills/`](skills/) directory contains detailed guides for implementing features:

### Generation Skills
- **[prd-generation.md](skills/prd-generation.md)**: PRD template, process, quality checklist
- **[spec-generation.md](skills/spec-generation.md)**: BDD-style Given/When/Then specs
- **[plan-generation.md](skills/plan-generation.md)**: Architecture plans with constitution.md compliance
- **[epic-generation.md](skills/epic-generation.md)**: Breaking PRDs into 2-5 logical Epics

### Workflow Skills
- **[context-gathering.md](skills/context-gathering.md)**: Repo exploration, constitution.md fetching
- **[feedback-incorporation.md](skills/feedback-incorporation.md)**: Handling PM/Tech Lead feedback

### Integration Skills
- **[jira-integration.md](skills/jira-integration.md)**: Markdown to Jira markup, MCP usage
- **[research-discovery.md](skills/research-discovery.md)**: System Catalog search, hallucination prevention
- **[quality-validation.md](skills/quality-validation.md)**: Auto-validation before submission

**Before implementing a node or feature, read the relevant skill.**

---

## Development Workflow

### 1. Understanding Requirements

When asked to implement a feature:
1. **Check Jira**: Read the corresponding story (e.g., YOUR-PROJECT-46)
2. **Read skill**: Find the relevant skill in `skills/` directory
3. **Check constitution**: Verify approach complies with `constitution.md`
4. **Read user stories**: Reference [`outcome-1-user-stories.md`](outcome-1-user-stories.md)

### 2. Implementation Order

**Standard workflow**:
1. **Schema first**: Define Pydantic models in `schemas/`
2. **Core logic**: Implement in appropriate module (`nodes/`, `workers/`, `api/`)
3. **Tests**: Write unit tests in `tests/unit/`
4. **Integration**: Wire up dependencies in `core/`
5. **Validation**: Run tests, linting, type checking

### 3. Testing

**Before claiming anything works**:
```bash
# Run tests
pytest tests/unit/test_<module>.py

# Run specific test
pytest tests/unit/test_webhook.py::test_hmac_validation -v

# Check coverage
pytest --cov=src/aisos --cov-report=term-missing
```

**Don't assume tests pass - verify with actual output.**

### 4. Code Quality

**Before committing**:
```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

---

## Common Tasks

### Adding a New API Endpoint

1. **Define schema** in `schemas/webhook.py` or new file
2. **Create route** in `api/routes/<name>.py`
3. **Register route** in `api/main.py`
4. **Add middleware** if needed (e.g., auth, validation)
5. **Write tests** in `tests/unit/test_api_<name>.py`

**Example**:
```python
# src/forge/api/routes/webhooks.py
from fastapi import APIRouter, HTTPException
from forge.schemas.webhook import WebhookEvent, WebhookResponse

router = APIRouter()

@router.post("/webhooks/jira", response_model=WebhookResponse)
async def receive_jira_webhook(event: WebhookEvent):
    # Validate HMAC (via middleware)
    # Deduplicate (via Redis)
    # Queue to Celery
    return WebhookResponse(status="success", ticket_id=event.ticket_id)
```

### Adding a New LangGraph Node

1. **Read skill**: Check `skills/` for relevant generation skill
2. **Define node function** in `nodes/node_<N>_<name>.py`
3. **Add node to graph** in `core/workflow.py`
4. **Add conditional routing** to map status → node
5. **Write tests** for node logic

**Example Node**:
```python
# src/forge/nodes/node_1_ideation.py
from forge.schemas.state import WorkflowState
from forge.core.logging import get_logger
from forge.core.jira_client import get_jira_client

logger = get_logger(__name__)
jira = get_jira_client()

def node_1_ideation_agent(state: WorkflowState) -> WorkflowState:
    """Generate PRD from Feature ticket description."""
    logger.info("node_started", node="node_1_ideation_agent", ticket_id=state.ticket_id)

    # Fetch current ticket (state has ticket_id)
    ticket = jira.get_issue(state.ticket_id)

    # Generate PRD using Claude
    prd = generate_prd(ticket.description, state.feedback_comment)

    # Update Jira with PRD
    jira.update_issue(state.ticket_id, description=prd)
    jira.transition_issue(state.ticket_id, "Pending PRD Approval")

    # Update state
    state.prd = prd
    state.last_node = "node_1_ideation_agent"
    return state
```

**Example Workflow Definition with Routing and Checkpointer**:
```python
# src/forge/core/workflow.py
from langgraph.graph import StateGraph
from langgraph.checkpoint.redis import RedisSaver
from forge.schemas.state import WorkflowState
from forge.core.config import get_settings
from forge.nodes import node_1_ideation, node_3_epic

settings = get_settings()

def route_by_status(state: WorkflowState) -> str:
    """Route to appropriate node based on current ticket status.

    This is called AFTER checkpointer loads/merges state.
    state.current_status comes from fresh Jira data (via worker input).
    Other fields (state.prd, state.epic_keys) come from Redis checkpoint.
    """
    status = state.current_status

    if status == "Drafting PRD":
        return "node_1_ideation_agent"
    elif status == "In Analysis":
        return "node_3_epic_generation"
    elif status == "Pending PRD Approval":
        return "pause_gate_prd_approval"
    # ... more conditions

    return "end"

# Build graph
workflow = StateGraph(WorkflowState)

# Add nodes
workflow.add_node("node_1_ideation_agent", node_1_ideation.node_1_ideation_agent)
workflow.add_node("node_3_epic_generation", node_3_epic.node_3_epic_generation)
workflow.add_node("pause_gate_prd_approval", pause_gate)

# Add conditional routing from start
# This runs AFTER state is loaded/merged by checkpointer
workflow.add_conditional_edges("__start__", route_by_status)

# Compile with Redis checkpointer
checkpointer = RedisSaver.from_conn_string(settings.redis_state_uri)
checkpointer.setup()  # Create tables/keys if needed

app = workflow.compile(checkpointer=checkpointer)

# How invoke works:
# 1. Load checkpoint from Redis (key: thread_id)
# 2. Merge input into loaded state (updates current_status, feedback_comment)
# 3. Call route_by_status(merged_state) → returns node name
# 4. Execute node (node can read/write state fields)
# 5. Save updated state to Redis
```

**Checkpointer Behavior**:

**First invoke** (thread_id not in Redis):
```python
# Input
workflow.invoke(
    input={"ticket_id": "PROJ-46", "current_status": "Drafting PRD"},
    config={"configurable": {"thread_id": "ticket_PROJ-46"}}
)

# State after checkpointer merge (no existing checkpoint)
state = WorkflowState(
    ticket_id="PROJ-46",
    current_status="Drafting PRD",
    # All other fields use defaults from schema
)

# Routes to node_1_ideation_agent
# Node generates PRD, sets state.prd = "# PRD..."
# Checkpointer saves state to Redis
```

**Second invoke** (thread_id exists in Redis):
```python
# Input (new status after PM approval)
workflow.invoke(
    input={"ticket_id": "PROJ-46", "current_status": "In Analysis"},
    config={"configurable": {"thread_id": "ticket_PROJ-46"}}
)

# State after checkpointer merge (loads from Redis + merges input)
state = WorkflowState(
    ticket_id="PROJ-46",
    current_status="In Analysis",  # NEW from input
    prd="# PRD...",  # PRESERVED from Redis checkpoint
    epic_keys=[],  # PRESERVED from Redis checkpoint
    # etc.
)

# Routes to node_3_epic_generation
# Node reads state.prd, generates Epics, sets state.epic_keys = ["PROJ-14", ...]
# Checkpointer saves updated state to Redis
```

### Adding a New Celery Task

1. **Define task** in `workers/tasks.py`
2. **Configure** in `workers/main.py` (Celery app setup)
3. **Write tests** using `pytest-mock` to mock Celery

**Example Main Worker Task** (stateless - just fetch and invoke):
```python
# src/forge/workers/tasks.py
from celery import Celery
from redis import Redis
from redlock import RedLock
from forge.core.config import get_settings
from forge.core.jira_client import get_jira_client
from forge.core.workflow import get_workflow

settings = get_settings()
app = Celery('aisos', broker=settings.celery_broker_url)
jira = get_jira_client()
workflow = get_workflow()
redis_client = Redis.from_url(settings.redis_lock_uri)

@app.task(bind=True, max_retries=3)
def process_webhook_event(self, ticket_id: str):
    """Process webhook event by invoking LangGraph workflow.

    Worker provides minimal fresh input from Jira.
    LangGraph checkpointer handles state loading/merging/saving.
    """
    lock_key = f"ticket_lock:{ticket_id}"
    lock = RedLock(lock_key, [redis_client], ttl=300000)

    try:
        # Acquire lock
        if not lock.acquire(blocking=True, blocking_timeout=10):
            raise self.retry(countdown=5)

        # Fetch current ticket state from Jira (always fresh)
        ticket = jira.get_issue(ticket_id)

        # Extract latest human comment (for feedback)
        comments = [c for c in ticket.comments if c.author.name != "AI Bot"]
        latest_comment = comments[-1].body if comments else None

        # Invoke LangGraph with minimal input (just current Jira data)
        # Checkpointer loads existing state from Redis automatically
        result = workflow.invoke(
            input={
                "ticket_id": ticket_id,
                "current_status": ticket.fields.status.name,
                "issue_type": ticket.fields.issuetype.name,
                "feedback_comment": latest_comment,
            },
            config={"configurable": {"thread_id": f"ticket_{ticket_id}"}}
        )

        # LangGraph has:
        # 1. Loaded checkpoint from Redis (if exists)
        # 2. Merged new input into state
        # 3. Routed via conditional edges
        # 4. Executed appropriate node
        # 5. Saved updated state to Redis

        return {"status": "success", "ticket_id": ticket_id}

    finally:
        lock.release()
```

**Key Points**:
- Worker only provides **fresh data from Jira** (current status, latest comment)
- Worker does NOT create/manage WorkflowState - checkpointer does this
- Worker is **stateless** - no need to load/save state manually
- LangGraph checkpointer automatically loads state from Redis on each invoke

### Adding a New Prompt Template

1. **Create template** in `prompts/<name>_template.py`
2. **Use LangChain `ChatPromptTemplate`**
3. **Include few-shot examples** (2-3 real examples)
4. **Version in Git** (tag when changing)
5. **Reference in node** that uses the prompt

---

## Environment Setup

### Required Environment Variables

```bash
# Copy example and fill in values
cp .env.example .env

# Minimum required:
JIRA_INSTANCE_URL=https://your-org.atlassian.net
JIRA_API_TOKEN=<your-token>
JIRA_PROJECT_KEY=AISOS
WEBHOOK_SECRET=<generate-random-secret>
ANTHROPIC_API_KEY=<your-claude-key>
```

### Local Development

```bash
# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Install dependencies
pip install -e ".[dev]"

# Run API server
uvicorn forge.api.main:app --reload

# Run Celery worker (separate terminal)
celery -A forge.workers.main worker --loglevel=info
```

**Or use Docker Compose**:
```bash
docker-compose up
```

---

## Debugging

### Checking Logs

**Development (colored console)**:
```bash
# API logs
uvicorn forge.api.main:app --reload --log-level=debug

# Worker logs
celery -A forge.workers.main worker --loglevel=debug
```

**Production (JSON)**:
```bash
export LOG_LEVEL=INFO
export APP_ENV=production
# Logs will be JSON format
```

### Inspecting Redis

```bash
# Connect to Redis
redis-cli

# Check broker queue
LLEN celery

# Check dedup cache
KEYS dedup:*

# Check state
KEYS langgraph:*

# Check locks
KEYS ticket_lock:*
```

### Testing Webhooks Locally

```bash
# Use curl to test webhook endpoint
curl -X POST http://localhost:8000/webhooks/jira \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature: sha256=<hmac>" \
  -d @tests/fixtures/webhook_payload.json
```

---

## Error Handling Patterns

### Validation Errors (Fail Fast)

```python
from fastapi import HTTPException

if not validate_hmac(request, secret):
    raise HTTPException(status_code=400, detail="Invalid HMAC signature")
```

### Transient Errors (Retry)

```python
from forge.core.logging import get_logger

logger = get_logger(__name__)

for attempt in range(3):
    try:
        result = call_external_service()
        break
    except TimeoutError:
        logger.warning("timeout", attempt=attempt)
        time.sleep(2 ** attempt)
else:
    raise Exception("Max retries exceeded")
```

### Permanent Errors (DLQ)

```python
try:
    ticket = jira_mcp.get_issue(ticket_id)
except NotFoundError:
    logger.error("ticket_not_found", ticket_id=ticket_id)
    send_to_dlq(ticket_id, "Ticket not found")
    return
```

---

## Patterns to Follow

### Configuration

```python
from forge.core.config import get_settings

settings = get_settings()  # Cached singleton
redis_uri = settings.redis_broker_uri
```

### Logging

```python
from forge.core.logging import get_logger

logger = get_logger(__name__)

logger.info("event_name", key1=value1, key2=value2)
logger.error("error_event", error=str(e), ticket_id=ticket_id)
```

### State Updates

```python
from forge.schemas.state import WorkflowState
from datetime import datetime

def update_state(state: WorkflowState, prd: str) -> WorkflowState:
    state.prd = prd
    state.last_node = "node_1_ideation_agent"
    state.updated_at = datetime.utcnow()
    return state
```

### Jira Operations

```python
# Always use MCP, never direct API
from forge.core.jira_client import get_jira_client

jira = get_jira_client()

# Fetch current state (always)
ticket = jira.get_issue(ticket_id)

# Create issue
epic = jira.create_issue(
    project_key="AISOS",
    summary="Epic Name",
    issue_type="Epic",
    description=description,
    additional_fields={"parent": "PROJ-1"}
)

# Update issue
jira.update_issue(ticket_id, description=new_description)

# Transition status
jira.transition_issue(ticket_id, "Pending PRD Approval")
```

---

## What NOT to Do

❌ **Don't write code without tests**
- Every new function needs tests in `tests/unit/`

❌ **Don't use print() for debugging**
- Use structured logging: `logger.debug("debug_event", data=data)`

❌ **Don't hardcode values**
- Use `settings = get_settings()` for configuration

❌ **Don't cache Jira ticket data**
- Always fetch current state: `jira.get_issue(ticket_id)`

❌ **Don't ignore constitution.md**
- Check compliance before implementing features

❌ **Don't modify state without updating updated_at**
- Always set `state.updated_at = datetime.utcnow()`

❌ **Don't create sync functions in async modules**
- API routes must be `async def`, use `await` for I/O

---

## Commit Conventions

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `chore`: Build, dependencies, config

**Example**:
```
feat(api): add HMAC signature validation to webhook endpoint

- Implement signature verification using secrets.compare_digest
- Reject invalid signatures with 400 status
- Add tests for valid/invalid signature scenarios

Implements PROJ-46
```

---

## Getting Help

### Documentation
- [`README.md`](README.md): Project overview, setup, usage
- [`constitution.md`](constitution.md): Technical constraints
- [`skills/`](skills/): Implementation guides
- [`outcome-1-user-stories.md`](outcome-1-user-stories.md): User stories for Phase 1

### External References
- FastAPI: https://fastapi.tiangolo.com/
- LangGraph: https://langchain-ai.github.io/langgraph/
- Celery: https://docs.celeryq.dev/
- Pydantic: https://docs.pydantic.dev/

### Questions
- Create GitHub issue with label `question`
- Ask in Slack #forge-orchestrator

---

## Quick Reference

### Start Development

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your values

# Start services
docker-compose up redis  # Just Redis
uvicorn forge.api.main:app --reload  # API
celery -A forge.workers.main worker --loglevel=info  # Worker
```

### Run Tests

```bash
pytest                                    # All tests
pytest tests/unit/                       # Unit tests only
pytest -k test_webhook                   # Specific test
pytest --cov=src/aisos --cov-report=html # Coverage report
```

### Code Quality

```bash
black src/ tests/        # Format
ruff check src/ tests/   # Lint
mypy src/               # Type check
```

### Common Commands

```bash
# Check Redis
redis-cli ping

# View Celery tasks
celery -A forge.workers.main inspect active

# Health check
curl http://localhost:8000/health

# Metrics
curl http://localhost:8000/metrics
```

---

**Remember**: Read the relevant skill before implementing, verify constitution compliance, write tests first, and commit frequently with clear messages.
