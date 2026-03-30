"""Guardrails loader for reading constitution and agent guidelines."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Standard paths for guardrail files
CONSTITUTION_PATHS = [
    "CONSTITUTION.md",
    "constitution.md",
    ".claude/CONSTITUTION.md",
    "docs/CONSTITUTION.md",
]

AGENTS_PATHS = [
    "AGENTS.md",
    "agents.md",
    ".claude/AGENTS.md",
    "docs/AGENTS.md",
    "CLAUDE.md",
    ".claude/CLAUDE.md",
]


@dataclass
class Guardrails:
    """Loaded guardrails for code execution."""

    constitution: Optional[str]
    agents: Optional[str]
    repo_path: Path

    @property
    def has_constitution(self) -> bool:
        """Check if constitution is loaded."""
        return self.constitution is not None

    @property
    def has_agents(self) -> bool:
        """Check if agents guidelines are loaded."""
        return self.agents is not None

    def get_system_context(self) -> str:
        """Get combined guardrails as system context.

        Returns:
            Combined constitution and agent guidelines.
        """
        parts = []

        if self.constitution:
            parts.append("# Project Constitution\n\n" + self.constitution)

        if self.agents:
            parts.append("# Agent Guidelines\n\n" + self.agents)

        return "\n\n---\n\n".join(parts) if parts else ""


class GuardrailsLoader:
    """Loads guardrails from repository files."""

    def __init__(self, repo_path: Path):
        """Initialize the guardrails loader.

        Args:
            repo_path: Path to the repository root.
        """
        self.repo_path = repo_path

    def load(self) -> Guardrails:
        """Load guardrails from the repository.

        Returns:
            Loaded Guardrails instance.
        """
        constitution = self._load_file(CONSTITUTION_PATHS)
        agents = self._load_file(AGENTS_PATHS)

        if constitution:
            logger.info(
                f"Loaded constitution ({len(constitution)} chars)"
            )
        else:
            logger.info("No constitution found")

        if agents:
            logger.info(f"Loaded agents guidelines ({len(agents)} chars)")
        else:
            logger.info("No agents guidelines found")

        return Guardrails(
            constitution=constitution,
            agents=agents,
            repo_path=self.repo_path,
        )

    def _load_file(self, candidate_paths: list[str]) -> Optional[str]:
        """Load the first existing file from candidate paths.

        Args:
            candidate_paths: List of paths to try.

        Returns:
            File contents if found, None otherwise.
        """
        for rel_path in candidate_paths:
            full_path = self.repo_path / rel_path
            if full_path.exists() and full_path.is_file():
                try:
                    content = full_path.read_text(encoding="utf-8")
                    logger.debug(f"Loaded guardrails from {rel_path}")
                    return content
                except Exception as e:
                    logger.warning(f"Failed to read {rel_path}: {e}")

        return None

    def validate_guardrails(self, guardrails: Guardrails) -> list[str]:
        """Validate loaded guardrails.

        Args:
            guardrails: Guardrails to validate.

        Returns:
            List of validation warnings.
        """
        warnings = []

        if not guardrails.has_constitution:
            warnings.append(
                "No constitution found. Code execution may lack constraints."
            )

        if not guardrails.has_agents:
            warnings.append(
                "No agents guidelines found. Using default behavior."
            )

        if guardrails.constitution and len(guardrails.constitution) < 100:
            warnings.append(
                "Constitution is very short. Consider expanding guidelines."
            )

        return warnings
