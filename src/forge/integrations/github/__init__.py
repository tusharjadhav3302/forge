"""GitHub integration for PR management and webhook handling."""

from forge.integrations.github.client import GitHubClient
from forge.integrations.github.webhooks import (
    GitHubWebhookData,
    create_github_webhook_event,
    is_ci_failure,
    is_ci_success,
    is_pr_merged,
    is_pr_review_approved,
    is_pr_review_changes_requested,
    parse_github_webhook,
)

__all__ = [
    "GitHubClient",
    "GitHubWebhookData",
    "create_github_webhook_event",
    "is_ci_failure",
    "is_ci_success",
    "is_pr_merged",
    "is_pr_review_approved",
    "is_pr_review_changes_requested",
    "parse_github_webhook",
]
