"""Epic decomposition node for LangGraph workflow."""

import logging
from typing import Any

from forge.integrations.claude.client import ClaudeClient
from forge.integrations.jira.client import JiraClient
from forge.models.workflow import FeatureStatus
from forge.orchestrator.state import WorkflowState, update_state_timestamp

logger = logging.getLogger(__name__)


async def decompose_epics(state: WorkflowState) -> WorkflowState:
    """Decompose specification into logical Epics with implementation plans.

    This node:
    1. Reads the approved specification from state
    2. Generates 2-5 cohesive Epics using Claude
    3. Creates Epic tickets in Jira linked to parent Feature
    4. Transitions Feature to "Pending Plan Approval"

    Args:
        state: Current workflow state with spec_content.

    Returns:
        Updated state with epic_keys populated.
    """
    ticket_key = state["ticket_key"]
    spec_content = state.get("spec_content", "")

    logger.info(f"Decomposing spec into Epics for {ticket_key}")

    jira = JiraClient()
    claude = ClaudeClient()

    try:
        # If spec not in state, this is an error
        if not spec_content.strip():
            logger.error(f"No spec content found for {ticket_key}")
            return {
                **state,
                "last_error": "No spec content available for Epic decomposition",
                "current_node": "decompose_epics",
            }

        # Get parent issue for project key
        parent_issue = await jira.get_issue(ticket_key)
        project_key = parent_issue.project_key

        # Build context for Epic generation
        context: dict[str, Any] = {
            "ticket_key": ticket_key,
            "project_key": project_key,
            "feature_summary": parent_issue.summary,
        }

        # Generate Epic breakdown using Claude
        epics_data = await claude.generate_epics(spec_content, context)

        if not epics_data:
            logger.warning(f"No Epics generated for {ticket_key}")
            return {
                **state,
                "last_error": "Epic generation returned no results",
                "current_node": "decompose_epics",
            }

        # Create Epics in Jira
        epic_keys: list[str] = []
        for epic in epics_data:
            summary = epic.get("summary", "Untitled Epic")
            plan = epic.get("plan", "")

            epic_key = await jira.create_epic(
                project_key=project_key,
                summary=summary,
                description=plan,
                parent_key=ticket_key,
            )
            epic_keys.append(epic_key)
            logger.info(f"Created Epic {epic_key}: {summary}")

        # Transition Feature to pending plan approval
        status = FeatureStatus.PENDING_PLAN_APPROVAL.value
        await jira.transition_issue(ticket_key, status)

        logger.info(f"Created {len(epic_keys)} Epics for {ticket_key}")

        return update_state_timestamp({
            **state,
            "epic_keys": epic_keys,
            "current_node": "plan_approval_gate",
            "last_error": None,
        })

    except Exception as e:
        logger.error(f"Epic decomposition failed for {ticket_key}: {e}")
        return {
            **state,
            "last_error": str(e),
            "current_node": "decompose_epics",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await jira.close()
        await claude.close()


async def regenerate_all_epics(state: WorkflowState) -> WorkflowState:
    """Delete all Epics and regenerate from spec with feedback.

    This handles Feature-level rejection where the entire Epic
    breakdown needs to be revised.

    Args:
        state: Current workflow state with feedback_comment set.

    Returns:
        Updated state with new epic_keys.
    """
    ticket_key = state["ticket_key"]
    feedback = state.get("feedback_comment", "")
    existing_epics = state.get("epic_keys", [])

    logger.info(f"Regenerating all Epics for {ticket_key} with feedback")

    jira = JiraClient()

    try:
        # Delete existing Epics
        for epic_key in existing_epics:
            try:
                await jira.delete_issue(epic_key, delete_subtasks=True)
                logger.info(f"Deleted Epic {epic_key}")
            except Exception as e:
                logger.warning(f"Failed to delete Epic {epic_key}: {e}")

        # Clear epic_keys and set feedback for decomposition
        updated_state = {
            **state,
            "epic_keys": [],
            "feedback_comment": feedback,
        }

        # Re-run decomposition (which will use context including feedback)
        return await decompose_epics(updated_state)

    except Exception as e:
        logger.error(f"Epic regeneration failed for {ticket_key}: {e}")
        return {
            **state,
            "last_error": str(e),
            "current_node": "regenerate_all_epics",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await jira.close()


async def update_single_epic(state: WorkflowState) -> WorkflowState:
    """Update a single Epic's implementation plan based on feedback.

    This handles Epic-level feedback where only one Epic needs revision.

    Args:
        state: Workflow state with current_epic_key and feedback_comment.

    Returns:
        Updated state.
    """
    ticket_key = state["ticket_key"]
    epic_key = state.get("current_epic_key")
    feedback = state.get("feedback_comment", "")

    if not epic_key:
        logger.warning(
            f"No current_epic_key for single Epic update on {ticket_key}"
        )
        return state

    logger.info(f"Updating Epic {epic_key} with feedback")

    jira = JiraClient()
    claude = ClaudeClient()

    try:
        # Get current Epic description
        epic_issue = await jira.get_issue(epic_key)
        original_plan = epic_issue.description or ""

        # Regenerate plan with feedback
        new_plan = await claude.regenerate_with_feedback(
            original_content=original_plan,
            feedback=feedback,
            content_type="epic",
        )

        # Update Epic description
        await jira.update_description(epic_key, new_plan)

        # Add comment to Epic acknowledging revision
        await jira.add_comment(
            epic_key,
            "Implementation plan has been revised based on feedback.",
        )

        logger.info(f"Updated Epic {epic_key} plan")

        return update_state_timestamp({
            **state,
            "current_epic_key": None,
            "feedback_comment": None,
            "revision_requested": False,
            "current_node": "plan_approval_gate",
            "last_error": None,
        })

    except Exception as e:
        logger.error(f"Epic update failed for {epic_key}: {e}")
        return {
            **state,
            "last_error": str(e),
            "current_node": "update_single_epic",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await jira.close()
        await claude.close()


def check_all_epics_approved(
    state: WorkflowState, epic_statuses: dict[str, str]
) -> bool:
    """Check if all Epics have been approved.

    Args:
        state: Current workflow state.
        epic_statuses: Dict mapping Epic key to current status.

    Returns:
        True if all Epics are approved.
    """
    epic_keys = state.get("epic_keys", [])
    if not epic_keys:
        return False

    approved_status = "approved"  # Adjust based on actual Jira workflow

    for epic_key in epic_keys:
        status = epic_statuses.get(epic_key, "").lower()
        if approved_status not in status:
            return False

    return True
