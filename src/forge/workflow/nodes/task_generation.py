"""Task generation node for LangGraph workflow."""

import logging
import re
from typing import Any

from forge.config import get_settings
from forge.integrations.agents import ForgeAgent
from forge.integrations.jira.client import JiraClient
from forge.models.workflow import ForgeLabel
from forge.prompts import load_prompt
from forge.workflow.feature.state import FeatureState as WorkflowState
from forge.workflow.utils import update_state_timestamp

logger = logging.getLogger(__name__)


async def generate_tasks(state: WorkflowState) -> WorkflowState:
    """Generate implementation Tasks for each approved Epic.

    This node:
    1. Iterates through all Epics in epic_keys
    2. Generates Tasks for each Epic using Claude
    3. Creates Task tickets in Jira with repository labels
    4. Updates state with task tracking

    Args:
        state: Current workflow state with epic_keys.

    Returns:
        Updated state with task_keys and tasks_by_repo populated.
    """
    ticket_key = state["ticket_key"]
    epic_keys = state.get("epic_keys", [])

    if not epic_keys:
        logger.warning(f"No Epics found for task generation on {ticket_key}")
        return {
            **state,
            "last_error": "No Epics available for task generation",
            "current_node": "generate_tasks",
        }

    logger.info(f"Generating Tasks for {len(epic_keys)} Epics on {ticket_key}")

    settings = get_settings()
    jira = JiraClient(settings)
    agent = ForgeAgent(settings)

    all_task_keys: list[str] = []
    tasks_by_repo: dict[str, list[str]] = {}
    jira_error = None

    try:
        # Get project key from parent Feature
        parent_issue = await jira.get_issue(ticket_key)
        project_key = parent_issue.project_key

        for epic_key in epic_keys:
            logger.info(f"Generating Tasks for Epic {epic_key}")

            # Get Epic details
            epic_issue = await jira.get_issue(epic_key)
            epic_plan = epic_issue.description or ""
            epic_summary = epic_issue.summary

            if not epic_plan.strip():
                logger.warning(f"Epic {epic_key} has no implementation plan")
                continue

            # Get repo from Epic labels (set during decomposition)
            epic_labels = await jira.get_labels(epic_key)
            epic_repo = ""
            for label in epic_labels:
                if label.startswith("repo:"):
                    epic_repo = label[5:]
                    break

            # Build context
            context: dict[str, Any] = {
                "epic_key": epic_key,
                "epic_summary": epic_summary,
                "feature_key": ticket_key,
                "project_key": project_key,
                "epic_repo": epic_repo,
            }

            # Generate Tasks using Deep Agents - primary operation
            tasks_data = await _generate_tasks_for_epic(
                agent, epic_plan, epic_summary, context
            )

            # Create Tasks in Jira - secondary operation
            for task in tasks_data:
                summary = task.get("summary", "Untitled Task")
                description = task.get("description", "")
                repo = task.get("repo", "")

                # Repo priority: task-level > epic-level > default config
                if not repo or repo == "unknown" or "/" not in repo:
                    repo = epic_repo  # Inherit from Epic

                if not repo or repo == "unknown" or "/" not in repo:
                    repo = settings.github_default_repo  # Fallback to config

                if not repo or "/" not in repo:
                    logger.warning(
                        f"Task '{summary}' has no valid repo. "
                        "Set repo labels on Feature/Epic or GITHUB_DEFAULT_REPO."
                    )
                    repo = "unknown"

                # Add labels: forge:managed for webhook routing, forge:parent for lookup, repo
                labels = [
                    ForgeLabel.FORGE_MANAGED.value,
                    f"forge:parent:{ticket_key}",  # Parent Feature key
                ]
                if repo and repo != "unknown":
                    labels.append(f"repo:{repo}")

                try:
                    task_key = await jira.create_task(
                        project_key=project_key,
                        summary=summary,
                        description=description,
                        parent_key=epic_key,
                        labels=labels,
                    )

                    all_task_keys.append(task_key)

                    # Track by repository
                    if repo not in tasks_by_repo:
                        tasks_by_repo[repo] = []
                    tasks_by_repo[repo].append(task_key)

                    logger.info(f"Created Task {task_key}: {summary} (repo: {repo})")
                except Exception as e:
                    # Log but continue creating remaining Tasks
                    jira_error = str(e)
                    logger.warning(
                        f"Failed to create Task '{summary}' for {ticket_key}: {e}"
                    )

        logger.info(
            f"Created {len(all_task_keys)} Tasks for {ticket_key}, "
            "awaiting implementation approval"
        )

        # If we created some Tasks, advance even with partial failures
        if all_task_keys:
            # Only set workflow label after confirming tasks were created
            try:
                await jira.set_workflow_label(ticket_key, ForgeLabel.TASK_PENDING)
            except Exception as e:
                jira_error = str(e)
                logger.warning(f"Failed to set workflow label for {ticket_key}: {e}")
            return update_state_timestamp({
                **state,
                "task_keys": all_task_keys,
                "tasks_by_repo": tasks_by_repo,
                "current_node": "task_approval_gate",
                "last_error": f"Partial Jira failure: {jira_error}" if jira_error else None,
            })
        else:
            # No Tasks created at all - this is a failure
            return {
                **state,
                "last_error": jira_error or "Failed to create any Tasks in Jira",
                "current_node": "generate_tasks",
                "retry_count": state.get("retry_count", 0) + 1,
            }

    except Exception as e:
        logger.error(f"Task generation failed for {ticket_key}: {e}")
        from forge.workflow.nodes.error_handler import notify_error
        await notify_error(state, str(e), "generate_tasks")
        # Save any Tasks we managed to create
        result_state = {
            **state,
            "last_error": str(e),
            "current_node": "generate_tasks",
            "retry_count": state.get("retry_count", 0) + 1,
        }
        if all_task_keys:
            result_state["task_keys"] = all_task_keys
            result_state["tasks_by_repo"] = tasks_by_repo
        return result_state
    finally:
        await jira.close()


async def _generate_tasks_for_epic(
    agent: ForgeAgent,
    epic_plan: str,
    epic_summary: str,
    context: dict[str, Any],
) -> list[dict[str, str]]:
    """Generate Tasks for a single Epic.

    Args:
        agent: Deep Agent client.
        epic_plan: Epic implementation plan.
        epic_summary: Epic title/summary.
        context: Additional context.

    Returns:
        List of Task dicts with summary, description, repo.
    """
    prompt = load_prompt(
        "generate-tasks",
        epic_summary=epic_summary,
        epic_plan=epic_plan,
    )

    result = await agent.run_task(
        task="generate-tasks",
        prompt=prompt,
        context=context,
    )

    return _parse_tasks_response(result)


def _parse_tasks_response(response: str) -> list[dict[str, str]]:
    """Parse Task generation response into structured data.

    Args:
        response: Raw response from Claude.

    Returns:
        List of Task dicts.
    """
    tasks = []
    current_task: dict[str, str] = {}
    current_section = None
    section_lines: list[str] = []

    for line in response.split("\n"):
        stripped = line.strip()

        if stripped.startswith("---"):
            # Save previous task if exists
            if current_task.get("summary"):
                if current_section == "description":
                    current_task["description"] = "\n".join(section_lines).strip()
                elif current_section == "acceptance_criteria":
                    # Append acceptance criteria to description
                    criteria = "\n".join(section_lines).strip()
                    current_task["description"] = (
                        current_task.get("description", "") +
                        "\n\nAcceptance Criteria:\n" + criteria
                    ).strip()
                tasks.append(current_task)
                current_task = {}
                section_lines = []
            continue

        if stripped.startswith("TASK:"):
            current_task["summary"] = stripped[5:].strip()
            current_section = "summary"
        elif stripped.startswith("REPO:"):
            repo = stripped[5:].strip().lower()
            # Clean up repo name
            repo = re.sub(r'[^a-z0-9\-_]', '', repo)
            current_task["repo"] = repo if repo else "unknown"
        elif stripped.startswith("DESCRIPTION:"):
            current_section = "description"
            section_lines = []
        elif stripped.startswith("ACCEPTANCE_CRITERIA:"):
            # Save description first
            if current_section == "description":
                current_task["description"] = "\n".join(section_lines).strip()
            current_section = "acceptance_criteria"
            section_lines = []
        elif current_section in ("description", "acceptance_criteria"):
            section_lines.append(line)

    # Don't forget the last task
    if current_task.get("summary"):
        if current_section == "description":
            current_task["description"] = "\n".join(section_lines).strip()
        elif current_section == "acceptance_criteria":
            criteria = "\n".join(section_lines).strip()
            current_task["description"] = (
                current_task.get("description", "") +
                "\n\nAcceptance Criteria:\n" + criteria
            ).strip()
        tasks.append(current_task)

    return tasks


def extract_repo_from_labels(labels: list[str]) -> str:
    """Extract repository name from Jira labels.

    Args:
        labels: List of Jira labels.

    Returns:
        Repository name or "unknown".
    """
    for label in labels:
        if label.startswith("repo:"):
            return label[5:]
    return "unknown"


async def regenerate_all_tasks(state: WorkflowState) -> WorkflowState:
    """Delete all Tasks and regenerate from Epics with feedback.

    This handles Feature-level rejection where the entire Task
    breakdown needs to be revised.

    Args:
        state: Current workflow state with feedback_comment set.

    Returns:
        Updated state with new task_keys.
    """
    ticket_key = state["ticket_key"]
    feedback = state.get("feedback_comment", "")
    existing_tasks = state.get("task_keys", [])

    logger.info(f"Regenerating all Tasks for {ticket_key} with feedback")

    jira = JiraClient()

    try:
        # Archive existing Tasks (unlink from parent, mark as archived)
        for task_key in existing_tasks:
            try:
                await jira.archive_issue(task_key, archive_subtasks=False)
                logger.info(f"Archived Task {task_key}")
            except Exception as e:
                logger.warning(f"Failed to archive Task {task_key}: {e}")

        # Clear task_keys and set feedback for regeneration
        updated_state = {
            **state,
            "task_keys": [],
            "tasks_by_repo": {},
            "feedback_comment": feedback,
        }

        # Re-run task generation (which will incorporate feedback in context)
        return await generate_tasks(updated_state)

    except Exception as e:
        logger.error(f"Task regeneration failed for {ticket_key}: {e}")
        from forge.workflow.nodes.error_handler import notify_error
        await notify_error(state, str(e), "regenerate_all_tasks")
        return {
            **state,
            "last_error": str(e),
            "current_node": "regenerate_all_tasks",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await jira.close()


async def update_single_task(state: WorkflowState) -> WorkflowState:
    """Update a single Task's description based on feedback.

    This handles Task-level feedback where only one Task needs revision.

    Args:
        state: Workflow state with current_task_key and feedback_comment.

    Returns:
        Updated state.
    """
    ticket_key = state["ticket_key"]
    task_key = state.get("current_task_key")
    feedback = state.get("feedback_comment", "")

    if not task_key:
        logger.warning(
            f"No current_task_key for single Task update on {ticket_key}"
        )
        return state

    logger.info(f"Updating Task {task_key} with feedback")

    jira = JiraClient()
    agent = ForgeAgent()

    try:
        # Get current Task description
        task_issue = await jira.get_issue(task_key)
        original_description = task_issue.description or ""

        # Regenerate description with feedback
        new_description = await agent.regenerate_with_feedback(
            original_content=original_description,
            feedback=feedback,
            content_type="task",
        )

        # Update Task in Jira
        await jira.update_description(task_key, new_description)

        # Add comment acknowledging revision
        await jira.add_comment(
            task_key,
            "Task has been revised based on feedback. Please review.",
        )

        logger.info(f"Task {task_key} updated with feedback")

        return update_state_timestamp({
            **state,
            "current_task_key": None,
            "feedback_comment": None,
            "revision_requested": False,
            "current_node": "task_approval_gate",
            "last_error": None,
        })

    except Exception as e:
        logger.error(f"Task update failed for {task_key}: {e}")
        from forge.workflow.nodes.error_handler import notify_error
        await notify_error(state, str(e), "update_single_task")
        return {
            **state,
            "last_error": str(e),
            "current_node": "update_single_task",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await jira.close()
        await agent.close()
