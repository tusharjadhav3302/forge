"""Deep Agents client for AI-powered SDLC orchestration.

Uses LangChain Deep Agents to provide agentic capabilities including
tool use, file operations, and configurable skill paths.
"""

import json
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver

from forge.config import Settings, get_settings
from forge.integrations.langfuse import get_langfuse_config

# Optional Vertex AI support
try:
    from langchain_google_vertexai.model_garden import ChatAnthropicVertex
    HAS_VERTEX = True
except ImportError:
    HAS_VERTEX = False

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent

# Plugin directory containing skills, prompts, and templates
PLUGIN_DIR = PROJECT_ROOT / "plugins" / "forge-sdlc"
PROMPTS_DIR = PLUGIN_DIR / "prompts"

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


def get_weather(city: str) -> str:
    """Placeholder tool for agent testing."""
    return f"Weather data for {city} not available."


class ForgeAgent:
    """AI agent for SDLC orchestration using Deep Agents.

    Provides autonomous task execution with configurable skill paths
    and tool capabilities. The agent selects the best approach for
    each task based on available skills.
    """

    def __init__(self, settings: Settings | None = None):
        """Initialize the Deep Agent client.

        Args:
            settings: Application settings. Uses default if not provided.
        """
        self.settings = settings or get_settings()
        self._ensure_api_key()
        self._checkpointer = MemorySaver()

    def _ensure_api_key(self) -> None:
        """Ensure Anthropic API key is available."""
        if self.settings.use_vertex_ai:
            logger.info("Using Vertex AI backend")
        elif not os.environ.get("ANTHROPIC_API_KEY"):
            api_key = self.settings.anthropic_api_key.get_secret_value()
            if api_key:
                os.environ["ANTHROPIC_API_KEY"] = api_key

    def _create_model(self) -> Any:
        """Create the appropriate chat model based on configuration.

        Returns:
            A LangChain ChatModel instance (ChatAnthropic or ChatAnthropicVertex).
        """
        if self.settings.use_vertex_ai:
            if not HAS_VERTEX:
                raise ImportError(
                    "langchain-google-vertexai is required for Vertex AI. "
                    "Install with: pip install langchain-google-vertexai"
                )
            logger.info(
                f"Creating ChatAnthropicVertex model: {self.settings.claude_model} "
                f"in {self.settings.anthropic_vertex_region}"
            )
            return ChatAnthropicVertex(
                model_name=self.settings.claude_model,
                project=self.settings.anthropic_vertex_project_id,
                location=self.settings.anthropic_vertex_region,
            )
        else:
            logger.info(f"Creating ChatAnthropic model: {self.settings.claude_model}")
            return ChatAnthropic(
                model=self.settings.claude_model,
                api_key=self.settings.anthropic_api_key.get_secret_value(),
            )

    def _get_skill_paths(self) -> list[str]:
        """Get configured skill paths.

        Returns:
            List of skill directory paths (with trailing slashes).
        """
        paths = []
        for path in self.settings.agent_skill_paths.split(","):
            path = path.strip()
            if path:
                # Ensure trailing slash for directory paths
                if not path.endswith("/"):
                    path = f"{path}/"
                paths.append(path)

        if not paths:
            # Default to plugin skills directory
            paths = ["plugins/forge-sdlc/skills/"]

        logger.debug(f"Using skill paths: {paths}")
        return paths

    def _get_root_dir(self) -> Path:
        """Get the root directory for the filesystem backend.

        Returns:
            Path to root directory.
        """
        if self.settings.agent_working_directory:
            return Path(self.settings.agent_working_directory)
        return PROJECT_ROOT

    def _create_agent(
        self,
        system_prompt: str,
        include_tools: bool = True,
    ) -> Any:
        """Create a Deep Agent instance with configured skills.

        Args:
            system_prompt: System prompt for the agent.
            include_tools: Whether to include file/search tools.

        Returns:
            Configured Deep Agent.
        """
        root_dir = self._get_root_dir()
        skill_paths = self._get_skill_paths()

        # Create filesystem backend
        backend = FilesystemBackend(root_dir=str(root_dir))

        # Create the model (supports both direct API and Vertex AI)
        model = self._create_model()

        # Create the agent - no interrupts for automated workflows
        agent = create_deep_agent(
            model=model,
            backend=backend,
            skills=skill_paths,
            system_prompt=system_prompt,
            checkpointer=self._checkpointer,
        )

        return agent

    async def _run_agent(
        self,
        prompt: str,
        system_prompt: str,
        include_tools: bool = True,
        session_id: str | None = None,
        trace_name: str | None = None,
    ) -> str:
        """Run the agent with the given prompt.

        Args:
            prompt: User prompt to send.
            system_prompt: System prompt for the agent.
            include_tools: Whether to include tools.
            session_id: Optional session ID for Langfuse (e.g., ticket key).
            trace_name: Optional trace name for Langfuse.

        Returns:
            Agent response text.
        """
        agent = self._create_agent(
            system_prompt=system_prompt,
            include_tools=include_tools,
        )

        # Generate unique thread ID for this conversation
        thread_id = str(uuid.uuid4())

        # Build config with Langfuse tracing if enabled
        config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

        # Add Langfuse callbacks for observability
        langfuse_config = get_langfuse_config(
            trace_name=trace_name or "deep_agent_invocation",
            session_id=session_id,
            metadata={"system_prompt_length": str(len(system_prompt))},
        )
        if langfuse_config:
            config.update(langfuse_config)

        # Invoke the agent
        result = agent.invoke(
            {
                "messages": [{"role": "user", "content": prompt}],
            },
            config=config,
        )

        # Extract response text from messages
        # Deep Agents returns LangChain message objects, not dicts
        response_text = []
        messages = result.get("messages", []) if isinstance(result, dict) else []

        for message in messages:
            # Check if it's an AI/Assistant message (LangChain message object)
            msg_type = type(message).__name__
            if msg_type in ("AIMessage", "AIMessageChunk"):
                content = message.content
                if isinstance(content, str):
                    response_text.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            response_text.append(block.get("text", ""))
                        elif hasattr(block, "text"):
                            response_text.append(block.text)

        return "\n".join(response_text)

    async def run_task(
        self,
        task: str,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Run a task, letting the agent choose the best approach.

        Deep Agents discovers skills automatically from the configured paths
        and selects the most appropriate one based on the task description.

        Args:
            task: Short task name for logging (e.g., 'generate-prd').
            prompt: The task description and content to process.
            context: Optional context variables for the prompt.

        Returns:
            Agent response text.
        """
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Build system prompt - let agent choose the best approach
        system_prompt = f"""Today's date is {current_date}.

You are an automated SDLC agent. Analyze the task and use the most appropriate skill or approach to complete it.

CRITICAL OUTPUT RULES:
1. DO NOT include any planning, reasoning, or meta-commentary in your response
2. DO NOT say things like "Now I have the template" or "Let me generate..."
3. DO NOT explain what you are doing - just do it
4. Your response should contain ONLY the final deliverable (PRD, spec, plan, code, etc.)
5. Start your response directly with the content - no preamble

Complete the task and return the result immediately."""

        if context:
            system_prompt += "\n\nContext:\n"
            for key, value in context.items():
                system_prompt += f"- {key}: {value}\n"

        # Extract ticket key for session tracking
        ticket_key = context.get("ticket_key") if context else None

        logger.info(f"Running task '{task}' using Deep Agents")
        result = await self._run_agent(
            prompt=prompt,
            system_prompt=system_prompt,
            include_tools=True,
            session_id=ticket_key,
            trace_name=f"task:{task}",
        )

        logger.info(f"Task '{task}' completed ({len(result)} chars)")
        return result

    # Backwards compatibility alias
    async def run_skill(
        self,
        skill_name: str,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Alias for run_task (backwards compatibility)."""
        return await self.run_task(task=skill_name, prompt=prompt, context=context)

        logger.info(f"Skill '{skill_name}' completed ({len(result)} chars)")
        return result

    def _load_mcp_config(self) -> dict[str, Any]:
        """Load MCP server configuration from JSON file.

        Returns:
            Dictionary with MCP server configurations.
        """
        if self.settings.agent_mcp_config_path:
            custom_path = Path(self.settings.agent_mcp_config_path)
            if custom_path.exists():
                return self._parse_mcp_config(custom_path)
            logger.warning(f"MCP config not found at {custom_path}")

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
        return self._expand_env_vars(config)

    def _expand_env_vars(self, obj: Any) -> Any:
        """Recursively expand ${VAR} patterns in config values.

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
            pattern = r"\$\{([^}]+)\}"

            def replace_var(match: re.Match[str]) -> str:
                var_name = match.group(1)
                if var_name in os.environ:
                    return os.environ[var_name]
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

        attr_name = var_name.lower()
        if hasattr(self.settings, attr_name):
            value = getattr(self.settings, attr_name)
            if hasattr(value, "get_secret_value"):
                return value.get_secret_value()
            return str(value)

        logger.warning(f"Unknown variable: {var_name}")
        return ""

    async def generate_prd(
        self,
        raw_requirements: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Generate a structured PRD from raw requirements.

        Uses the 'generate-prd' skill from configured skill paths.

        Args:
            raw_requirements: Raw requirements text.
            context: Optional additional context.

        Returns:
            Generated PRD content.
        """
        prompt = f"""Please create a Product Requirements Document from the following raw requirements:

{raw_requirements}

Additional context:
{context or 'None provided'}

Generate a comprehensive, well-structured PRD following the instructions provided."""

        logger.info("Generating PRD using Deep Agents with skill")
        result = await self.run_skill(
            skill_name="generate-prd",
            prompt=prompt,
            context={
                "ticket_key": context.get("ticket_key", "") if context else "",
                "project_key": context.get("project_key", "") if context else "",
            },
        )

        logger.info(f"Generated PRD ({len(result)} chars)")
        return result

    async def generate_spec(
        self,
        prd_content: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Generate a behavioral specification from a PRD.

        Uses the 'generate-spec' skill from configured skill paths.

        Args:
            prd_content: Approved PRD content.
            context: Optional additional context.

        Returns:
            Generated specification content.
        """
        prompt = f"""Please create a detailed behavioral specification from the following Product Requirements Document:

{prd_content}

Additional context:
{context or 'None provided'}

Generate a comprehensive specification following the instructions provided."""

        logger.info("Generating Spec using Deep Agents with skill")
        result = await self.run_skill(
            skill_name="generate-spec",
            prompt=prompt,
            context={
                "ticket_key": context.get("ticket_key", "") if context else "",
                "project_key": context.get("project_key", "") if context else "",
            },
        )

        logger.info(f"Generated specification ({len(result)} chars)")
        return result

    async def generate_epics(
        self,
        spec_content: str,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        """Generate Epic breakdown from a specification.

        Uses the 'decompose-epics' skill from configured skill paths.

        Args:
            spec_content: Approved specification content.
            context: Optional additional context.

        Returns:
            List of dicts with 'summary' and 'plan' for each Epic.
        """
        available_repos = context.get("available_repos", []) if context else []
        repo_instruction = ""
        if available_repos:
            repo_list = "\n".join(f"  - {r}" for r in available_repos)
            repo_instruction = f"""
AVAILABLE REPOSITORIES:
{repo_list}

IMPORTANT: Each Epic MUST be assigned to one of the repositories listed above.
Use REPO: <owner/repo> format in your output. Do NOT invent new repositories."""
        else:
            repo_instruction = """
NOTE: No repositories configured. Use REPO: unknown for now."""

        prompt = f"""Please decompose the following specification into 2-5 logical Epics with implementation plans:

{spec_content}

Additional context:
- Feature: {context.get('feature_summary', 'Not provided') if context else 'Not provided'}
- Project: {context.get('project_key', 'Not provided') if context else 'Not provided'}
{repo_instruction}

Generate the Epic breakdown following the instructions provided."""

        logger.info("Generating Epics using Deep Agents with skill")
        result = await self.run_skill(
            skill_name="decompose-epics",
            prompt=prompt,
            context={
                "ticket_key": context.get("ticket_key", "") if context else "",
                "project_key": context.get("project_key", "") if context else "",
                "feature_summary": context.get("feature_summary", "") if context else "",
                "available_repos": available_repos,
            },
        )

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
        skill_map = {
            "prd": "generate-prd",
            "spec": "generate-spec",
            "epic": "decompose-epics",
        }
        skill_name = skill_map.get(content_type, "generate-prd")

        prompt = f"""Please revise the following {content_type.upper()} based on the feedback provided:

ORIGINAL CONTENT:
{original_content}

FEEDBACK:
{feedback}

Regenerate the content addressing all feedback points while maintaining the overall structure and quality."""

        logger.info(f"Regenerating {content_type} with feedback using Deep Agents")
        result = await self.run_skill(
            skill_name=skill_name,
            prompt=prompt,
            context={"is_revision": True},
        )

        logger.info(f"Regenerated {content_type} ({len(result)} chars)")
        return result

    @staticmethod
    def _parse_epics_response(response: str) -> list[dict[str, str]]:
        """Parse the Epic generation response into structured data.

        Args:
            response: Raw response from agent.

        Returns:
            List of Epic dicts with 'summary', 'plan', and 'repo'.
        """
        import re

        epics = []
        current_epic: dict[str, str] = {}
        current_section = None
        plan_lines: list[str] = []

        for line in response.split("\n"):
            stripped = line.strip()

            if stripped.startswith("---"):
                if current_epic.get("summary"):
                    current_epic["plan"] = "\n".join(plan_lines).strip()
                    epics.append(current_epic)
                    current_epic = {}
                    plan_lines = []
                continue

            if stripped.startswith("EPIC:"):
                current_epic["summary"] = stripped[5:].strip()
                current_section = "summary"
            elif stripped.startswith("REPO:"):
                # Extract repo (owner/name format)
                repo = stripped[5:].strip()
                # Clean up any extra text
                repo = re.sub(r'[^a-zA-Z0-9/_-]', '', repo)
                if "/" in repo:
                    current_epic["repo"] = repo
            elif stripped.startswith("PLAN:"):
                current_section = "plan"
            elif current_section == "plan":
                plan_lines.append(line)

        if current_epic.get("summary"):
            current_epic["plan"] = "\n".join(plan_lines).strip()
            epics.append(current_epic)

        return epics

    async def close(self) -> None:
        """Close the agent and cleanup resources."""
        pass
