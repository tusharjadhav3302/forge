"""Claude Agent SDK client for AI-powered SDLC orchestration.

Uses the Claude Agent SDK to provide agentic capabilities including
tool use, file operations, and MCP server access.
"""

import logging
import os
from datetime import datetime
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    query,
)

from forge.config import Settings, get_settings

logger = logging.getLogger(__name__)


# System prompts for different generation tasks
PRD_SYSTEM_PROMPT = """You are an expert Product Manager skilled at creating clear,
structured Product Requirements Documents (PRDs).

Today's date is {current_date}.

When given raw requirements or ideas, you will:
1. Identify the core business goals and user value
2. Define clear user personas and their needs
3. Articulate strategic value and success metrics
4. Structure the content into a professional PRD format

Output format:
- Use clear headings and sections
- Include: Overview, Goals, User Personas, Requirements, Success Metrics
- Be specific and measurable where possible
- Avoid technical implementation details
"""

SPEC_SYSTEM_PROMPT = """You are an expert Business Analyst skilled at creating
behavioral specifications with precise acceptance criteria.

Today's date is {current_date}.

When given a PRD, you will:
1. Extract user scenarios and prioritize them (P1, P2, P3)
2. Define Given/When/Then acceptance criteria for each scenario
3. List functional requirements that are testable
4. Define measurable success criteria
5. Identify edge cases and error scenarios

Output format:
- Prioritized user scenarios with acceptance criteria
- Functional requirements (FR-001, FR-002, etc.)
- Success criteria with specific metrics
- Assumptions and constraints
"""

EPIC_SYSTEM_PROMPT = """You are an expert Technical Architect skilled at decomposing
features into logical work units (Epics) with implementation plans.

Today's date is {current_date}.

When given a specification, you will:
1. Identify 2-5 cohesive capability areas (Epics)
2. For each Epic, create a detailed implementation plan including:
   - Architecture overview
   - Technical approach
   - Key components and their responsibilities
   - Dependencies and risks
   - Estimated complexity

Output format for each Epic:
- Epic Title (capability name)
- Overview paragraph
- Technical approach
- Key components list
- Dependencies
- Risks and mitigations
"""


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
    ) -> ClaudeAgentOptions:
        """Configure agent options with tools and MCP servers.

        Args:
            system_prompt: System prompt for the agent.
            include_tools: Whether to include file/bash tools.
            include_mcp: Whether to include MCP servers.

        Returns:
            Configured ClaudeAgentOptions.
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        formatted_prompt = system_prompt.format(current_date=current_date)

        allowed_tools = []
        mcp_servers = {}

        if include_tools:
            allowed_tools.extend(["Read", "Glob", "Grep", "WebSearch"])

        if include_mcp:
            # Add GitHub MCP if configured
            github_token = self.settings.github_token.get_secret_value()
            if github_token and github_token != "your-github-personal-access-token":
                mcp_servers["github"] = {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_TOKEN": github_token},
                }
                allowed_tools.append("mcp__github__*")

        return ClaudeAgentOptions(
            system_prompt=formatted_prompt,
            allowed_tools=allowed_tools if allowed_tools else None,
            mcp_servers=mcp_servers if mcp_servers else None,
            permission_mode="bypassPermissions",  # For automated workflows
            model=self.settings.claude_model,
        )

    async def _run_agent(
        self,
        prompt: str,
        system_prompt: str,
        include_tools: bool = True,
        include_mcp: bool = False,
    ) -> str:
        """Run the agent with the given prompt.

        Args:
            prompt: User prompt to send.
            system_prompt: System prompt template.
            include_tools: Whether to include tools.
            include_mcp: Whether to include MCP servers.

        Returns:
            Agent response text.
        """
        options = self._get_agent_options(
            system_prompt=system_prompt,
            include_tools=include_tools,
            include_mcp=include_mcp,
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

        Args:
            raw_requirements: Raw requirements text from Jira description.
            context: Optional additional context (e.g., project info).

        Returns:
            Generated PRD content.
        """
        prompt = f"""Please create a Product Requirements Document from the following
raw requirements:

{raw_requirements}

Additional context:
{context or 'None provided'}

Generate a comprehensive, well-structured PRD."""

        logger.info("Generating PRD using Claude Agent SDK")
        result = await self._run_agent(
            prompt=prompt,
            system_prompt=PRD_SYSTEM_PROMPT,
            include_tools=True,
            include_mcp=False,
        )

        logger.info(f"Generated PRD ({len(result)} chars)")
        return result

    async def generate_spec(
        self,
        prd_content: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Generate a behavioral specification from a PRD.

        Args:
            prd_content: Approved PRD content.
            context: Optional additional context.

        Returns:
            Generated specification content.
        """
        prompt = f"""Please create a detailed behavioral specification from the
following Product Requirements Document:

{prd_content}

Additional context:
{context or 'None provided'}

Generate a comprehensive specification with prioritized user scenarios,
Given/When/Then acceptance criteria, and functional requirements."""

        logger.info("Generating Spec using Claude Agent SDK")
        result = await self._run_agent(
            prompt=prompt,
            system_prompt=SPEC_SYSTEM_PROMPT,
            include_tools=True,
            include_mcp=False,
        )

        logger.info(f"Generated specification ({len(result)} chars)")
        return result

    async def generate_epics(
        self,
        spec_content: str,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        """Generate Epic breakdown from a specification.

        Args:
            spec_content: Approved specification content.
            context: Optional additional context (e.g., repo structure).

        Returns:
            List of dicts with 'summary' and 'plan' for each Epic.
        """
        prompt = f"""Please decompose the following specification into 2-5
logical Epics with implementation plans:

{spec_content}

Additional context:
{context or 'None provided'}

For each Epic, provide:
1. A clear summary/title (one line)
2. A detailed implementation plan

Format your response as:
---
EPIC: [Epic Title]
PLAN:
[Detailed implementation plan]
---
(repeat for each Epic)"""

        logger.info("Generating Epics using Claude Agent SDK")
        result = await self._run_agent(
            prompt=prompt,
            system_prompt=EPIC_SYSTEM_PROMPT,
            include_tools=True,
            include_mcp=True,  # Can access GitHub for repo context
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
        system_prompts = {
            "prd": PRD_SYSTEM_PROMPT,
            "spec": SPEC_SYSTEM_PROMPT,
            "epic": EPIC_SYSTEM_PROMPT,
        }
        system = system_prompts.get(content_type, PRD_SYSTEM_PROMPT)

        prompt = f"""Please revise the following {content_type.upper()} based on
the feedback provided:

ORIGINAL CONTENT:
{original_content}

FEEDBACK:
{feedback}

Please regenerate the content addressing all feedback points while maintaining
the overall structure and quality."""

        logger.info(f"Regenerating {content_type} with feedback using Claude Agent SDK")
        result = await self._run_agent(
            prompt=prompt,
            system_prompt=system,
            include_tools=True,
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
