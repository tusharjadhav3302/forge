"""Test configuration management."""

from forge.core.config import Settings


def test_settings_defaults():
    """Test default settings values."""
    settings = Settings(
        jira_api_token="test",
        anthropic_api_key="test",
    )

    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.debug is False
    assert settings.api_port == 8000


def test_settings_jira_url_normalization():
    """Test Jira URL trailing slash removal."""
    settings = Settings(
        jira_instance_url="https://test.atlassian.net/",
        jira_api_token="test",
        anthropic_api_key="test",
    )

    assert settings.jira_instance_url == "https://test.atlassian.net"


def test_settings_environment_properties():
    """Test environment check properties."""
    dev_settings = Settings(
        app_env="development",
        jira_api_token="test",
        anthropic_api_key="test",
    )
    assert dev_settings.is_development is True
    assert dev_settings.is_production is False

    prod_settings = Settings(
        app_env="production",
        jira_api_token="test",
        anthropic_api_key="test",
    )
    assert prod_settings.is_production is True
    assert prod_settings.is_development is False
