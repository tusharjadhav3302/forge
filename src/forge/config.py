"""Configuration management using Pydantic settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for state persistence and message queue",
    )

    # Jira Configuration
    jira_base_url: str = Field(
        description="Jira instance URL (e.g., https://company.atlassian.net)"
    )
    jira_api_token: SecretStr = Field(description="Jira API token for authentication")
    jira_user_email: str = Field(description="Email associated with Jira API token")
    jira_webhook_secret: SecretStr = Field(
        default=SecretStr(""), description="Shared secret for Jira webhook validation"
    )
    jira_spec_custom_field: str = Field(
        default="",
        description="Custom field ID for Specification storage (optional)",
    )

    # Jira workflow configuration
    jira_use_labels: bool = Field(
        default=True,
        description="Use labels instead of custom statuses for workflow state",
    )
    jira_store_in_comments: bool = Field(
        default=True,
        description="Store PRD/Spec in comments instead of custom fields",
    )

    # GitHub Configuration
    github_token: SecretStr = Field(description="GitHub personal access token")
    github_webhook_secret: SecretStr = Field(
        default=SecretStr(""), description="Shared secret for GitHub webhook validation"
    )

    # Anthropic Configuration
    # Option 1: Direct Anthropic API
    anthropic_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Anthropic API key for Claude (leave empty for Vertex AI)",
    )
    # Option 2: Google Vertex AI
    anthropic_vertex_project_id: str = Field(
        default="",
        description="Google Cloud project ID for Vertex AI",
    )
    anthropic_vertex_region: str = Field(
        default="us-east5",
        description="Google Cloud region for Vertex AI (e.g., us-east5)",
    )
    claude_model: str = Field(
        default="claude-3-5-sonnet-v2@20241022",
        description="Claude model to use (e.g., claude-3-5-sonnet-v2@20241022 for Vertex AI)",
    )

    # Langfuse Configuration
    langfuse_public_key: str = Field(default="", description="Langfuse public key")
    langfuse_secret_key: SecretStr = Field(
        default=SecretStr(""), description="Langfuse secret key"
    )
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com", description="Langfuse host URL"
    )

    # Application Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    ci_fix_max_retries: int = Field(
        default=5, description="Maximum retry attempts for autonomous CI fixes"
    )
    webhook_ack_timeout: float = Field(
        default=0.5, description="Webhook acknowledgment timeout in seconds"
    )

    @property
    def langfuse_enabled(self) -> bool:
        """Check if Langfuse tracing is configured."""
        return bool(
            self.langfuse_public_key
            and self.langfuse_secret_key.get_secret_value()
        )

    @property
    def use_vertex_ai(self) -> bool:
        """Check if using Vertex AI instead of direct Anthropic API."""
        return bool(
            self.anthropic_vertex_project_id
            and not self.anthropic_api_key.get_secret_value()
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
