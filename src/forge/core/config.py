"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    debug: bool = False

    # Redis URLs
    redis_broker_uri: str = Field(default="redis://localhost:6379/0")
    redis_lock_uri: str = Field(default="redis://localhost:6379/1")
    redis_dedup_uri: str = Field(default="redis://localhost:6379/2")
    redis_state_uri: str = Field(default="redis://localhost:6379/3")

    # Jira
    jira_instance_url: str = Field(default="https://company.atlassian.net")
    jira_api_token: str = Field(default="")
    jira_project_key: str = Field(default="YOUR_PROJECT")
    jira_user_email: str = Field(default="bot@company.com")

    # Webhook
    webhook_secret: str = Field(default="change-me-in-production")

    # Claude AI
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-sonnet-4-20250514")

    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/0")
    celery_max_retries: int = Field(default=3, ge=1, le=10)

    # FastAPI
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_workers: int = Field(default=4, ge=1)

    # LangFuse (optional)
    langfuse_public_key: str = Field(default="")
    langfuse_secret_key: str = Field(default="")
    langfuse_host: str = Field(default="https://cloud.langfuse.com")

    # GitHub
    github_token: str = Field(default="")
    github_api_url: str = Field(default="https://api.github.com")

    # Monitoring
    prometheus_enabled: bool = Field(default=True)
    metrics_port: int = Field(default=9090, ge=1, le=65535)

    # Feature Flags
    enable_feedback_loops: bool = Field(default=True)
    enable_quality_validation: bool = Field(default=True)
    enable_constitution_checks: bool = Field(default=True)

    @field_validator("jira_instance_url")
    @classmethod
    def validate_jira_url(cls, v: str) -> str:
        """Ensure Jira URL doesn't have trailing slash."""
        return v.rstrip("/")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()
