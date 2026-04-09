#!/usr/bin/env python3
"""Forge container entrypoint for AI-powered code implementation.

This script runs inside the development sandbox container and:
1. Reads task details from environment or mounted config
2. Loads repository guardrails (constitution.md/agents.md)
3. Runs Deep Agents with full tool access to implement the task
4. Runs local tests to validate implementation
5. Creates git commit with changes
6. Exits with status code indicating success/failure

The orchestrator (outside container) handles git push and PR creation.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Exit codes
EXIT_SUCCESS = 0
EXIT_TASK_FAILED = 1
EXIT_TESTS_FAILED = 2
EXIT_CONFIG_ERROR = 3


def load_guardrails(workspace: Path) -> str:
    """Load repository guardrails from constitution.md or agents.md."""
    guardrails = ""

    for filename in ["CLAUDE.md", "AGENTS.md", "constitution.md", "agents.md"]:
        filepath = workspace / filename
        if filepath.exists():
            logger.info(f"Loading guardrails from {filename}")
            guardrails += f"\n\n# {filename}\n"
            guardrails += filepath.read_text()

    if not guardrails:
        logger.warning("No guardrails file found in workspace")

    return guardrails


def detect_test_command(workspace: Path) -> str | None:
    """Detect the appropriate test command for the repository."""
    # Check for common test configurations
    checks = [
        # Python
        (workspace / "pyproject.toml", "pytest"),
        (workspace / "setup.py", "pytest"),
        (workspace / "pytest.ini", "pytest"),
        # Go
        (workspace / "go.mod", "go test ./..."),
        # Node.js
        (workspace / "package.json", "npm test"),
        # Rust
        (workspace / "Cargo.toml", "cargo test"),
        # Make
        (workspace / "Makefile", "make test"),
    ]

    for marker_file, command in checks:
        if marker_file.exists():
            # For package.json, verify test script exists
            if marker_file.name == "package.json":
                try:
                    pkg = json.loads(marker_file.read_text())
                    if "test" not in pkg.get("scripts", {}):
                        continue
                except (json.JSONDecodeError, KeyError):
                    continue

            # For Makefile, verify test target exists
            if marker_file.name == "Makefile":
                content = marker_file.read_text()
                if "test:" not in content and "test :" not in content:
                    continue

            logger.info(f"Detected test command: {command}")
            return command

    logger.warning("No test command detected")
    return None


def run_tests(workspace: Path, test_command: str) -> bool:
    """Run tests and return True if they pass."""
    logger.info(f"Running tests: {test_command}")

    try:
        result = subprocess.run(
            test_command,
            shell=True,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )

        if result.returncode == 0:
            logger.info("Tests passed")
            return True
        else:
            logger.error(f"Tests failed with exit code {result.returncode}")
            logger.error(f"stdout: {result.stdout[:2000]}")
            logger.error(f"stderr: {result.stderr[:2000]}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Tests timed out after 10 minutes")
        return False
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return False


def git_commit(workspace: Path, message: str) -> bool:
    """Stage all changes and create a commit."""
    try:
        # Stage all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )

        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=workspace,
            capture_output=True,
        )

        if result.returncode == 0:
            logger.info("No changes to commit")
            return True

        # Create commit
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=workspace,
            check=True,
            capture_output=True,
        )

        logger.info(f"Created commit: {message}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Git commit failed: {e}")
        return False


def run_agent_task(
    workspace: Path,
    task_summary: str,
    task_description: str,
    guardrails: str,
) -> bool:
    """Run Deep Agents to implement the task."""
    logger.info(f"Implementing task: {task_summary}")

    try:
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend

        # Check for API credentials
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        vertex_project = os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID")

        if not api_key and not vertex_project:
            logger.error("No API credentials found (ANTHROPIC_API_KEY or ANTHROPIC_VERTEX_PROJECT_ID)")
            return False

        # Create the agent with filesystem backend
        backend = FilesystemBackend(root_dir=str(workspace))

        # Build system prompt with guardrails
        system_prompt = f"""You are an AI software engineer implementing a specific task.

## Workspace
You are working in: /workspace
All file paths should be relative to this directory.

## Task
{task_summary}

## Detailed Requirements
{task_description}

## Repository Guidelines
{guardrails if guardrails else "No specific guidelines provided."}

## Instructions
1. Read and understand the existing codebase structure
2. Implement the task following the repository's coding standards
3. Write clean, well-documented code
4. Ensure your changes are complete and tested
5. Do NOT push to git - only commit your changes locally

Use the available tools to read, write, and edit files as needed.
"""

        # Determine model based on available credentials
        if vertex_project:
            from langchain_google_vertexai.model_garden import ChatAnthropicVertex
            model = ChatAnthropicVertex(
                model_name=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929"),
                project=vertex_project,
                location=os.environ.get("ANTHROPIC_VERTEX_REGION", "us-east5"),
            )
        else:
            from langchain_anthropic import ChatAnthropic
            model = ChatAnthropic(
                model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929"),
                api_key=api_key,
            )

        # Create and run the agent
        agent = create_deep_agent(
            model=model,
            backend=backend,
            system_prompt=system_prompt,
        )

        # Run the agent
        agent.invoke({
            "messages": [{"role": "user", "content": f"Implement this task:\n\n{task_description}"}],
        })

        logger.info("Agent completed task execution")
        return True

    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        return False
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Forge container entrypoint for AI code implementation"
    )
    parser.add_argument(
        "--task-file",
        type=Path,
        help="Path to JSON file with task details",
    )
    parser.add_argument(
        "--task-summary",
        type=str,
        help="Short task summary",
    )
    parser.add_argument(
        "--task-description",
        type=str,
        help="Detailed task description",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests after implementation",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("/workspace"),
        help="Workspace directory (default: /workspace)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum test fix attempts (default: 3)",
    )

    args = parser.parse_args()

    # Load task details
    if args.task_file:
        if not args.task_file.exists():
            logger.error(f"Task file not found: {args.task_file}")
            sys.exit(EXIT_CONFIG_ERROR)

        task_data = json.loads(args.task_file.read_text())
        task_summary = task_data.get("summary", "")
        task_description = task_data.get("description", "")
    elif args.task_summary and args.task_description:
        task_summary = args.task_summary
        task_description = args.task_description
    else:
        logger.error("Task details required: use --task-file or --task-summary + --task-description")
        sys.exit(EXIT_CONFIG_ERROR)

    workspace = args.workspace
    if not workspace.exists():
        logger.error(f"Workspace not found: {workspace}")
        sys.exit(EXIT_CONFIG_ERROR)

    logger.info(f"Workspace: {workspace}")
    logger.info(f"Task: {task_summary}")

    # Load guardrails
    guardrails = load_guardrails(workspace)

    # Detect test command
    test_command = detect_test_command(workspace) if not args.skip_tests else None

    # Implementation loop with test retries
    for attempt in range(args.max_retries + 1):
        if attempt > 0:
            logger.info(f"Retry attempt {attempt}/{args.max_retries}")

        # Run agent to implement task
        if not run_agent_task(workspace, task_summary, task_description, guardrails):
            logger.error("Task implementation failed")
            sys.exit(EXIT_TASK_FAILED)

        # Run tests if configured
        if test_command:
            if run_tests(workspace, test_command):
                break
            elif attempt < args.max_retries:
                # Update task description with test failure context
                task_description += "\n\n## Previous Attempt Failed\nTests failed. Please fix the issues and try again."
                continue
            else:
                logger.error("Tests failed after max retries")
                # Still commit what we have, but exit with failure
                git_commit(workspace, f"[WIP] {task_summary} (tests failing)")
                sys.exit(EXIT_TESTS_FAILED)
        else:
            break

    # Commit changes
    if not git_commit(workspace, f"[forge] {task_summary}"):
        logger.error("Failed to commit changes")
        sys.exit(EXIT_TASK_FAILED)

    logger.info("Task completed successfully")
    sys.exit(EXIT_SUCCESS)


if __name__ == "__main__":
    main()
