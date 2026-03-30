"""PRD generation node for LangGraph workflow."""

import logging
from typing import Any

from forge.config import get_settings
from forge.integrations.claude.agent import ClaudeAgentClient
from forge.integrations.jira.client import JiraClient
from forge.models.workflow import ForgeLabel
from forge.orchestrator.state import WorkflowState, update_state_timestamp

logger = logging.getLogger(__name__)


async def generate_prd(state: WorkflowState) -> WorkflowState:
    """Generate a PRD from raw requirements in Jira description.

    This node:
    1. Reads the current Jira issue description
    2. Generates a structured PRD using Claude
    3. Updates the Jira description with the PRD
    4. Transitions the ticket to "Pending PRD Approval"

    Args:
        state: Current workflow state.

    Returns:
        Updated state with prd_content populated.
    """
    ticket_key = state["ticket_key"]
    logger.info(f"Generating PRD for {ticket_key}")

    jira = JiraClient()
    claude = ClaudeAgentClient()

    try:
        # Fetch current issue to get raw requirements
        issue = await jira.get_issue(ticket_key)
        raw_requirements = issue.description or ""

        if not raw_requirements.strip():
            logger.warning(f"No description found for {ticket_key}")
            return {
                **state,
                "last_error": "No requirements found in issue description",
                "current_node": "generate_prd",
            }

        # Build context from issue metadata
        context: dict[str, Any] = {
            "ticket_key": ticket_key,
            "summary": issue.summary,
            "project_key": issue.project_key,
        }

        # Generate PRD using Claude
        prd_content = await claude.generate_prd(raw_requirements, context)

        # Update Jira with generated PRD
        settings = get_settings()
        if settings.jira_store_in_comments:
            # Store PRD in a structured comment
            await jira.add_structured_comment(
                ticket_key,
                "Product Requirements Document (PRD)",
                prd_content,
                comment_type="prd",
            )
        else:
            # Update description directly
            await jira.update_description(ticket_key, prd_content)

        # Set workflow label (instead of custom status transition)
        await jira.set_workflow_label(ticket_key, ForgeLabel.PRD_PENDING)

        logger.info(
            f"PRD generated for {ticket_key} ({len(prd_content)} chars)"
        )

        return update_state_timestamp({
            **state,
            "prd_content": prd_content,
            "current_node": "prd_approval_gate",
            "last_error": None,
        })

    except Exception as e:
        logger.error(f"PRD generation failed for {ticket_key}: {e}")
        return {
            **state,
            "last_error": str(e),
            "current_node": "generate_prd",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await jira.close()
        await claude.close()


async def regenerate_prd_with_feedback(state: WorkflowState) -> WorkflowState:
    """Regenerate PRD incorporating user feedback.

    This node handles the case where a PM rejects the PRD and provides
    feedback via a Jira comment. It regenerates the PRD addressing
    the feedback and updates Jira.

    Args:
        state: Current workflow state with feedback_comment set.

    Returns:
        Updated state with new prd_content.
    """
    ticket_key = state["ticket_key"]
    feedback = state.get("feedback_comment", "")
    original_prd = state.get("prd_content", "")

    if not feedback:
        logger.warning(
            f"No feedback provided for PRD regeneration on {ticket_key}"
        )
        return state

    logger.info(f"Regenerating PRD for {ticket_key} with feedback")

    jira = JiraClient()
    claude = ClaudeAgentClient()

    try:
        # Regenerate PRD with feedback
        new_prd = await claude.regenerate_with_feedback(
            original_content=original_prd,
            feedback=feedback,
            content_type="prd",
        )

        # Update Jira with regenerated PRD
        await jira.update_description(ticket_key, new_prd)

        # Add comment acknowledging the revision
        await jira.add_comment(
            ticket_key,
            "PRD has been revised based on feedback. Please review.",
        )

        logger.info(f"PRD regenerated for {ticket_key} ({len(new_prd)} chars)")

        return update_state_timestamp({
            **state,
            "prd_content": new_prd,
            "feedback_comment": None,
            "revision_requested": False,
            "current_node": "prd_approval_gate",
            "last_error": None,
        })

    except Exception as e:
        logger.error(f"PRD regeneration failed for {ticket_key}: {e}")
        return {
            **state,
            "last_error": str(e),
            "current_node": "regenerate_prd",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await jira.close()
        await claude.close()
