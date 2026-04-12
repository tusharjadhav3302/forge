<p align="center">
  <img src="docs/images/logo.png" alt="Forge Logo" width="1000">
</p>

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
- Jira Cloud account with API access
- GitHub account with Personal Access Token
- Anthropic API key (or Google Vertex AI access)

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

### Build Container Image (Development)

For local development, build the sandbox container:

```bash
podman build -t forge-dev:latest -f containers/Containerfile containers/
```

For production, configure `CONTAINER_IMAGE` to pull from your registry. See `containers/README.md` for details.

## Configuration

Create a `.env` file with the following variables (see `.env.example` for full list):

```bash
# Jira Configuration
JIRA_BASE_URL=https://your-org.atlassian.net
JIRA_USER_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token

# GitHub Configuration
GITHUB_TOKEN=github_pat_your_token
GITHUB_KNOWN_REPOS=org/repo1,org/repo2
GITHUB_DEFAULT_REPO=org/repo1

# Anthropic Configuration (choose one)
# Option 1: Direct API
ANTHROPIC_API_KEY=sk-ant-your-api-key
# Option 2: Google Vertex AI
ANTHROPIC_VERTEX_PROJECT_ID=your-gcp-project
ANTHROPIC_VERTEX_REGION=us-east5

# Claude Model
CLAUDE_MODEL=claude-opus-4-5@20251101

# Redis Configuration
REDIS_URL=redis://localhost:6380/0

# MCP Servers (all enabled by default)
AGENT_ENABLE_MCP=true
AGENT_MCP_SERVERS=*

# Langfuse Observability (optional)
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### MCP Servers

Forge agents have access to MCP (Model Context Protocol) servers for external integrations. Configure in `mcp-servers.json`:

| Server | Description | Auth Required |
|--------|-------------|---------------|
| `github` | GitHub Copilot MCP | `GITHUB_TOKEN` |
| `atlassian` | Local Atlassian MCP (SSE) | `JIRA_USER_EMAIL` + `JIRA_API_TOKEN` |
| `context7` | Upstash Context7 for library docs | Optional API key |
| `gitmcp` | GitMCP.io for repo documentation | None |

By default, MCP tools are restricted to **read-only operations** (`AGENT_MCP_READ_ONLY=true`).

## Running Locally

### Using Podman Compose (not tested)

```bash
# Start all services
podman-compose up -d

# View logs
podman-compose logs -f forge
```

### Development Mode

```bash
# Start Redis
podman-compose up -d redis

# Run the API server
uv run uvicorn forge.main:app --reload --port 8000

# In another terminal, run the queue worker
uv run forge worker
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
│   ├── agents/        # Deep Agents with MCP integration
│   └── langfuse/      # Observability
├── models/            # Domain and event models
├── orchestrator/      # LangGraph workflow
│   ├── nodes/        # Workflow node implementations
│   ├── gates/        # Human-in-the-loop gates
│   └── state.py      # Workflow state schema
├── prompts/           # Versioned prompt templates
│   └── v1/           # Prompt version 1
├── queue/            # Redis Streams producer/consumer
├── workspace/        # Ephemeral workspace management
└── config.py         # Application configuration

mcp-servers.json       # MCP server configurations
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

## Observability

### Langfuse Tracing

All LLM calls are traced to Langfuse for monitoring and debugging:

- PRD generation traces
- Spec generation traces
- Epic decomposition traces
- Code implementation traces
- CI fix attempt traces

### Metrics

Prometheus metrics exposed at `GET /metrics`:

- `forge_webhooks_received_total` - Webhook events received (by source, event_type)
- `forge_webhooks_processed_total` - Webhook events processed
- `forge_workflows_started_total` - Workflows started (by ticket_type)
- `forge_workflows_completed_total` - Workflows completed (by ticket_type, final_node)
- `forge_ci_fix_attempts_total` - CI fix attempts (by repo, result)
- `forge_agent_invocations_total` - Agent invocations (by task_type)
- `forge_agent_duration_seconds` - Agent invocation duration histogram
- `forge_queue_depth` - Current event queue depth
- `forge_mcp_tools_loaded` - MCP tools loaded per server

## Security

- Webhook signature verification for Jira and GitHub
- Ephemeral workspaces cleaned up after PR creation
- No persistent storage of source code

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request


