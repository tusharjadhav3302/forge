"""GitHub REST API client for PR and repository operations."""

import logging
from typing import Any, Optional

import httpx

from forge.config import Settings, get_settings

logger = logging.getLogger(__name__)


class GitHubClient:
    """Async client for GitHub REST API.

    Handles authentication and common operations for repositories,
    pull requests, and code reviews.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the GitHub client.

        Args:
            settings: Application settings. Uses default if not provided.
        """
        self.settings = settings or get_settings()
        self.base_url = "https://api.github.com"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with authentication."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {self.settings.github_token.get_secret_value()}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> dict[str, Any]:
        """Create a new pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            title: PR title.
            body: PR description.
            head: Source branch name.
            base: Target branch name.

        Returns:
            API response with PR details.
        """
        client = await self._get_client()
        response = await client.post(
            f"/repos/{owner}/{repo}/pulls",
            json={
                "title": title,
                "body": body,
                "head": head,
                "base": base,
            },
        )
        response.raise_for_status()
        data = response.json()
        logger.info(f"Created PR #{data['number']} in {owner}/{repo}")
        return data

    async def get_pull_request(
        self, owner: str, repo: str, pr_number: int
    ) -> dict[str, Any]:
        """Get pull request details.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            API response with PR details.
        """
        client = await self._get_client()
        response = await client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        response.raise_for_status()
        return response.json()

    async def create_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        commit_id: str,
        path: str,
        line: int,
    ) -> dict[str, Any]:
        """Create a review comment on a PR.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.
            body: Comment text.
            commit_id: Commit SHA to comment on.
            path: File path to comment on.
            line: Line number to comment on.

        Returns:
            API response with comment details.
        """
        client = await self._get_client()
        response = await client.post(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/comments",
            json={
                "body": body,
                "commit_id": commit_id,
                "path": path,
                "line": line,
            },
        )
        response.raise_for_status()
        logger.info(f"Created review comment on PR #{pr_number}")
        return response.json()

    async def create_issue_comment(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> dict[str, Any]:
        """Create a general comment on a PR/issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue/PR number.
            body: Comment text.

        Returns:
            API response with comment details.
        """
        client = await self._get_client()
        response = await client.post(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json={"body": body},
        )
        response.raise_for_status()
        logger.info(f"Created comment on issue #{issue_number}")
        return response.json()

    async def get_check_runs(
        self, owner: str, repo: str, ref: str
    ) -> list[dict[str, Any]]:
        """Get check runs for a commit.

        Args:
            owner: Repository owner.
            repo: Repository name.
            ref: Git reference (commit SHA, branch, or tag).

        Returns:
            List of check run details.
        """
        client = await self._get_client()
        response = await client.get(f"/repos/{owner}/{repo}/commits/{ref}/check-runs")
        response.raise_for_status()
        return response.json().get("check_runs", [])

    async def get_workflow_run_logs(
        self, owner: str, repo: str, run_id: int
    ) -> str:
        """Download workflow run logs.

        Args:
            owner: Repository owner.
            repo: Repository name.
            run_id: Workflow run ID.

        Returns:
            Log content as string.
        """
        client = await self._get_client()
        response = await client.get(
            f"/repos/{owner}/{repo}/actions/runs/{run_id}/logs",
            follow_redirects=True,
        )
        response.raise_for_status()
        return response.text

    async def get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        """Get repository details.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            API response with repository details.
        """
        client = await self._get_client()
        response = await client.get(f"/repos/{owner}/{repo}")
        response.raise_for_status()
        return response.json()
