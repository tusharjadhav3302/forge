---
name: generate-prd
description: Generate a structured Product Requirements Document (PRD) from raw requirements. Use when asked to create a PRD, product spec, requirements document, or feature definition.
---

# PRD Generation Skill

Generate a Product Requirements Document using the template and guidelines below.

## Instructions

1. Read the template from `plugins/forge-sdlc/templates/prd-template.md`
2. **Fetch attachments**: Check whether the feature ticket has any attachments (e.g. mockups, research docs, specs, diagrams). Use `mcp__atlassian__jira_download_attachments` or equivalent Jira tools to retrieve them. For each attachment, attempt to read or fetch its content and incorporate it as additional context. If an attachment cannot be read (e.g. unsupported binary format), note its filename and skip it.
3. Analyze the raw requirements provided, combined with any content extracted from attachments
4. Fill in all sections of the template
5. Ensure every requirement is testable and specific
6. Validate against the quality checklist

## Generation Rules

1. **Be Specific**: Avoid vague language. Every requirement must be testable.
2. **Prioritize**: Use MVP (must-have), non-MVP (should-have), nice-to-have.
3. **User-Centric**: Frame everything from the user's perspective.
4. **Measurable**: Include specific metrics and acceptance criteria.
5. **Complete**: Fill all sections. Mark unknowns as "TBD - [clarification needed]".
6. **No Implementation**: Focus on WHAT, not HOW. No technical solutions.
7. **Honest Constraints**: Only list constraints that are definitively known to apply. Do not invent or speculate about constraints that may not hold — an uncertain constraint is an assumption, not a constraint.

## Markdown Formatting

Output must be valid markdown. For tables:
- Every row must start AND end with `|`
- All rows must have the same number of columns
- Include separator row after header: `|---|---|---|`

Example:
```markdown
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-001 | Description | MVP |
```

## Quality Checklist

Before returning the PRD, verify:

- [ ] Executive summary is concise (2-3 sentences)
- [ ] Problem statement clearly articulates the pain point
- [ ] At least 1 user persona defined with goals and pain points
- [ ] All functional requirements have acceptance criteria
- [ ] Success metrics are quantifiable with specific targets
- [ ] Scope boundaries clearly defined (in/out of scope)
- [ ] Risks have mitigation strategies
- [ ] No technical implementation details included

## Output Format

Follow the structure in `plugins/forge-sdlc/templates/prd-template.md` exactly.

IMPORTANT: Return ONLY the PRD content. Do not include any planning text, explanations of what you're doing, or meta-commentary. Start directly with the PRD title.
