# Forge Container Sandbox

The container sandbox provides an isolated environment for AI-powered code implementation. Tasks are executed inside ephemeral Podman containers with full tool access.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Forge Orchestrator                        │
│                                                              │
│  ContainerRunner (runner.py)                                │
│    - Spawns container with workspace mounted                │
│    - Passes credentials via environment                     │
│    - Passes system prompt template via env var              │
│    - Waits for completion with timeout                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Podman Container                          │
│                                                              │
│  entrypoint.py                                              │
│    - Loads system prompt from FORGE_SYSTEM_PROMPT_TEMPLATE  │
│    - Reads task details from mounted /task.json             │
│    - Loads guardrails (CLAUDE.md, AGENTS.md, etc.)          │
│    - Invokes Deep Agents with full tool access              │
│    - Agent decides when/what tests to run                   │
│    - Commits changes on success                             │
└─────────────────────────────────────────────────────────────┘
```

## Container Image

Based on `mcr.microsoft.com/devcontainers/universal:linux` which provides:
- Python, Node.js, Go, Java, C++, Ruby, .NET, PHP, Rust
- Common development tools (git, make, etc.)

Additional packages installed:
- `deepagents` - AI agent framework
- `anthropic`, `langchain-anthropic` - Claude API access
- `langchain-google-vertexai` - Vertex AI support

## Image Configuration

The container image is configurable via the `CONTAINER_IMAGE` environment variable:

```bash
# Local development (default)
CONTAINER_IMAGE=forge-dev:latest

# Production (from registry)
CONTAINER_IMAGE=your-registry.com/forge:v1.0.0
```

## Building (Development)

For local development, build the image manually:

```bash
podman build -t forge-dev:latest -f containers/Containerfile containers/
```

## Production Deployment

For production, push to a container registry and configure `CONTAINER_IMAGE`:

```bash
# Build and tag for registry
podman build -t your-registry.com/forge:v1.0.0 -f containers/Containerfile containers/

# Push to registry
podman push your-registry.com/forge:v1.0.0

# Configure in .env
CONTAINER_IMAGE=your-registry.com/forge:v1.0.0
```

The orchestrator will pull the image from the registry on first task execution.

## Configuration

### Container Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `timeout_seconds` | 7200 (2 hours) | Maximum execution time |
| `memory_limit` | 4g | Container memory limit |
| `cpu_limit` | 2 | CPU cores allocated |
| `network_mode` | slirp4netns | Rootless networking |

### Environment Variables

Passed automatically by the orchestrator:

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key (direct API) |
| `ANTHROPIC_VERTEX_PROJECT_ID` | GCP project for Vertex AI |
| `ANTHROPIC_VERTEX_REGION` | Vertex AI region |
| `CLAUDE_MODEL` | Model to use (e.g., `claude-sonnet-4-5-20250929`) |
| `FORGE_SYSTEM_PROMPT_TEMPLATE` | System prompt template (interpolated by entrypoint) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to mounted gcloud credentials |
| `GIT_USER_NAME` | Git author name for commits (default: `Forge`) |
| `GIT_USER_EMAIL` | Git author email for commits (default: `forge@example.com`) |

### System Prompt

The system prompt is loaded from `src/forge/prompts/v1/container-system.md` and passed to the container via `FORGE_SYSTEM_PROMPT_TEMPLATE`. The entrypoint interpolates these variables:

- `{workspace_path}` - Container workspace path (/workspace)
- `{task_key}` - Jira task key being implemented (e.g., `AISOS-191`)
- `{task_summary}` - Short task description
- `{task_description}` - Detailed task requirements
- `{guardrails}` - Repository guidelines from CLAUDE.md, AGENTS.md, etc.
- `{previous_task_keys}` - List of previously completed task keys for context handoff

## Container Naming

Containers are named for easy identification:
```
forge-{ticket_key}-{repo_name}-{pid}
```

Example: `forge-AISOS-189-installer-12345`

## Task Execution

The entrypoint runs a Deep Agent with full tool access:
1. Reads and understands the codebase
2. Implements the required changes
3. Runs tests **at its discretion** (not forced)
4. Commits changes when ready

The agent has full bash access and decides its own approach to implementation, including when and what tests to run.

## Exit Codes

| Code | Constant | Description |
|------|----------|-------------|
| 0 | `EXIT_SUCCESS` | Task completed successfully |
| 1 | `EXIT_TASK_FAILED` | Agent execution failed |
| 2 | `EXIT_TESTS_FAILED` | Reserved (tests now agent-discretion) |
| 3 | `EXIT_CONFIG_ERROR` | Configuration or setup error |

## Guardrails

The entrypoint automatically loads repository guidelines from:
- `CLAUDE.md`
- `AGENTS.md`
- `constitution.md`
- `agents.md`

These are included in the system prompt to guide the agent's behavior.

## Debugging

View container logs:
```bash
# List running containers
podman ps | grep forge

# View logs
podman logs forge-AISOS-189-installer-12345

# Attach to running container
podman exec -it forge-AISOS-189-installer-12345 bash
```

## Cleanup

Containers are automatically removed after execution (`--rm` flag). To manually clean up:
```bash
# Remove stopped forge containers
podman container prune -f

# Remove old images
podman image prune -f
```
