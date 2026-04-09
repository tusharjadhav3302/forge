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
    jira_domain: str = Field(
        default="",
        description="Jira domain for MCP (e.g., company.atlassian.net, derived from base URL if empty)"
    )

    @property
    def jira_domain_resolved(self) -> str:
        """Get Jira domain, derived from base URL if not explicitly set."""
        if self.jira_domain:
            return self.jira_domain
        # Extract domain from base URL (e.g., https://company.atlassian.net -> company.atlassian.net)
        from urllib.parse import urlparse
        parsed = urlparse(self.jira_base_url)
        return parsed.netloc or self.jira_base_url

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

    @property
    def atlassian_auth_base64(self) -> str:
        """Generate base64-encoded auth string for Atlassian MCP (email:api_token)."""
        import base64
        credentials = f"{self.jira_user_email}:{self.jira_api_token.get_secret_value()}"
        return base64.b64encode(credentials.encode()).decode()

    # GitHub Configuration
    github_token: SecretStr = Field(description="GitHub personal access token")
    github_webhook_secret: SecretStr = Field(
        default=SecretStr(""), description="Shared secret for GitHub webhook validation"
    )
    github_default_repo: str = Field(
        default="",
        description="Default repository (owner/repo format) for tasks without explicit repo assignment",
    )
    github_known_repos: str = Field(
        default="",
        description="Comma-separated list of known repositories (owner/repo format) for repo assignment",
    )

    @property
    def known_repos(self) -> list[str]:
        """Get list of known repositories."""
        if not self.github_known_repos:
            return []
        return [r.strip() for r in self.github_known_repos.split(",") if r.strip()]

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

    # Claude Agent SDK Configuration
    agent_enable_tools: bool = Field(
        default=True,
        description="Enable agent tools (Read, Glob, Grep, WebSearch)",
    )
    agent_allowed_tools: str = Field(
        default="*",
        description="Allowed agent tools: '*' for all, or comma-separated list",
    )
    agent_enable_mcp: bool = Field(
        default=True,
        description="Enable MCP server integrations",
    )
    agent_mcp_servers: str = Field(
        default="*",
        description="MCP servers to enable: '*' for all from config, or comma-separated list",
    )
    agent_mcp_read_only: bool = Field(
        default=True,
        description="Restrict MCP tools to read-only operations (no create/update/delete)",
    )
    agent_mcp_config_path: str = Field(
        default="",
        description="Path to MCP servers config file (default: mcp-servers.json in project root)",
    )
    agent_working_directory: str = Field(
        default="",
        description="Working directory for agent file operations (empty = current dir)",
    )
    agent_skill_paths: str = Field(
        default="plugins/forge-sdlc/skills/",
        description="Comma-separated list of skill directories (relative to working dir)",
    )
    agent_backend: str = Field(
        default="filesystem",
        description="Deep Agents backend type: filesystem, state, or store",
    )
    agent_log_file: str = Field(
        default="",
        description="Path to agent trace log file for debugging (empty = no file logging)",
    )
    agent_dev_mode: bool = Field(
        default=False,
        description="Development mode: allow all tools (bash, write) without restrictions",
    )

    # Prompt Configuration
    prompt_version: str = Field(
        default="v1",
        description="Prompt template version to use (e.g., v1, v2)",
    )

    # Application Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    log_file: str = Field(
        default="",
        description="Path to log file (empty = stdout only)",
    )
    ci_fix_max_retries: int = Field(
        default=5, description="Maximum retry attempts for autonomous CI fixes"
    )
    webhook_ack_timeout: float = Field(
        default=0.5, description="Webhook acknowledgment timeout in seconds"
    )

    # OpenTelemetry Configuration
    otlp_endpoint: str = Field(
        default="",
        description="OTLP endpoint for trace export (e.g., http://localhost:4317)",
    )
    otlp_service_name: str = Field(
        default="forge",
        description="Service name for trace attribution",
    )
    tracing_enabled: bool = Field(
        default=True,
        description="Enable distributed tracing",
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
