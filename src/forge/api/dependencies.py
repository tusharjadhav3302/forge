"""FastAPI dependency injection for shared resources."""

from typing import Annotated

from fastapi import Depends

from forge.config import Settings, get_settings
from forge.integrations.github import GitHubClient
from forge.integrations.jira import JiraClient


async def get_jira_client() -> JiraClient:
    """Dependency for Jira client."""
    return JiraClient()


async def get_github_client() -> GitHubClient:
    """Dependency for GitHub client."""
    return GitHubClient()


# Type aliases for dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings)]
JiraClientDep = Annotated[JiraClient, Depends(get_jira_client)]
GitHubClientDep = Annotated[GitHubClient, Depends(get_github_client)]
