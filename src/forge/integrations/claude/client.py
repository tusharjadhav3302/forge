"""Claude Code SDK wrapper for AI-powered content generation."""

import logging
from typing import Any, Optional

from anthropic import AsyncAnthropic

from forge.config import Settings, get_settings
from forge.integrations.langfuse import trace_llm_call

logger = logging.getLogger(__name__)

# Default model for generation tasks
DEFAULT_MODEL = "claude-sonnet-4-20250514"

# System prompts for different generation tasks
PRD_SYSTEM_PROMPT = """You are an expert Product Manager skilled at creating clear,
structured Product Requirements Documents (PRDs).

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


class ClaudeClient:
    """Async client for Claude API interactions.

    Provides high-level methods for PRD, Spec, and Epic generation
    with built-in Langfuse tracing.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the Claude client.

        Args:
            settings: Application settings. Uses default if not provided.
        """
        self.settings = settings or get_settings()
        self._client: Optional[AsyncAnthropic] = None

    async def _get_client(self) -> AsyncAnthropic:
        """Get or create the Anthropic client."""
        if self._client is None:
            self._client = AsyncAnthropic(
                api_key=self.settings.anthropic_api_key.get_secret_value()
            )
        return self._client

    async def generate_prd(
        self,
        raw_requirements: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """Generate a structured PRD from raw requirements.

        Args:
            raw_requirements: Raw requirements text from Jira description.
            context: Optional additional context (e.g., project info).

        Returns:
            Generated PRD content.
        """
        client = await self._get_client()

        user_prompt = f"""Please create a Product Requirements Document from the following
raw requirements:

{raw_requirements}

Additional context:
{context or 'None provided'}

Generate a comprehensive, well-structured PRD."""

        with trace_llm_call(
            "generate_prd",
            {"raw_requirements": raw_requirements[:500], "context": context},
        ) as trace:
            response = await client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=4096,
                system=PRD_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            result = response.content[0].text
            trace["output"] = result[:500]

        logger.info(f"Generated PRD ({len(result)} chars)")
        return result

    async def generate_spec(
        self,
        prd_content: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """Generate a behavioral specification from a PRD.

        Args:
            prd_content: Approved PRD content.
            context: Optional additional context.

        Returns:
            Generated specification content.
        """
        client = await self._get_client()

        user_prompt = f"""Please create a detailed behavioral specification from the
following Product Requirements Document:

{prd_content}

Additional context:
{context or 'None provided'}

Generate a comprehensive specification with prioritized user scenarios,
Given/When/Then acceptance criteria, and functional requirements."""

        with trace_llm_call(
            "generate_spec",
            {"prd_content": prd_content[:500], "context": context},
        ) as trace:
            response = await client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=8192,
                system=SPEC_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            result = response.content[0].text
            trace["output"] = result[:500]

        logger.info(f"Generated specification ({len(result)} chars)")
        return result

    async def generate_epics(
        self,
        spec_content: str,
        context: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, str]]:
        """Generate Epic breakdown from a specification.

        Args:
            spec_content: Approved specification content.
            context: Optional additional context (e.g., repo structure).

        Returns:
            List of dicts with 'summary' and 'plan' for each Epic.
        """
        client = await self._get_client()

        user_prompt = f"""Please decompose the following specification into 2-5
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

        with trace_llm_call(
            "generate_epics",
            {"spec_content": spec_content[:500], "context": context},
        ) as trace:
            response = await client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=8192,
                system=EPIC_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            result = response.content[0].text
            trace["output"] = result[:500]

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
        client = await self._get_client()

        system_prompts = {
            "prd": PRD_SYSTEM_PROMPT,
            "spec": SPEC_SYSTEM_PROMPT,
            "epic": EPIC_SYSTEM_PROMPT,
        }
        system = system_prompts.get(content_type, PRD_SYSTEM_PROMPT)

        user_prompt = f"""Please revise the following {content_type.upper()} based on
the feedback provided:

ORIGINAL CONTENT:
{original_content}

FEEDBACK:
{feedback}

Please regenerate the content addressing all feedback points while maintaining
the overall structure and quality."""

        with trace_llm_call(
            f"regenerate_{content_type}",
            {"feedback": feedback[:500], "content_type": content_type},
        ) as trace:
            response = await client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=8192,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            result = response.content[0].text
            trace["output"] = result[:500]

        logger.info(f"Regenerated {content_type} with feedback ({len(result)} chars)")
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
        """Close the client (no-op for Anthropic client)."""
        self._client = None
