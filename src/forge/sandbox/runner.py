"""Container runner for sandbox code execution.

This module handles spawning and managing podman containers for
AI-powered code implementation. The orchestrator uses this to:

1. Spawn a container with the workspace mounted
2. Wait for completion
3. Retrieve exit status and logs
4. Clean up the container

The container runs the entrypoint script which invokes Deep Agents
to implement tasks with full tool access.
"""

import asyncio
import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from forge.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Default container image
DEFAULT_IMAGE = "forge-dev:latest"

# Exit codes from entrypoint.py
EXIT_SUCCESS = 0
EXIT_TASK_FAILED = 1
EXIT_TESTS_FAILED = 2
EXIT_CONFIG_ERROR = 3


@dataclass
class ContainerResult:
    """Result from container execution."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    tests_passed: bool | None = None  # None if tests were skipped
    error_message: str | None = None

    @property
    def tests_failed(self) -> bool:
        """Check if tests specifically failed."""
        return self.exit_code == EXIT_TESTS_FAILED


@dataclass
class ContainerConfig:
    """Configuration for container execution."""

    image: str = DEFAULT_IMAGE
    timeout_seconds: int = 7200  # 2 hours default
    memory_limit: str = "4g"
    cpu_limit: str = "2"
    network_mode: str = "slirp4netns"  # Rootless networking
    skip_tests: bool = False
    max_retries: int = 3
    env_vars: dict[str, str] = field(default_factory=dict)


class ContainerRunner:
    """Manages container lifecycle for sandbox execution.

    This class provides the interface between the Forge orchestrator
    and podman containers. It handles:

    - Container spawning with proper mounts and limits
    - Passing credentials securely via environment
    - Waiting for completion with timeout
    - Capturing logs and exit status
    - Container cleanup
    """

    def __init__(self, settings: Settings | None = None):
        """Initialize the container runner.

        Args:
            settings: Application settings. Uses default if not provided.
        """
        self.settings = settings or get_settings()
        self._verify_podman()

    def _verify_podman(self) -> None:
        """Verify podman is available."""
        if not shutil.which("podman"):
            raise RuntimeError("podman not found in PATH")

    def _build_env_vars(self, config: ContainerConfig) -> dict[str, str]:
        """Build environment variables to pass to container.

        Only passes LLM credentials - no other secrets.
        """
        env = {}

        # Pass Anthropic credentials
        if self.settings.anthropic_api_key.get_secret_value():
            env["ANTHROPIC_API_KEY"] = self.settings.anthropic_api_key.get_secret_value()

        # Pass Vertex AI credentials
        if self.settings.use_vertex_ai:
            env["ANTHROPIC_VERTEX_PROJECT_ID"] = self.settings.anthropic_vertex_project_id
            env["ANTHROPIC_VERTEX_REGION"] = self.settings.anthropic_vertex_region
            # GOOGLE_APPLICATION_CREDENTIALS will be set if we mount gcloud creds
            env["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.config/gcloud/application_default_credentials.json"

        # Pass model configuration
        env["CLAUDE_MODEL"] = self.settings.claude_model

        # Merge with any custom env vars from config
        env.update(config.env_vars)

        return env

    def _get_gcloud_credentials_path(self) -> Path | None:
        """Get path to gcloud application default credentials if they exist."""
        adc_path = Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
        if adc_path.exists():
            return adc_path
        return None

    def _build_podman_command(
        self,
        workspace_path: Path,
        task_file: Path,
        config: ContainerConfig,
    ) -> list[str]:
        """Build the podman run command."""
        cmd = [
            "podman", "run",
            "--rm",  # Remove container after exit
            "--name", f"forge-{os.getpid()}-{id(self)}",
            # Mount workspace
            "-v", f"{workspace_path}:/workspace:Z",
            # Mount task file
            "-v", f"{task_file}:/task.json:ro,Z",
            # Resource limits
            "--memory", config.memory_limit,
            "--cpus", config.cpu_limit,
            # Network (limited)
            "--network", config.network_mode,
            # Working directory
            "-w", "/workspace",
        ]

        # Mount gcloud credentials for Vertex AI authentication
        if self.settings.use_vertex_ai:
            gcloud_creds = self._get_gcloud_credentials_path()
            if gcloud_creds:
                # Mount the credentials file to container
                cmd.extend([
                    "-v", f"{gcloud_creds}:/root/.config/gcloud/application_default_credentials.json:ro,Z",
                ])

        # Add environment variables
        for key, value in self._build_env_vars(config).items():
            cmd.extend(["-e", f"{key}={value}"])

        # Add timeout
        cmd.extend(["--timeout", str(config.timeout_seconds)])

        # Add image
        cmd.append(config.image)

        # Add entrypoint arguments
        cmd.extend([
            "--task-file", "/task.json",
            "--max-retries", str(config.max_retries),
        ])

        if config.skip_tests:
            cmd.append("--skip-tests")

        return cmd

    async def run(
        self,
        workspace_path: Path,
        task_summary: str,
        task_description: str,
        config: ContainerConfig | None = None,
    ) -> ContainerResult:
        """Run a task in a container sandbox.

        Args:
            workspace_path: Path to the cloned repository workspace.
            task_summary: Short task summary.
            task_description: Detailed task description.
            config: Container configuration. Uses defaults if not provided.

        Returns:
            ContainerResult with execution status and logs.
        """
        config = config or ContainerConfig()

        # Create task file
        task_file = workspace_path / ".forge-task.json"
        task_data = {
            "summary": task_summary,
            "description": task_description,
        }
        task_file.write_text(json.dumps(task_data, indent=2))

        try:
            # Build command
            cmd = self._build_podman_command(workspace_path, task_file, config)

            logger.info(f"Starting container for task: {task_summary}")
            logger.debug(f"Command: {' '.join(cmd)}")

            # Run container
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=config.timeout_seconds + 60,  # Extra buffer
                )
            except TimeoutError:
                logger.error("Container execution timed out")
                process.kill()
                await process.wait()
                return ContainerResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr="Container execution timed out",
                    error_message="Timeout exceeded",
                )

            exit_code = process.returncode or 0
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            logger.info(f"Container exited with code {exit_code}")

            # Determine result
            if exit_code == EXIT_SUCCESS:
                return ContainerResult(
                    success=True,
                    exit_code=exit_code,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    tests_passed=True,
                )
            elif exit_code == EXIT_TESTS_FAILED:
                return ContainerResult(
                    success=False,
                    exit_code=exit_code,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    tests_passed=False,
                    error_message="Tests failed after max retries",
                )
            else:
                return ContainerResult(
                    success=False,
                    exit_code=exit_code,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    error_message=f"Task failed with exit code {exit_code}",
                )

        finally:
            # Cleanup task file
            if task_file.exists():
                task_file.unlink()

    async def build_image(
        self,
        containerfile_path: Path | None = None,
        tag: str = DEFAULT_IMAGE,
    ) -> bool:
        """Build the container image.

        Args:
            containerfile_path: Path to Containerfile. Uses default if not provided.
            tag: Image tag. Defaults to forge-dev:latest.

        Returns:
            True if build succeeded.
        """
        if containerfile_path is None:
            # Find Containerfile in project
            project_root = Path(__file__).parent.parent.parent.parent
            containerfile_path = project_root / "containers" / "Containerfile"

        if not containerfile_path.exists():
            logger.error(f"Containerfile not found: {containerfile_path}")
            return False

        context_dir = containerfile_path.parent

        cmd = [
            "podman", "build",
            "-t", tag,
            "-f", str(containerfile_path),
            str(context_dir),
        ]

        logger.info(f"Building container image: {tag}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            logger.info(f"Successfully built image: {tag}")
            return True
        else:
            logger.error(f"Failed to build image: {stderr.decode()}")
            return False

    async def image_exists(self, tag: str = DEFAULT_IMAGE) -> bool:
        """Check if the container image exists locally.

        Args:
            tag: Image tag to check.

        Returns:
            True if image exists.
        """
        cmd = ["podman", "image", "exists", tag]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        await process.wait()
        return process.returncode == 0

    async def pull_base_image(self) -> bool:
        """Pull the devcontainers/universal base image.

        Returns:
            True if pull succeeded.
        """
        cmd = [
            "podman", "pull",
            "mcr.microsoft.com/devcontainers/universal:linux",
        ]

        logger.info("Pulling devcontainers/universal base image...")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            logger.info("Successfully pulled base image")
            return True
        else:
            logger.error(f"Failed to pull base image: {stderr.decode()}")
            return False
