# Forge

AI-powered SDLC orchestration system for automated planning workflows.

## Overview

Forge automates the generation of Product Requirements Documents (PRDs), Epics, User Stories, Specifications, and Implementation Plans using AI agents and LangGraph workflows. It's designed to work with any Jira project through webhook integration.

## Components

### 1. FastAPI Webhook Gateway (`src/forge/api/`)
- Receives Jira webhook events (status transitions, comments)
- HMAC signature validation
- Redis deduplication
- Publishes ticket_id to Celery queue

### 2. Celery Workers (`src/forge/workers/`)
- Acquire distributed locks per ticket
- Fetch current ticket state from Jira
- Route to appropriate LangGraph node
- Handle retries and error recovery

### 3. LangGraph Nodes (`src/forge/nodes/`)
**Pure content generators** - update state only, orchestration layer handles Jira sync
- `node_1_ideation_agent`: PRD generation (sets state.prd, state.next_status)
- `node_3_epic_generation`: Epic breakdown (sets state.epic_data)
- `node_4_story_and_spec_generation`: User Stories + specs (sets state.story_data)
- `node_5_context_gathering`: Repo analysis (constitution.md)
- `node_6_plan_generation`: Implementation plans (sets state.plan)

### 4. Core Services (`src/forge/core/`)
- Redis client (connection pooling)
- Jira MCP client
- LangGraph workflow definition
- Configuration management

## Project Structure

```
forge/
├── src/forge/
│   ├── api/                    # FastAPI webhook gateway
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── routes/
│   │   │   ├── webhooks.py    # POST /webhooks/jira
│   │   │   └── health.py      # GET /health
│   │   └── middleware/
│   │       └── auth.py        # HMAC validation
│   │
│   ├── workers/               # Celery workers
│   │   ├── __init__.py
│   │   ├── main.py           # Celery app entry point
│   │   ├── tasks.py          # Celery tasks
│   │   └── routing.py        # Status → Node routing
│   │
│   ├── nodes/                # LangGraph nodes
│   │   ├── __init__.py
│   │   ├── node_1_ideation.py
│   │   ├── node_3_epic.py
│   │   ├── node_4_story.py
│   │   ├── node_5_context.py
│   │   └── node_6_plan.py
│   │
│   ├── core/                 # Core services
│   │   ├── __init__.py
│   │   ├── config.py         # Settings management
│   │   ├── redis_client.py   # Redis connection
│   │   ├── jira_client.py    # Jira MCP wrapper
│   │   ├── workflow.py       # LangGraph workflow
│   │   └── logging.py        # Structured logging
│   │
│   ├── prompts/              # LLM prompts
│   │   ├── __init__.py
│   │   ├── prd_template.py
│   │   ├── spec_template.py
│   │   └── plan_template.py
│   │
│   └── schemas/              # Pydantic models
│       ├── __init__.py
│       ├── webhook.py        # Webhook event schemas
│       ├── jira.py           # Jira issue schemas
│       └── state.py          # LangGraph state schema
│
├── tests/
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
│
├── skills/                   # AI agent skills (9 reusable guides)
│   ├── prd-generation/
│   │   └── SKILL.md
│   ├── epic-generation/
│   │   └── SKILL.md
│   ├── spec-generation/
│   │   └── SKILL.md
│   ├── plan-generation/
│   │   └── SKILL.md
│   └── ...                  # 5 more skills
│
├── pyproject.toml           # Project metadata + dependencies
├── .env.example             # Example environment variables
├── Dockerfile               # Docker image
├── docker-compose.yml       # Local development setup
└── README.md               # This file
```

## Setup

### Prerequisites

- Python 3.11+
- Redis 7.0+
- Jira Cloud instance with webhook configuration
- Anthropic API key (for Claude)

### Installation

1. **Navigate to the repository**:
   ```bash
   cd forge
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**:
   ```bash
   # Using uv (recommended - faster)
   uv sync

   # Or using pip
   pip install -e .
   # or for development
   pip install -e ".[dev]"
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Start Redis** (if not running):
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

### Running Locally

**Start FastAPI server**:
```bash
uvicorn forge.api.main:app --reload --port 8000
```

**Start Celery worker**:
```bash
celery -A forge.workers.main worker --loglevel=info
```

**Or use Docker Compose**:
```bash
docker-compose up
```

## Configuration

Environment variables (see `.env.example`):

```bash
# Redis
REDIS_BROKER_URI=redis://localhost:6379/0
REDIS_LOCK_URI=redis://localhost:6379/1
REDIS_DEDUP_URI=redis://localhost:6379/2
REDIS_STATE_URI=redis://localhost:6379/3

# Jira
JIRA_INSTANCE_URL=https://your-org.atlassian.net
JIRA_API_TOKEN=your-token-here
JIRA_PROJECT_KEY=YOUR_PROJECT  # Can be any Jira project

# Webhook
WEBHOOK_SECRET=your-hmac-secret

# Claude AI
ANTHROPIC_API_KEY=sk-ant-...

# Logging
LOG_LEVEL=INFO
```

## Development

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src/forge --cov-report=html

# Specific test file
pytest tests/unit/test_webhook.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Deployment

```bash
# Build Docker image
docker build -t forge:latest .

# Run with Docker Compose
docker-compose up -d
```

## Troubleshooting

### Webhook not triggering

1. Check Jira webhook configuration
2. Verify webhook URL is accessible
3. Check HMAC secret matches
4. Review FastAPI logs for validation errors

### Worker not processing tasks

1. Check Redis connection: `redis-cli ping`
2. Verify Celery broker URL
3. Check worker logs for errors
4. Ensure distributed lock is released

### State not persisting

1. Check Redis DB 3 (state) is accessible
2. Verify LangGraph checkpointer configuration
3. Check thread_id matches ticket_id

## Key Design Principles

- **Programmatic Jira Sync**: Nodes are pure content generators; orchestration layer handles all Jira operations
- **Technology-Agnostic Skills**: Reusable guides that work across different projects and tech stacks
- **Constitution Compliance**: Plans automatically validated against repository constraints
- **Human-in-the-Loop**: Approval gates at PRD, Spec, and Plan stages
- **State Persistence**: Redis-backed checkpointer enables workflow resumption after crashes

