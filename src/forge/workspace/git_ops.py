"""Git operations for workspace management."""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from forge.config import get_settings
from forge.workspace.manager import Workspace

logger = logging.getLogger(__name__)


class GitOperations:
    """Git operations for cloning, branching, committing, and pushing."""

    def __init__(self, workspace: Workspace):
        """Initialize git operations for a workspace.

        Args:
            workspace: Workspace to operate on.
        """
        self.workspace = workspace
        self.settings = get_settings()

    @property
    def repo_path(self) -> Path:
        """Get the repository path."""
        return self.workspace.path

    def _run_git(
        self,
        *args: str,
        capture_output: bool = True,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a git command in the workspace.

        Args:
            *args: Git command arguments.
            capture_output: Capture stdout/stderr.
            check: Raise on non-zero exit.

        Returns:
            CompletedProcess result.
        """
        cmd = ["git", *args]
        logger.debug(f"Running: {' '.join(cmd)} in {self.repo_path}")

        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=capture_output,
            text=True,
            check=False,
        )

        if check and result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise GitError(f"Git command failed: {' '.join(cmd)}\n{error_msg}")

        return result

    def clone(self, repo_url: Optional[str] = None) -> None:
        """Clone the repository into the workspace.

        Args:
            repo_url: Repository URL. Constructs from settings if None.
        """
        if repo_url is None:
            token = self.settings.github_token.get_secret_value()
            repo_url = (
                f"https://x-access-token:{token}@github.com/"
                f"{self.workspace.repo_name}.git"
            )

        # Clone to workspace path
        subprocess.run(
            ["git", "clone", repo_url, str(self.repo_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info(f"Cloned {self.workspace.repo_name} to {self.repo_path}")

    def create_branch(self, base_branch: str = "main") -> None:
        """Create and checkout a new branch.

        Args:
            base_branch: Base branch to branch from.
        """
        # Fetch latest
        self._run_git("fetch", "origin", base_branch)

        # Create and checkout branch
        self._run_git(
            "checkout", "-b", self.workspace.branch_name,
            f"origin/{base_branch}"
        )
        logger.info(
            f"Created branch {self.workspace.branch_name} "
            f"from {base_branch}"
        )

    def checkout_branch(self, branch_name: Optional[str] = None) -> None:
        """Checkout an existing branch.

        Args:
            branch_name: Branch to checkout. Uses workspace branch if None.
        """
        branch = branch_name or self.workspace.branch_name
        self._run_git("checkout", branch)
        logger.info(f"Checked out branch {branch}")

    def stage_all(self) -> None:
        """Stage all changes."""
        self._run_git("add", "-A")

    def stage_files(self, *files: str) -> None:
        """Stage specific files.

        Args:
            *files: File paths to stage.
        """
        if files:
            self._run_git("add", *files)

    def commit(self, message: str, author_name: str = "Forge") -> bool:
        """Create a commit with the staged changes.

        Args:
            message: Commit message.
            author_name: Author name for the commit.

        Returns:
            True if commit was created, False if nothing to commit.
        """
        # Check if there are changes to commit
        result = self._run_git("status", "--porcelain", check=False)
        if not result.stdout.strip():
            logger.info("Nothing to commit")
            return False

        self._run_git(
            "commit",
            "-m", message,
            "--author", f"{author_name} <forge@noreply.anthropic.com>",
        )
        logger.info(f"Committed: {message[:50]}...")
        return True

    def push(self, force: bool = False) -> None:
        """Push the current branch to origin.

        Args:
            force: Force push (use with caution).
        """
        args = ["push", "-u", "origin", self.workspace.branch_name]
        if force:
            args.insert(1, "--force")

        self._run_git(*args)
        logger.info(f"Pushed branch {self.workspace.branch_name}")

    def get_current_sha(self) -> str:
        """Get the current commit SHA.

        Returns:
            Full commit SHA.
        """
        result = self._run_git("rev-parse", "HEAD")
        return result.stdout.strip()

    def get_diff_stats(self) -> dict[str, int]:
        """Get statistics about changes.

        Returns:
            Dict with files_changed, insertions, deletions.
        """
        result = self._run_git("diff", "--stat", "--cached", check=False)

        stats = {"files_changed": 0, "insertions": 0, "deletions": 0}

        for line in result.stdout.strip().split("\n"):
            if "files changed" in line or "file changed" in line:
                parts = line.split(",")
                for part in parts:
                    part = part.strip()
                    if "file" in part:
                        stats["files_changed"] = int(part.split()[0])
                    elif "insertion" in part:
                        stats["insertions"] = int(part.split()[0])
                    elif "deletion" in part:
                        stats["deletions"] = int(part.split()[0])

        return stats

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes.

        Returns:
            True if there are uncommitted changes.
        """
        result = self._run_git("status", "--porcelain", check=False)
        return bool(result.stdout.strip())

    def reset_hard(self) -> None:
        """Reset all changes (use with caution)."""
        self._run_git("reset", "--hard", "HEAD")
        self._run_git("clean", "-fd")
        logger.info("Reset workspace to HEAD")


class GitError(Exception):
    """Raised when a git operation fails."""

    pass
