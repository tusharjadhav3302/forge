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

# Optional MCP support
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

from forge.config import Settings, get_settings
from forge.integrations.langfuse import get_langfuse_config
from forge.prompts import load_prompt, set_default_version

# Optional Vertex AI support
try:
    from langchain_google_vertexai.model_garden import ChatAnthropicVertex
    HAS_VERTEX = True
except ImportError:
    HAS_VERTEX = False

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent

# Default MCP servers config file locations (checked in order)
MCP_CONFIG_PATHS = [
    PROJECT_ROOT / "mcp-servers.json",
    PROJECT_ROOT / "forge-mcp.json",
    Path.home() / ".forge" / "mcp-servers.json",
]

logger = logging.getLogger(__name__)




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
        self._current_repo: str = ""  # Set per-task for dynamic MCP URLs

        # Set prompt version from config
        set_default_version(self.settings.prompt_version)

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

    def _get_allowed_tools(self) -> list[str] | None:
        """Get list of allowed tools based on config.

        Returns:
            List of tool names, or None if all tools allowed.
        """
        if not self.settings.agent_enable_tools:
            logger.debug("Agent tools disabled via config")
            return []

        allowed = self.settings.agent_allowed_tools.strip()
        if allowed == "*":
            logger.debug("All agent tools allowed")
            return None  # None means all tools

        tools = [t.strip() for t in allowed.split(",") if t.strip()]
        logger.debug(f"Allowed agent tools: {tools}")
        return tools

    def _get_root_dir(self) -> Path:
        """Get the root directory for the filesystem backend.

        Returns:
            Path to root directory.
        """
        if self.settings.agent_working_directory:
            return Path(self.settings.agent_working_directory)
        return PROJECT_ROOT

    async def _load_mcp_tools(self) -> list[Any]:
        """Load tools from configured MCP servers.

        Returns:
            List of tools from MCP servers.
        """
        if not HAS_MCP:
            logger.warning("langchain-mcp-adapters not installed, MCP tools unavailable")
            return []

        mcp_config = self._load_mcp_config()

        if not mcp_config:
            logger.debug("No MCP servers configured")
            return []

        logger.info(f"Loading MCP tools from servers: {list(mcp_config.keys())}")

        try:
            client = MultiServerMCPClient(mcp_config)
            tools = await client.get_tools()
            logger.info(f"Loaded {len(tools)} tools from MCP servers")
            return tools
        except Exception as e:
            logger.error(f"Failed to load MCP tools: {e}")
            return []

    async def _create_agent_async(
        self,
        system_prompt: str,
        include_tools: bool = True,
    ) -> Any:
        """Create a Deep Agent instance with configured skills and MCP tools.

        Args:
            system_prompt: System prompt for the agent.
            include_tools: Whether to include file/search tools.

        Returns:
            Configured Deep Agent.
        """
        root_dir = self._get_root_dir()
        skill_paths = self._get_skill_paths()
        allowed_tools = self._get_allowed_tools()

        # Log configuration for visibility
        logger.info(f"Agent config: root_dir={root_dir}, skills={skill_paths}")
        logger.info(f"Agent tools: {'all' if allowed_tools is None else allowed_tools}")

        # Create filesystem backend
        backend = FilesystemBackend(root_dir=str(root_dir))

        # Create the model (supports both direct API and Vertex AI)
        model = self._create_model()

        # Load MCP tools if enabled
        mcp_tools = await self._load_mcp_tools() if include_tools else []

        # Create the agent with MCP tools
        agent = create_deep_agent(
            model=model,
            backend=backend,
            skills=skill_paths,
            system_prompt=system_prompt,
            checkpointer=self._checkpointer,
            tools=mcp_tools if mcp_tools else None,
        )

        return agent

    def _create_agent(
        self,
        system_prompt: str,
        include_tools: bool = True,
    ) -> Any:
        """Create a Deep Agent instance (sync wrapper).

        For MCP tools, use _create_agent_async instead.

        Args:
            system_prompt: System prompt for the agent.
            include_tools: Whether to include file/search tools.

        Returns:
            Configured Deep Agent.
        """
        root_dir = self._get_root_dir()
        skill_paths = self._get_skill_paths()
        allowed_tools = self._get_allowed_tools()
        mcp_config = self._load_mcp_config()

        # Log configuration for visibility
        logger.info(f"Agent config: root_dir={root_dir}, skills={skill_paths}")
        logger.info(f"Agent tools: {'all' if allowed_tools is None else allowed_tools}")
        logger.info(f"Agent MCP servers: {list(mcp_config.keys())}")

        # Create filesystem backend
        backend = FilesystemBackend(root_dir=str(root_dir))

        # Create the model (supports both direct API and Vertex AI)
        model = self._create_model()

        # Create the agent (MCP tools loaded in async version)
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
        # Use async version to load MCP tools
        agent = await self._create_agent_async(
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

        # Set current repo for dynamic MCP URLs (e.g., gitmcp.io/{owner}/{repo})
        if context and context.get("current_repo"):
            self._current_repo = context["current_repo"]

        # Load system prompt from file
        system_prompt = load_prompt("system", current_date=current_date)

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

    def _load_mcp_config(self) -> dict[str, Any]:
        """Load MCP server configuration from JSON file.

        Returns:
            Dictionary with server names as keys and configs as values.
            Format matches langchain-mcp-adapters MultiServerMCPClient.
        """
        if not self.settings.agent_enable_mcp:
            logger.debug("MCP disabled via config")
            return {}

        # Load full config from file
        all_servers: dict[str, Any] = {}

        if self.settings.agent_mcp_config_path:
            custom_path = Path(self.settings.agent_mcp_config_path)
            if custom_path.exists():
                all_servers = self._parse_mcp_config(custom_path)
            else:
                logger.warning(f"MCP config not found at {custom_path}")
        else:
            for config_path in MCP_CONFIG_PATHS:
                if config_path.exists():
                    logger.debug(f"Loading MCP config from {config_path}")
                    all_servers = self._parse_mcp_config(config_path)
                    break

        # Filter servers based on agent_mcp_servers setting
        enabled_setting = self.settings.agent_mcp_servers.strip()

        if enabled_setting == "*":
            # All servers enabled
            logger.info(f"MCP enabled with all servers: {list(all_servers.keys())}")
            return all_servers

        # Filter to only enabled servers
        enabled_list = [s.strip() for s in enabled_setting.split(",") if s.strip()]
        filtered_servers = {
            name: config
            for name, config in all_servers.items()
            if name in enabled_list
        }

        logger.info(f"MCP enabled with servers: {list(filtered_servers.keys())}")
        return filtered_servers

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
        """Recursively expand ${VAR} and {owner}/{repo} patterns in config values.

        Args:
            obj: Config object (dict, list, or string).

        Returns:
            Object with variables expanded.
        """
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            result = obj

            # Expand ${VAR} patterns (environment variables and settings)
            pattern = r"\$\{([^}]+)\}"

            def replace_var(match: re.Match[str]) -> str:
                var_name = match.group(1)
                if var_name in os.environ:
                    return os.environ[var_name]
                return self._get_setting_value(var_name)

            result = re.sub(pattern, replace_var, result)

            # Expand {owner}/{repo} pattern for GitMCP URLs
            if "{owner}/{repo}" in result and self._current_repo:
                result = result.replace("{owner}/{repo}", self._current_repo)

            return result
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
            "GITHUB_PERSONAL_ACCESS_TOKEN": lambda: self.settings.github_token.get_secret_value(),
            "JIRA_API_TOKEN": lambda: self.settings.jira_api_token.get_secret_value(),
            "JIRA_USER_EMAIL": lambda: self.settings.jira_user_email,
            "JIRA_BASE_URL": lambda: self.settings.jira_base_url,
            "JIRA_DOMAIN": lambda: self.settings.jira_domain_resolved,
            "ATLASSIAN_AUTH_BASE64": lambda: self.settings.atlassian_auth_base64,
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
        prompt = load_prompt(
            "generate-prd",
            raw_requirements=raw_requirements,
            context=context or "None provided",
        )

        logger.info("Generating PRD using Deep Agents with skill")
        result = await self.run_task(
            task="generate-prd",
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
        prompt = load_prompt(
            "generate-spec",
            prd_content=prd_content,
            context=context or "None provided",
        )

        logger.info("Generating Spec using Deep Agents with skill")
        result = await self.run_task(
            task="generate-spec",
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

        prompt = load_prompt(
            "decompose-epics",
            spec_content=spec_content,
            feature_summary=context.get("feature_summary", "Not provided") if context else "Not provided",
            project_key=context.get("project_key", "Not provided") if context else "Not provided",
            repo_instruction=repo_instruction,
        )

        logger.info("Generating Epics using Deep Agents with skill")
        result = await self.run_task(
            task="decompose-epics",
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

        prompt = load_prompt(
            "regenerate",
            content_type=content_type.upper(),
            original_content=original_content,
            feedback=feedback,
        )

        logger.info(f"Regenerating {content_type} with feedback using Deep Agents")
        result = await self.run_task(
            task=skill_name,
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
