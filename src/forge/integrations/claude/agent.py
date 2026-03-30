"""Claude Agent SDK client for AI-powered SDLC orchestration.

Uses the Claude Agent SDK to provide agentic capabilities including
tool use, file operations, and MCP server access.
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    query,
)

from forge.config import Settings, get_settings

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent

# Plugin directory containing skills, prompts, and templates
PLUGIN_DIR = PROJECT_ROOT / "plugins" / "forge-sdlc"
PROMPTS_DIR = PLUGIN_DIR / "prompts"
SKILLS_DIR = PLUGIN_DIR / "skills"

# Default MCP servers config file locations (checked in order)
MCP_CONFIG_PATHS = [
    PROJECT_ROOT / "mcp-servers.json",
    PROJECT_ROOT / "forge-mcp.json",
    Path.home() / ".forge" / "mcp-servers.json",
]

logger = logging.getLogger(__name__)


def load_prompt(name: str, context: dict[str, Any] | None = None) -> str:
    """Load a system prompt from the prompts directory.

    Args:
        name: Prompt name (without .md extension).
        context: Variables to substitute in the prompt.

    Returns:
        Formatted prompt content.
    """
    prompt_file = PROMPTS_DIR / f"{name}.md"

    if not prompt_file.exists():
        logger.warning(f"Prompt file not found: {prompt_file}")
        return ""

    content = prompt_file.read_text()

    # Substitute context variables
    if context:
        for key, value in context.items():
            content = content.replace(f"{{{key}}}", str(value))

    return content


# Fallback prompts if files not found
FALLBACK_PROMPTS = {
    "prd": "Today's date is {current_date}. Generate a PRD using the generate-prd skill.",
    "spec": "Today's date is {current_date}. Generate a spec using the generate-spec skill.",
    "epic": "Today's date is {current_date}. Decompose into epics using the decompose-epics skill.",
}


class ClaudeAgentClient:
    """Agentic client for Claude using the Claude Agent SDK.

    Provides high-level methods for PRD, Spec, and Epic generation
    with full tool use capabilities including file access and MCP servers.
    """

    def __init__(self, settings: Settings | None = None):
        """Initialize the Claude Agent client.

        Args:
            settings: Application settings. Uses default if not provided.
        """
        self.settings = settings or get_settings()
        self._ensure_api_key()

    def _ensure_api_key(self) -> None:
        """Ensure Anthropic API key is available."""
        if self.settings.use_vertex_ai:
            # For Vertex AI, we need GOOGLE_APPLICATION_CREDENTIALS
            logger.info("Using Vertex AI backend")
        elif not os.environ.get("ANTHROPIC_API_KEY"):
            api_key = self.settings.anthropic_api_key.get_secret_value()
            if api_key:
                os.environ["ANTHROPIC_API_KEY"] = api_key

    def _get_agent_options(
        self,
        system_prompt: str,
        include_tools: bool = True,
        include_mcp: bool = False,
        include_skills: bool = True,
    ) -> ClaudeAgentOptions:
        """Configure agent options with tools, MCP servers, and skills.

        Args:
            system_prompt: System prompt for the agent.
            include_tools: Whether to include file/bash tools.
            include_mcp: Whether to include MCP servers.
            include_skills: Whether to enable skills from .claude/skills/.

        Returns:
            Configured ClaudeAgentOptions.
        """
        allowed_tools: list[str] = []
        mcp_servers: dict[str, dict[str, Any]] = {}

        # Always enable Skill tool to use skills from .claude/skills/
        if include_skills:
            allowed_tools.append("Skill")

        # Configure tools based on settings
        if include_tools and self.settings.agent_enable_tools:
            configured_tools = [
                t.strip() for t in self.settings.agent_allowed_tools.split(",")
                if t.strip()
            ]
            allowed_tools.extend(configured_tools)

        # Configure MCP servers based on settings
        if include_mcp and self.settings.agent_enable_mcp:
            enabled_servers = [
                s.strip().lower()
                for s in self.settings.agent_mcp_servers.split(",")
                if s.strip()
            ]
            mcp_servers = self._build_mcp_servers(enabled_servers)
            # Add wildcard permissions for each MCP server
            for server_name in mcp_servers:
                allowed_tools.append(f"mcp__{server_name}__*")

        # Build options
        options_kwargs: dict[str, Any] = {
            "system_prompt": system_prompt,
            "permission_mode": "bypassPermissions",
            "model": self.settings.claude_model,
            # Load skills from project directory (.claude/skills/)
            "setting_sources": ["project"],
            # Set working directory to project root for skill discovery
            "cwd": str(PROJECT_ROOT),
        }

        if allowed_tools:
            options_kwargs["allowed_tools"] = allowed_tools
        if mcp_servers:
            options_kwargs["mcp_servers"] = mcp_servers

        # Override working directory if configured
        if self.settings.agent_working_directory:
            options_kwargs["cwd"] = self.settings.agent_working_directory

        return ClaudeAgentOptions(**options_kwargs)

    def _load_mcp_config(self) -> dict[str, Any]:
        """Load MCP server configuration from JSON file.

        Searches for config file in standard locations and returns
        the parsed configuration.

        Returns:
            Dictionary with MCP server configurations.
        """
        # Check custom path from settings first
        if self.settings.agent_mcp_config_path:
            custom_path = Path(self.settings.agent_mcp_config_path)
            if custom_path.exists():
                return self._parse_mcp_config(custom_path)
            logger.warning(f"MCP config not found at {custom_path}")

        # Check standard locations
        for config_path in MCP_CONFIG_PATHS:
            if config_path.exists():
                logger.debug(f"Loading MCP config from {config_path}")
                return self._parse_mcp_config(config_path)

        logger.debug("No MCP config file found, using empty config")
        return {"mcpServers": {}}

    def _parse_mcp_config(self, config_path: Path) -> dict[str, Any]:
        """Parse MCP config file and expand environment variables.

        Args:
            config_path: Path to the JSON config file.

        Returns:
            Parsed configuration with env vars expanded.
        """
        with open(config_path) as f:
            config = json.load(f)

        # Expand environment variables in the config
        return self._expand_env_vars(config)

    def _expand_env_vars(self, obj: Any) -> Any:
        """Recursively expand ${VAR} patterns in config values.

        Also supports Pydantic SecretStr values from settings.

        Args:
            obj: Config object (dict, list, or string).

        Returns:
            Object with environment variables expanded.
        """
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # Pattern matches ${VAR_NAME}
            pattern = r"\$\{([^}]+)\}"

            def replace_var(match: re.Match[str]) -> str:
                var_name = match.group(1)
                # Check environment first
                if var_name in os.environ:
                    return os.environ[var_name]
                # Check settings (handles SecretStr values)
                return self._get_setting_value(var_name)

            return re.sub(pattern, replace_var, obj)
        return obj

    def _get_setting_value(self, var_name: str) -> str:
        """Get a setting value by name, handling SecretStr.

        Args:
            var_name: Environment variable / setting name.

        Returns:
            The setting value as string, or empty string if not found.
        """
        # Map env var names to settings attributes
        var_mapping = {
            "GITHUB_TOKEN": lambda: self.settings.github_token.get_secret_value(),
            "JIRA_API_TOKEN": lambda: self.settings.jira_api_token.get_secret_value(),
            "JIRA_USER_EMAIL": lambda: self.settings.jira_user_email,
            "JIRA_BASE_URL": lambda: self.settings.jira_base_url,
            "AGENT_WORKING_DIRECTORY": lambda: (
                self.settings.agent_working_directory or os.getcwd()
            ),
            "ANTHROPIC_API_KEY": lambda: (
                self.settings.anthropic_api_key.get_secret_value()
            ),
        }

        if var_name in var_mapping:
            return var_mapping[var_name]()

        # Fallback: try to get from settings by lowercase attribute name
        attr_name = var_name.lower()
        if hasattr(self.settings, attr_name):
            value = getattr(self.settings, attr_name)
            if hasattr(value, "get_secret_value"):
                return value.get_secret_value()
            return str(value)

        logger.warning(f"Unknown variable: {var_name}")
        return ""

    def _build_mcp_servers(
        self, enabled_servers: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Build MCP server configurations based on enabled list.

        Loads server definitions from config file and filters to
        only include enabled servers.

        Args:
            enabled_servers: List of server names to enable.

        Returns:
            Dictionary of MCP server configurations.
        """
        config = self._load_mcp_config()
        all_servers = config.get("mcpServers", {})

        mcp_servers: dict[str, dict[str, Any]] = {}

        for server_name in enabled_servers:
            if server_name in all_servers:
                mcp_servers[server_name] = all_servers[server_name]
                logger.info(f"Enabled MCP server: {server_name}")
            else:
                logger.warning(
                    f"MCP server '{server_name}' not found in config. "
                    f"Available: {list(all_servers.keys())}"
                )

        return mcp_servers

    async def _run_agent(
        self,
        prompt: str,
        system_prompt: str,
        include_tools: bool = True,
        include_mcp: bool = False,
        include_skills: bool = True,
    ) -> str:
        """Run the agent with the given prompt.

        Args:
            prompt: User prompt to send.
            system_prompt: System prompt template.
            include_tools: Whether to include tools.
            include_mcp: Whether to include MCP servers.
            include_skills: Whether to enable skills.

        Returns:
            Agent response text.
        """
        options = self._get_agent_options(
            system_prompt=system_prompt,
            include_tools=include_tools,
            include_mcp=include_mcp,
            include_skills=include_skills,
        )

        results = []

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text"):
                        results.append(block.text)
            elif isinstance(message, ResultMessage):
                logger.info(f"Agent completed: {message.subtype}")

        return "\n".join(results)

    async def generate_prd(
        self,
        raw_requirements: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Generate a structured PRD from raw requirements.

        Uses the 'generate-prd' skill which provides the template and guidelines.

        Args:
            raw_requirements: Raw requirements text from Jira description.
            context: Optional additional context (e.g., project info).

        Returns:
            Generated PRD content.
        """
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Build context for prompt
        prompt_context = {
            "current_date": current_date,
            "ticket_key": context.get("ticket_key", "") if context else "",
            "project_key": context.get("project_key", "") if context else "",
        }

        # Load prompt from file
        system_prompt = load_prompt("prd", prompt_context)
        if not system_prompt:
            system_prompt = FALLBACK_PROMPTS["prd"].format(current_date=current_date)

        prompt = f"""Please create a Product Requirements Document from the following
raw requirements:

{raw_requirements}

Additional context:
{context or 'None provided'}

Use the 'generate-prd' skill to generate a comprehensive, well-structured PRD."""

        logger.info("Generating PRD using Claude Agent SDK with skill")
        result = await self._run_agent(
            prompt=prompt,
            system_prompt=system_prompt,
            include_tools=True,
            include_mcp=False,
            include_skills=True,
        )

        logger.info(f"Generated PRD ({len(result)} chars)")
        return result

    async def generate_spec(
        self,
        prd_content: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Generate a behavioral specification from a PRD.

        Uses the 'generate-spec' skill which provides the template and guidelines.

        Args:
            prd_content: Approved PRD content.
            context: Optional additional context.

        Returns:
            Generated specification content.
        """
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Build context for prompt
        prompt_context = {
            "current_date": current_date,
            "ticket_key": context.get("ticket_key", "") if context else "",
            "project_key": context.get("project_key", "") if context else "",
        }

        # Load prompt from file
        system_prompt = load_prompt("spec", prompt_context)
        if not system_prompt:
            system_prompt = FALLBACK_PROMPTS["spec"].format(current_date=current_date)

        prompt = f"""Please create a detailed behavioral specification from the
following Product Requirements Document:

{prd_content}

Additional context:
{context or 'None provided'}

Use the 'generate-spec' skill to generate a comprehensive specification."""

        logger.info("Generating Spec using Claude Agent SDK with skill")
        result = await self._run_agent(
            prompt=prompt,
            system_prompt=system_prompt,
            include_tools=True,
            include_mcp=False,
            include_skills=True,
        )

        logger.info(f"Generated specification ({len(result)} chars)")
        return result

    async def generate_epics(
        self,
        spec_content: str,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        """Generate Epic breakdown from a specification.

        Uses the 'decompose-epics' skill which provides the template and guidelines.

        Args:
            spec_content: Approved specification content.
            context: Optional additional context (e.g., repo structure).

        Returns:
            List of dicts with 'summary' and 'plan' for each Epic.
        """
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Build context for prompt
        prompt_context = {
            "current_date": current_date,
            "ticket_key": context.get("ticket_key", "") if context else "",
            "project_key": context.get("project_key", "") if context else "",
            "feature_summary": context.get("feature_summary", "") if context else "",
        }

        # Load prompt from file
        system_prompt = load_prompt("epic", prompt_context)
        if not system_prompt:
            system_prompt = FALLBACK_PROMPTS["epic"].format(current_date=current_date)

        prompt = f"""Please decompose the following specification into 2-5
logical Epics with implementation plans:

{spec_content}

Additional context:
{context or 'None provided'}

Use the 'decompose-epics' skill to generate the Epic breakdown."""

        logger.info("Generating Epics using Claude Agent SDK with skill")
        result = await self._run_agent(
            prompt=prompt,
            system_prompt=system_prompt,
            include_tools=True,
            include_mcp=True,
            include_skills=True,
        )

        # Parse the response into Epic structures
        epics = self._parse_epics_response(result)
        logger.info(f"Generated {len(epics)} Epics")
        return epics

    async def regenerate_with_feedback(
        self,
        original_content: str,
        feedback: str,
        content_type: str,
    ) -> str:
        """Regenerate content incorporating feedback.

        Args:
            original_content: The original generated content.
            feedback: User feedback/revision request.
            content_type: Type of content (prd, spec, epic).

        Returns:
            Regenerated content.
        """
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Build context for prompt
        prompt_context = {"current_date": current_date}

        # Load prompt from file
        system_prompt = load_prompt(content_type, prompt_context)
        if not system_prompt:
            fallback = FALLBACK_PROMPTS.get(content_type, FALLBACK_PROMPTS["prd"])
            system_prompt = fallback.format(current_date=current_date)

        # Map content types to skill names
        skill_map = {
            "prd": "generate-prd",
            "spec": "generate-spec",
            "epic": "decompose-epics",
        }
        skill_name = skill_map.get(content_type, "generate-prd")

        prompt = f"""Please revise the following {content_type.upper()} based on
the feedback provided:

ORIGINAL CONTENT:
{original_content}

FEEDBACK:
{feedback}

Use the '{skill_name}' skill to regenerate the content addressing all feedback
points while maintaining the overall structure and quality."""

        logger.info(f"Regenerating {content_type} with feedback using Claude Agent SDK")
        result = await self._run_agent(
            prompt=prompt,
            system_prompt=system_prompt,
            include_tools=True,
            include_skills=True,
        )

        logger.info(f"Regenerated {content_type} ({len(result)} chars)")
        return result

    @staticmethod
    def _parse_epics_response(response: str) -> list[dict[str, str]]:
        """Parse the Epic generation response into structured data.

        Args:
            response: Raw response from Claude.

        Returns:
            List of Epic dicts with 'summary' and 'plan'.
        """
        epics = []
        current_epic: dict[str, str] = {}
        current_section = None
        plan_lines: list[str] = []

        for line in response.split("\n"):
            line = line.strip()

            if line.startswith("---"):
                # Save previous epic if exists
                if current_epic.get("summary"):
                    current_epic["plan"] = "\n".join(plan_lines).strip()
                    epics.append(current_epic)
                    current_epic = {}
                    plan_lines = []
                continue

            if line.startswith("EPIC:"):
                current_epic["summary"] = line[5:].strip()
                current_section = "summary"
            elif line.startswith("PLAN:"):
                current_section = "plan"
            elif current_section == "plan":
                plan_lines.append(line)

        # Don't forget the last epic
        if current_epic.get("summary"):
            current_epic["plan"] = "\n".join(plan_lines).strip()
            epics.append(current_epic)

        return epics

    async def close(self) -> None:
        """Close the client (no-op for Agent SDK)."""
        pass
