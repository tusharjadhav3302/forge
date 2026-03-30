"""Specification generation node for LangGraph workflow."""

import logging
from typing import Any

from forge.config import get_settings
from forge.integrations.claude.agent import ClaudeAgentClient
from forge.integrations.jira.client import JiraClient
from forge.models.workflow import ForgeLabel
from forge.orchestrator.state import WorkflowState, update_state_timestamp

logger = logging.getLogger(__name__)


async def generate_spec(state: WorkflowState) -> WorkflowState:
    """Generate a behavioral specification from the approved PRD.

    This node:
    1. Reads the PRD content from state (or fetches from Jira)
    2. Generates a specification with Given/When/Then acceptance criteria
    3. Stores spec in Jira custom field
    4. Transitions ticket to "Pending Spec Approval"

    Args:
        state: Current workflow state with prd_content.

    Returns:
        Updated state with spec_content populated.
    """
    ticket_key = state["ticket_key"]
    prd_content = state.get("prd_content", "")

    logger.info(f"Generating specification for {ticket_key}")

    jira = JiraClient()
    claude = ClaudeAgentClient()

    try:
        # If PRD not in state, fetch from Jira
        if not prd_content:
            issue = await jira.get_issue(ticket_key)
            prd_content = issue.description or ""

        if not prd_content.strip():
            logger.warning(f"No PRD content found for {ticket_key}")
            return {
                **state,
                "last_error": "No PRD content available for spec generation",
                "current_node": "generate_spec",
            }

        # Build context
        context: dict[str, Any] = {
            "ticket_key": ticket_key,
        }

        # Generate specification using Claude
        spec_content = await claude.generate_spec(prd_content, context)

        # Store spec in Jira (comment or custom field based on config)
        settings = get_settings()
        if settings.jira_store_in_comments:
            await jira.add_structured_comment(
                ticket_key,
                "Technical Specification",
                spec_content,
                comment_type="spec",
            )
        elif settings.jira_spec_custom_field:
            await jira.update_custom_field(
                ticket_key,
                settings.jira_spec_custom_field,
                spec_content,
            )

        # Set workflow label (instead of custom status transition)
        await jira.set_workflow_label(ticket_key, ForgeLabel.SPEC_PENDING)

        logger.info(f"Spec generated for {ticket_key} ({len(spec_content)} chars)")

        return update_state_timestamp({
            **state,
            "spec_content": spec_content,
            "current_node": "spec_approval_gate",
            "last_error": None,
        })

    except Exception as e:
        logger.error(f"Spec generation failed for {ticket_key}: {e}")
        return {
            **state,
            "last_error": str(e),
            "current_node": "generate_spec",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await jira.close()
        await claude.close()


async def regenerate_spec_with_feedback(state: WorkflowState) -> WorkflowState:
    """Regenerate specification incorporating user feedback.

    Args:
        state: Current workflow state with feedback_comment set.

    Returns:
        Updated state with new spec_content.
    """
    ticket_key = state["ticket_key"]
    feedback = state.get("feedback_comment", "")
    original_spec = state.get("spec_content", "")

    if not feedback:
        logger.warning(f"No feedback provided for spec regeneration on {ticket_key}")
        return state

    logger.info(f"Regenerating spec for {ticket_key} with feedback")

    jira = JiraClient()
    claude = ClaudeAgentClient()

    try:
        # Regenerate spec with feedback
        new_spec = await claude.regenerate_with_feedback(
            original_content=original_spec,
            feedback=feedback,
            content_type="spec",
        )

        # Store updated spec in Jira (comment or custom field based on config)
        settings = get_settings()
        if settings.jira_store_in_comments:
            await jira.add_structured_comment(
                ticket_key,
                "Technical Specification (Revised)",
                new_spec,
                comment_type="spec",
            )
        elif settings.jira_spec_custom_field:
            await jira.update_custom_field(
                ticket_key,
                settings.jira_spec_custom_field,
                new_spec,
            )

        # Add comment acknowledging revision
        await jira.add_comment(
            ticket_key,
            "Specification has been revised based on feedback. Please review the updated version.",
        )

        logger.info(f"Spec regenerated for {ticket_key} ({len(new_spec)} chars)")

        return update_state_timestamp({
            **state,
            "spec_content": new_spec,
            "feedback_comment": None,
            "revision_requested": False,
            "current_node": "spec_approval_gate",
            "last_error": None,
        })

    except Exception as e:
        logger.error(f"Spec regeneration failed for {ticket_key}: {e}")
        return {
            **state,
            "last_error": str(e),
            "current_node": "regenerate_spec",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await jira.close()
        await claude.close()
