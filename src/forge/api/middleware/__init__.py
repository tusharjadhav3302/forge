"""API middleware modules."""

from forge.api.middleware.deduplication import (
    DeduplicationService,
    generate_idempotency_key,
    get_dedup_service,
)
from forge.api.middleware.validation import (
    ValidationError,
    ValidationResult,
    WebhookSource,
    validate_github_payload,
    validate_jira_payload,
    validate_webhook_payload,
)

__all__ = [
    "DeduplicationService",
    "ValidationError",
    "ValidationResult",
    "WebhookSource",
    "generate_idempotency_key",
    "get_dedup_service",
    "validate_github_payload",
    "validate_jira_payload",
    "validate_webhook_payload",
]
