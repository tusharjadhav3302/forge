# Quickstart: AI-Integrated SDLC Orchestrator

**Feature**: 001-ai-sdlc-orchestrator
**Date**: 2026-03-30

## Prerequisites

- Python 3.11+
- Podman & podman-compose (for Redis and containers)
- Jira Cloud instance with admin access
- GitHub repository access
- Claude API key (Anthropic)

## Setup

### 1. Clone and Install

```bash
# Clone repository
git clone <repo-url> forge
cd forge

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### 2. Start Infrastructure

```bash
# Start Redis (for state persistence and message queue)
podman-compose up -d redis

# Verify Redis is running
podman-compose ps
```

### 3. Configure Environment

Create `.env` file in project root:

```bash
# Jira Configuration
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_API_TOKEN=your-api-token
JIRA_USER_EMAIL=your-email@company.com
JIRA_SPEC_CUSTOM_FIELD=customfield_10050
JIRA_WEBHOOK_SECRET=your-webhook-secret

# GitHub Configuration
GITHUB_TOKEN=your-github-token
GITHUB_WEBHOOK_SECRET=your-github-webhook-secret

# Claude Configuration
ANTHROPIC_API_KEY=your-anthropic-api-key

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Langfuse Configuration (optional)
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 4. Configure Jira Webhooks

In Jira Admin:
1. Go to **Settings** > **System** > **Webhooks**
2. Create a new webhook:
   - **URL**: `https://your-domain/api/v1/webhooks/jira`
   - **Events**: Issue updated, Comment created
   - **JQL Filter**: `project = YOURPROJECT` (optional)
3. Note the webhook secret for `JIRA_WEBHOOK_SECRET`

### 5. Configure GitHub Webhooks

In your repository settings:
1. Go to **Settings** > **Webhooks** > **Add webhook**
2. Configure:
   - **Payload URL**: `https://your-domain/api/v1/webhooks/github`
   - **Content type**: `application/json`
   - **Secret**: Set and save for `GITHUB_WEBHOOK_SECRET`
   - **Events**: Pull requests, Check runs, Push events

## Running the Orchestrator

### Development Mode

```bash
# Start the webhook gateway
uvicorn forge.main:app --reload --port 8000

# In another terminal, start the orchestrator worker
python -m forge.orchestrator.worker
```

### Production Mode

```bash
# Start with Docker Compose
podman-compose up -d

# View logs
podman-compose logs -f forge-api forge-worker
```

## Verify Installation

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "redis": "connected",
  "queue_depth": 0
}
```

### Test Webhook

```bash
# Simulate a Jira webhook
curl -X POST http://localhost:8000/api/v1/webhooks/jira \
  -H "Content-Type: application/json" \
  -H "X-Atlassian-Webhook-Identifier: test-123" \
  -d '{
    "webhookEvent": "jira:issue_updated",
    "issue": {
      "key": "TEST-1",
      "fields": {
        "issuetype": {"name": "Feature"},
        "status": {"name": "Drafting PRD"},
        "description": "Test feature description"
      }
    },
    "changelog": {
      "items": [{"field": "status", "toString": "Drafting PRD"}]
    }
  }'
```

Expected response:
```json
{
  "status": "accepted",
  "event_id": "evt_xxx",
  "message": "Event queued for processing"
}
```

## First Workflow

1. **Create a Feature ticket in Jira** with raw requirements in the description
2. **Transition to "Drafting PRD"** status
3. **Watch the logs** - the orchestrator will:
   - Receive the webhook
   - Generate a structured PRD
   - Update the Jira ticket description
   - Transition to "Pending PRD Approval"
4. **Review and approve** by transitioning to "Drafting Spec"
5. **Continue through workflow** following the status transitions

## Troubleshooting

### Webhook Not Received
- Check firewall/ingress rules
- Verify webhook URL is publicly accessible
- Check Jira webhook delivery logs

### Redis Connection Failed
- Verify Redis is running: `podman-compose ps`
- Check `REDIS_URL` configuration
- Test connection: `redis-cli ping`

### Claude API Errors
- Verify `ANTHROPIC_API_KEY` is valid
- Check rate limits in Anthropic dashboard
- Review Langfuse traces for details

### Jira API Errors
- Verify API token has required permissions
- Check custom field ID is correct
- Review error logs for specific API responses

## Next Steps

- Review [plan.md](plan.md) for architecture details
- See [data-model.md](data-model.md) for entity definitions
- Check [contracts/](contracts/) for API specifications
- Run `/speckit.tasks` to generate implementation tasks
