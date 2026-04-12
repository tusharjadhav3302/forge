Please break down the following Epic into implementation Tasks:

EPIC: {epic_summary}

IMPLEMENTATION PLAN:
{epic_plan}

Generate 3-8 concrete Tasks that can be completed in 2-8 hours each.

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
