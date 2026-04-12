Please decompose the following specification into 2-5 logical Epics with implementation plans:

{spec_content}

Additional context:
- Feature: {feature_summary}
- Project: {project_key}
{repo_instruction}

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

Separate each Epic with `---` on its own line. Include 2-5 Epics total.
