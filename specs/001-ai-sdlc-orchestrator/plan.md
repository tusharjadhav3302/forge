# Implementation Plan: AI-Integrated SDLC Orchestrator

**Branch**: `001-ai-sdlc-orchestrator` | **Date**: 2026-04-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-ai-sdlc-orchestrator/spec.md`

## Summary

Build an AI-driven SDLC orchestrator that automates the software development lifecycle from PRD generation through code review and merge. The system uses LangGraph for cyclical state machine execution, FastAPI for webhook ingestion, and Claude Code for AI-powered code generation. All artifacts are stored in Jira (Zero-UI architecture), with human-in-the-loop gates at key transitions.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: LangGraph, FastAPI, Redis, Anthropic SDK, GitPython, httpx, Deep Agents
**Container Runtime**: Podman (for sandbox isolation during code execution)
**Storage**: Redis (workflow state via LangGraph Checkpointer), Jira (artifacts/source of truth)
**Testing**: pytest, pytest-asyncio, httpx (for API testing)
**Target Platform**: Linux server (containerized deployment)
**Project Type**: web-service (webhook gateway + background orchestrator workers)
**Performance Goals**: Webhook acknowledgment <500ms, 99% of events; PRD/Spec generation <5min
**Constraints**: Must respect Jira/GitHub/LLM API rate limits; FIFO ordering per ticket
**Scale/Scope**: Initial pilot: single repository; Phase 4: multi-repo concurrent execution

### Container Sandbox Architecture

The development phase uses podman containers to provide security isolation while enabling
full AI agent autonomy ("lights-out factory"):

```
┌─────────────────────────────────────────────────────────────────────┐
│  Forge Orchestrator (host)                                         │
│    1. Ensure fork exists (create if needed)                        │
│    2. Clone upstream repo to /tmp/forge-{ticket}/                  │
│    3. Add fork as remote, fetch to sync                            │
│    4. Spawn podman container with repo mounted at /workspace       │
│    5. Wait for container completion                                │
│    6. Push to fork from host (credentials never enter container)   │
│    7. Create PR from fork to upstream via GitHub API               │
│    8. Destroy container and cleanup temp directory                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ podman run --rm -v /tmp/forge-{ticket}:/workspace
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Development Sandbox Container (forge-dev image)                   │
│    Environment:                                                    │
│    - Deep Agents with FilesystemBackend(root_dir="/workspace")     │
│    - ALL tools enabled: write_file, edit_file, execute, glob, grep │
│    - Read-only MCP for external research (docs, search)            │
│    - No host filesystem access beyond /workspace                   │
│    - No cloud credentials, API tokens, or SSH keys                 │
│    - Network: limited to LLM API + read-only external docs         │
│                                                                    │
│    Workflow:                                                       │
│    1. Read constitution.md/agents.md from workspace                │
│    2. Read .forge/handoff.md for context from previous tasks       │
│    3. Implement Tasks using full tool autonomy                     │
│    4. Run local tests (at agent's discretion)                      │
│    5. Git commit (within workspace)                                │
│    6. Save handoff summary to .forge/handoff.md                    │
│    7. Save conversation history to .forge/history/{task}.json      │
│    8. Exit with status code (success/failure)                      │
└─────────────────────────────────────────────────────────────────────┘

### Task Context Handoff

When multiple Tasks target the same repository, context is preserved between
Task implementations via a two-tier handoff mechanism:

```
.forge/
├── handoff.md              # Concise summary (always read by next agent)
│   ## Task: AISOS-101 - Add user authentication
│   - Added auth.py with JWT handling
│   - Key decision: Used PyJWT for simplicity
│   - Tests: test_auth.py added
│
└── history/
    ├── AISOS-101.json      # Full conversation history (read on demand)
    └── AISOS-102.json
```

**Handoff Flow**:
1. Agent starts → reads `.forge/handoff.md` for quick context
2. If deeper context needed → agent reads specific history file
3. Agent implements current task
4. Agent appends summary to `handoff.md`
5. Agent saves full history to `history/{task_key}.json`

**Benefits**:
- Handoff is lightweight (~100 lines), always fits in context window
- Full history available for complex situations requiring deep context
- Per-task history files enable inspection and debugging
- Context survives container restarts and task retries
```

**Container Image Requirements**:

Phase 1 (MVP): Based on devcontainers universal image
- Base: `mcr.microsoft.com/devcontainers/universal:linux`
- Pre-installed: Python, Node, Go, Java, C++, Ruby, .NET, PHP, Rust
- Add: Deep Agents with FilesystemBackend, Anthropic SDK
- Add: Forge-specific entrypoint script
- Git included (for commits, not push)
- Common build tools included (make, gcc, cmake, etc.)
- No pre-installed credentials or secrets
- Image size: ~10GB (devcontainers universal limit, pre-pull on workers)
- Reference: https://github.com/devcontainers/images/tree/main/src/universal

Phase 2 (Optimization): Leverage devcontainer ecosystem
- If repo has `.devcontainer/devcontainer.json` → build/use that image
- If repo has `.forge/container.yaml` → use Forge-specific override
- Fallback to Phase 1 fat image for repos without config
- Benefit: repos already configured for VS Code/Codespaces "just work"

### Fork-Based Workflow

The Forge service account uses a fork-based workflow to avoid requiring write access to
upstream repositories. This provides security isolation and works with any repository
the account can read.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Upstream Repository (org/repo)                                    │
│    - Forge has READ access only                                    │
│    - PRs target this repo's default branch                         │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ PR: forge-account:feature-branch → main
                              │
┌─────────────────────────────────────────────────────────────────────┐
│  Fork Repository (forge-account/repo)                              │
│    - Created automatically if not exists                           │
│    - Synced with upstream before each task                         │
│    - Feature branches pushed here                                  │
│    - Forge has WRITE access                                        │
└─────────────────────────────────────────────────────────────────────┘
```

**Workflow Steps**:

1. **Fork Management** (workspace_setup or pr_creation node):
   - Check if fork exists via GitHub API (`GET /repos/{forge-account}/{repo}`)
   - If not, create fork (`POST /repos/{owner}/{repo}/forks`)
   - Wait for fork to be ready (async operation)

2. **Workspace Setup**:
   - Clone upstream repository (ensures latest code)
   - Add fork as remote: `git remote add fork https://github.com/{forge-account}/{repo}`
   - Fetch fork to get any existing branches

3. **PR Creation**:
   - Push feature branch to fork: `git push fork feature-branch`
   - Create PR via GitHub API with `head: "{forge-account}:feature-branch"`
   - PR targets upstream's default branch

**Configuration**:
- `GITHUB_FORK_OWNER`: The GitHub account/org where forks are created (defaults to authenticated user)
- Fork naming: Same as upstream repo name (GitHub enforces this)

**Benefits**:
- Forge never needs write access to upstream repositories
- Works with any public or readable private repository
- Clear audit trail - all Forge changes come from fork
- No risk of accidental pushes to protected branches

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-Driven Development | PASS | All artifacts (PRD, Spec, Plan, Tasks) generated and stored before execution |
| II. Human-in-the-Loop Gates | PASS | Pause gates at PRD approval, Spec approval, Epic approval, Code review |
| III. Jira as Single Source of Truth | PASS | Zero-UI architecture; all artifacts in Jira fields |
| IV. Trust but Verify | PASS | Agents read constitution.md and current codebase before implementation |
| V. Localized Guardrails | PASS | Repo-level constitution.md/agents.md loaded per workspace |
| VI. Repository-Grouped Concurrency | PASS | Tasks grouped by repo; one PR per repository |
| VII. Ephemeral Workspaces | PASS | Tempfile workspaces destroyed after PR creation |
| VIII. Modular Workflow Routing | PASS | Issue type determines workflow entry point |

**Result**: All constitution principles satisfied. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-sdlc-orchestrator/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── webhook-api.md
│   └── jira-integration.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
forge/
├── containers/
│   ├── Containerfile             # Podman image definition for sandbox
│   └── entrypoint.py             # Container entrypoint (runs Deep Agent)
├── src/
│   └── forge/
│       ├── __init__.py
│       ├── main.py                    # FastAPI application entry
│       ├── config.py                  # Configuration management
│       │
│       ├── api/                       # Webhook Gateway (FastAPI)
│       │   ├── __init__.py
│       │   ├── routes/
│       │   │   ├── __init__.py
│       │   │   ├── jira.py            # Jira webhook handlers
│       │   │   ├── github.py          # GitHub webhook handlers
│       │   │   └── health.py          # Health check endpoints
│       │   ├── middleware/
│       │   │   ├── __init__.py
│       │   │   ├── deduplication.py   # Webhook deduplication
│       │   │   └── validation.py      # Payload validation
│       │   └── dependencies.py        # FastAPI dependencies
│       │
│       ├── orchestrator/              # LangGraph State Machine
│       │   ├── __init__.py
│       │   ├── graph.py               # Main orchestrator graph definition
│       │   ├── state.py               # Workflow state definitions
│       │   ├── checkpointer.py        # Redis checkpointer setup
│       │   ├── nodes/                 # LangGraph nodes
│       │   │   ├── __init__.py
│       │   │   ├── prd_generation.py
│       │   │   ├── spec_generation.py
│       │   │   ├── epic_decomposition.py
│       │   │   ├── task_generation.py
│       │   │   ├── task_router.py
│       │   │   ├── workspace_setup.py
│       │   │   ├── implementation.py
│       │   │   ├── ci_evaluator.py
│       │   │   ├── ai_reviewer.py
│       │   │   └── bug_workflow.py
│       │   └── gates/                 # Pause gates (HITL)
│       │       ├── __init__.py
│       │       ├── prd_approval.py
│       │       ├── spec_approval.py
│       │       ├── plan_approval.py
│       │       ├── task_approval.py
│       │       └── rca_approval.py
│       │
│       ├── integrations/              # External service clients
│       │   ├── __init__.py
│       │   ├── jira/
│       │   │   ├── __init__.py
│       │   │   ├── client.py          # Jira REST API client
│       │   │   ├── models.py          # Jira data models
│       │   │   └── webhooks.py        # Webhook payload parsing
│       │   ├── github/
│       │   │   ├── __init__.py
│       │   │   ├── client.py          # GitHub API client
│       │   │   └── webhooks.py        # Webhook payload parsing
│       │   ├── claude/
│       │   │   ├── __init__.py
│       │   │   └── client.py          # Claude Code SDK wrapper
│       │   └── langfuse/
│       │       ├── __init__.py
│       │       └── tracing.py         # Observability integration
│       │
│       ├── workspace/                 # Ephemeral workspace management
│       │   ├── __init__.py
│       │   ├── manager.py             # Workspace lifecycle
│       │   ├── git_ops.py             # GitPython operations
│       │   └── guardrails.py          # Constitution/agents.md loading
│       │
│       ├── sandbox/                   # Container sandbox for code execution
│       │   ├── __init__.py
│       │   ├── runner.py              # Podman container orchestration
│       │   ├── test_runner.py         # Detect and run repo test commands
│       │   └── config.py              # Container resource limits, network
│       │
│       ├── queue/                     # Message broker integration
│       │   ├── __init__.py
│       │   ├── producer.py            # Event publishing
│       │   ├── consumer.py            # Event consumption
│       │   └── models.py              # Queue message models
│       │
│       └── models/                    # Shared domain models
│           ├── __init__.py
│           ├── workflow.py            # Workflow state models
│           ├── artifacts.py           # PRD, Spec, Plan, Task models
│           └── events.py              # Webhook event models
│
├── tests/
│   ├── conftest.py                    # Shared fixtures
│   ├── contract/                      # API contract tests
│   │   ├── test_webhook_contracts.py
│   │   └── test_jira_contracts.py
│   ├── integration/                   # Integration tests
│   │   ├── test_prd_workflow.py
│   │   ├── test_spec_workflow.py
│   │   └── test_execution_workflow.py
│   └── unit/                          # Unit tests
│       ├── test_nodes/
│       ├── test_integrations/
│       └── test_workspace/
│
├── pyproject.toml                     # Project configuration
├── Dockerfile                         # Container image
├── docker-compose.yml                 # Local development stack
└── README.md                          # Project documentation
```

**Structure Decision**: Single Python project with modular package structure. The `src/forge` layout follows standard Python packaging conventions with clear separation between API layer, orchestrator core, integrations, and workspace management.

## Complexity Tracking

> **No violations requiring justification.** All architecture decisions align with constitution principles.
