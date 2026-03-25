"""Pytest configuration and fixtures."""

import pytest
from pydantic_settings import BaseSettings

from forge.core.config import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Provide test settings."""
    return Settings(
        app_env="development",
        redis_broker_uri="redis://localhost:6379/10",
        redis_lock_uri="redis://localhost:6379/11",
        redis_dedup_uri="redis://localhost:6379/12",
        redis_state_uri="redis://localhost:6379/13",
        jira_instance_url="https://test.atlassian.net",
        jira_api_token="test-token",
        webhook_secret="test-secret",
        anthropic_api_key="test-key",
    )


@pytest.fixture
def sample_webhook_payload() -> dict:
    """Sample Jira webhook payload."""
    return {
        "timestamp": 1711468800000,
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "AISOS-46",
            "id": "10001",
            "fields": {
                "summary": "FastAPI Webhook Endpoints",
                "description": "As a system integrator...",
                "status": {"name": "Drafting PRD", "id": "10002"},
                "issuetype": {"name": "Feature", "id": "10000"},
            },
        },
        "changelog": {
            "items": [
                {
                    "field": "status",
                    "fieldtype": "jira",
                    "from": "10001",
                    "fromString": "Pending PRD Approval",
                    "to": "10002",
                    "toString": "Drafting PRD",
                }
            ]
        },
    }
