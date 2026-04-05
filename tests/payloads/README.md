# Test Webhook Payloads

Sample Jira webhook payloads for testing the Forge workflow.

## Endpoint

```
POST http://localhost:8000/api/v1/webhooks/jira
Content-Type: application/json
```

## Usage with curl

```bash
# Start a new feature workflow
curl -X POST http://localhost:8000/api/v1/webhooks/jira \
  -H "Content-Type: application/json" \
  -d @tests/payloads/01-feature-created.json

# Request PRD revision
curl -X POST http://localhost:8000/api/v1/webhooks/jira \
  -H "Content-Type: application/json" \
  -d @tests/payloads/02-prd-revision-requested.json

# Approve PRD
curl -X POST http://localhost:8000/api/v1/webhooks/jira \
  -H "Content-Type: application/json" \
  -d @tests/payloads/03-prd-approved.json
```

## Workflow Sequence

| # | File | Action | Next State |
|---|------|--------|------------|
| 1 | `01-feature-created.json` | Create feature | PRD generated, `forge:prd-pending` |
| 2 | `02-prd-revision-requested.json` | Comment with feedback | PRD regenerated |
| 3 | `03-prd-approved.json` | Label change | Spec generated, `forge:spec-pending` |
| 4 | `04-spec-revision-requested.json` | Comment with feedback | Spec regenerated |
| 5 | `05-spec-approved.json` | Label change | Epics decomposed, `forge:plan-pending` |
| 6 | `06-plan-revision-requested.json` | Comment with feedback | Epics regenerated |
| 7 | `07-plan-approved.json` | Label change | Tasks generated, execution starts |

## Label Reference

| Stage | Pending | Approved |
|-------|---------|----------|
| PRD | `forge:prd-pending` | `forge:prd-approved` |
| Spec | `forge:spec-pending` | `forge:spec-approved` |
| Plan | `forge:plan-pending` | `forge:plan-approved` |

## Notes

- Set `JIRA_WEBHOOK_SECRET=` (empty) in `.env` to skip signature validation during testing
- Change `TEST-123` to match your actual ticket key
- The workflow must be running (`uv run forge worker`)
