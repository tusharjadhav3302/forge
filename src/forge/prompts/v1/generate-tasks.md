Please break down the following Epic into implementation Tasks:

EPIC: {epic_summary}

IMPLEMENTATION PLAN:
{epic_plan}

{existing_tasks_section}

Generate 3-8 concrete Tasks that can be completed in 2-8 hours each.

## Avoiding Duplication

If existing tasks are listed above:
- Do NOT create tasks that duplicate work already assigned to other Epics
- Cross-cutting concerns (e.g., "add tests", "update docs") should only appear once across all Epics
- If this Epic needs integration with work from another Epic, reference it rather than recreating it

## Output Format

You MUST use this exact format for each Task. The parser depends on these exact prefixes:

```
TASK: [Concise task title - max 100 chars]
REPO: [owner/repo - inherit from Epic if not specified]
DESCRIPTION:
[What needs to be implemented, including:]
- Specific files to create/modify
- Functions/classes to implement
- Integration points
ACCEPTANCE_CRITERIA:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests pass
---
```

Separate each Task with `---` on its own line. Include 3-8 Tasks total.
