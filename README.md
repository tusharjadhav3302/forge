# Forge - AI-Integrated SDLC Orchestrator

An intelligent orchestration system that automates the software development lifecycle from Feature ideation through code delivery using AI-powered planning and execution.

## Overview

Forge orchestrates the complete SDLC workflow:

1. **PRD Generation** - Transforms raw Jira Feature descriptions into structured PRDs
2. **Specification Generation** - Creates behavioral specifications with Given/When/Then criteria
3. **Epic Decomposition** - Breaks Features into logical Epics with implementation plans
4. **Task Generation** - Creates implementation Tasks with repository assignments
5. **Code Execution** - Implements Tasks in ephemeral workspaces
6. **CI/CD Validation** - Monitors CI and attempts autonomous fixes
7. **Code Review** - AI-powered review before human approval
8. **Merge Handling** - Aggregates status on successful merge

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Forge Orchestrator                       │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Gateway  │  Redis Queue  │  LangGraph Workflow     │
├─────────────────────────────────────────────────────────────┤
│     Jira          │    GitHub     │   Claude (Anthropic)    │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

- **FastAPI Gateway** - Receives webhooks from Jira and GitHub
- **Redis Queue** - FIFO message queue for event processing
- **LangGraph Workflow** - State machine for SDLC orchestration
- **Integrations** - Jira, GitHub, and Claude Code clients

## Prerequisites

- Python 3.11+
- Redis 7.0+
- Docker and Docker Compose (for local development)
- Jira Cloud account with API access
- GitHub organization with webhook access
- Anthropic API key

## Installation

### Using uv (recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/forge.git
cd forge

# Install dependencies
uv sync

# Copy environment configuration
cp .env.example .env
# Edit .env with your credentials
```

### Using pip

```bash
pip install -e .
```

## Configuration

Create a `.env` file with the following variables:

```bash
# Jira Configuration
JIRA_BASE_URL=https://your-org.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token

# GitHub Configuration
GITHUB_TOKEN=ghp_your_github_token
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY_PATH=/path/to/private-key.pem
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# Anthropic Configuration
ANTHROPIC_API_KEY=sk-ant-your-api-key

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Langfuse Observability (optional)
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Application Settings
LOG_LEVEL=INFO
CI_FIX_MAX_RETRIES=3
WORKSPACE_BASE_PATH=/tmp/forge-workspaces
```

## Running Locally

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f forge
```

### Development Mode

```bash
# Start Redis
docker-compose up -d redis

# Run the API server
uv run uvicorn forge.main:app --reload --port 8000

# In another terminal, run the queue worker
uv run python -m forge.queue.worker
```

## API Endpoints

### Health Check

```
GET /health
```

Returns service health status.

### Jira Webhooks

```
POST /webhooks/jira
```

Receives Jira issue events (created, updated, transitioned).

### GitHub Webhooks

```
POST /webhooks/github
```

Receives GitHub events (check_run, pull_request, pull_request_review).

## Workflow States

### Feature Workflow

```
Drafting PRD → Pending PRD Approval → Drafting Spec → Pending Spec Approval
→ Planning → Pending Plan Approval → In Development → In Review → Done
```

### Bug Workflow

```
Analyzing → Pending RCA Approval → Fixing → In Review → Done
```

## Project Structure

```
src/forge/
├── api/                 # FastAPI routes and middleware
│   ├── routes/         # Endpoint handlers
│   └── middleware/     # Deduplication, validation
├── integrations/       # External service clients
│   ├── jira/          # Jira REST client
│   ├── github/        # GitHub REST client
│   ├── claude/        # Anthropic SDK wrapper
│   └── langfuse/      # Observability
├── models/            # Domain and event models
├── orchestrator/      # LangGraph workflow
│   ├── nodes/        # Workflow node implementations
│   ├── gates/        # Human-in-the-loop gates
│   └── state.py      # Workflow state schema
├── queue/            # Redis Streams producer/consumer
├── workspace/        # Ephemeral workspace management
└── config.py         # Application configuration
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=forge

# Run specific test file
uv run pytest tests/test_workflow.py
```

### Linting and Formatting

```bash
# Check code
uv run ruff check src/

# Format code
uv run ruff format src/
```

### Type Checking

```bash
uv run mypy src/forge/
```

## Deployment

### Docker

```bash
# Build image
docker build -t forge:latest .

# Run container
docker run -p 8000:8000 --env-file .env forge:latest
```

### Kubernetes

Helm charts available in `deploy/helm/forge/`.

```bash
helm install forge ./deploy/helm/forge \
  --set secrets.anthropicApiKey=$ANTHROPIC_API_KEY \
  --set secrets.jiraApiToken=$JIRA_API_TOKEN
```

## Observability

### Langfuse Tracing

All LLM calls are traced to Langfuse for monitoring and debugging:

- PRD generation traces
- Spec generation traces
- Epic decomposition traces
- Code implementation traces
- CI fix attempt traces

### Metrics

Prometheus metrics exposed at `/metrics`:

- `forge_webhooks_received_total` - Webhook events received
- `forge_workflows_started_total` - Workflows started
- `forge_workflows_completed_total` - Workflows completed
- `forge_ci_fix_attempts_total` - CI fix attempts

## Security

- All API tokens stored as secrets (never in code)
- Webhook signature verification for Jira and GitHub
- Ephemeral workspaces cleaned up after PR creation
- No persistent storage of source code

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - See [LICENSE](LICENSE) for details.
