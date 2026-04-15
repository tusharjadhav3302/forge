Please decompose the following specification into logical Epics with implementation plans:

{spec_content}

Additional context:
- Feature: {feature_summary}
- Project: {project_key}
{repo_instruction}

## Scope Guidelines

Choose the number of Epics based on feature complexity:
- **Simple features** (single config field, one endpoint, isolated change): 1 Epic
- **Medium features** (2-3 related components, moderate integration): 2-3 Epics  
- **Large features** (multiple subsystems, extensive integration): 3-5 Epics

Fewer Epics is better. Only split when work is genuinely independent and parallelizable.
Avoid artificial separation like "Config Epic" + "Validation Epic" + "Tests Epic" - 
these belong together in one cohesive Epic.

## Output Format

You MUST use this exact format for each Epic. The parser depends on these exact prefixes:

```
EPIC: [Concise epic title - max 100 chars]
REPO: [owner/repo from the available repositories]
PLAN:
[Detailed implementation plan with:]
- Technical approach and architecture decisions
- Key components/files to create or modify
- Dependencies and integration points
- Testing strategy
- Estimated complexity (S/M/L)
---
```

Separate each Epic with `---` on its own line.
