"""Task generation node for LangGraph workflow."""

import logging
import re
from typing import Any

from forge.config import Settings, get_settings
from forge.integrations.claude.client import get_anthropic_client
from forge.integrations.jira.client import JiraClient
from forge.integrations.langfuse import trace_llm_call
from forge.models.workflow import FeatureStatus
from forge.orchestrator.state import WorkflowState, update_state_timestamp

logger = logging.getLogger(__name__)

# System prompt for Task generation
TASK_SYSTEM_PROMPT = """You are an expert Software Engineer skilled at breaking down
Epic implementation plans into concrete, actionable Tasks.

When given an Epic with its implementation plan, you will:
1. Identify discrete, testable units of work (2-8 hours each)
2. Define clear acceptance criteria for each Task
3. Identify which repository each Task belongs to (from context)
4. Order Tasks by dependency (foundation first)

Output format for each Task:
---
TASK: [Task Title]
REPO: [repository-name or "unknown"]
DESCRIPTION:
[Detailed implementation steps]

ACCEPTANCE_CRITERIA:
- [Criterion 1]
- [Criterion 2]
---
(repeat for each Task)
"""


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
    anthropic = get_anthropic_client(settings)

    all_task_keys: list[str] = []
    tasks_by_repo: dict[str, list[str]] = {}

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

            # Build context
            context: dict[str, Any] = {
                "epic_key": epic_key,
                "epic_summary": epic_summary,
                "feature_key": ticket_key,
                "project_key": project_key,
            }

            # Generate Tasks using Claude
            tasks_data = await _generate_tasks_for_epic(
                anthropic, epic_plan, epic_summary, context
            )

            # Create Tasks in Jira
            for task in tasks_data:
                summary = task.get("summary", "Untitled Task")
                description = task.get("description", "")
                repo = task.get("repo", "unknown")

                # Add repository as label
                labels = [f"repo:{repo}"] if repo != "unknown" else []

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

        # Transition Feature to Executing
        await jira.transition_issue(ticket_key, FeatureStatus.EXECUTING.value)

        logger.info(f"Created {len(all_task_keys)} Tasks for {ticket_key}")

        return update_state_timestamp({
            **state,
            "task_keys": all_task_keys,
            "tasks_by_repo": tasks_by_repo,
            "current_node": "task_router",
            "last_error": None,
        })

    except Exception as e:
        logger.error(f"Task generation failed for {ticket_key}: {e}")
        return {
            **state,
            "last_error": str(e),
            "current_node": "generate_tasks",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    finally:
        await jira.close()


async def _generate_tasks_for_epic(
    client: AsyncAnthropic,
    epic_plan: str,
    epic_summary: str,
    context: dict[str, Any],
) -> list[dict[str, str]]:
    """Generate Tasks for a single Epic.

    Args:
        client: Anthropic client.
        epic_plan: Epic implementation plan.
        epic_summary: Epic title/summary.
        context: Additional context.

    Returns:
        List of Task dicts with summary, description, repo.
    """
    user_prompt = f"""Please break down the following Epic into implementation Tasks:

EPIC: {epic_summary}

IMPLEMENTATION PLAN:
{epic_plan}

CONTEXT:
{context}

Generate 3-8 concrete Tasks that can be completed in 2-8 hours each.
Include repository assignment when possible (look for mentions of specific repos,
services, or components in the plan)."""

    with trace_llm_call(
        "generate_tasks",
        {"epic_summary": epic_summary, "context": context},
    ) as trace:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=TASK_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        result = response.content[0].text
        trace["output"] = result[:500]

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
