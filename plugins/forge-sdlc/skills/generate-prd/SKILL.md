---
name: generate-prd
description: Generate a structured Product Requirements Document (PRD) from raw requirements. Use when asked to create a PRD, product spec, requirements document, or feature definition.
---

# PRD Generation Skill

Generate a Product Requirements Document using the template and guidelines below.

## Instructions

1. Read the template from `plugins/forge-sdlc/templates/prd-template.md`
2. Analyze the raw requirements provided
3. Fill in all sections of the template
4. Ensure every requirement is testable and specific
5. Validate against the quality checklist

## Generation Rules

1. **Be Specific**: Avoid vague language. Every requirement must be testable.
2. **Prioritize**: Use P1 (must-have), P2 (should-have), P3 (nice-to-have).
3. **User-Centric**: Frame everything from the user's perspective.
4. **Measurable**: Include specific metrics and acceptance criteria.
5. **Complete**: Fill all sections. Mark unknowns as "TBD - [clarification needed]".
6. **No Implementation**: Focus on WHAT, not HOW. No technical solutions.

## Markdown Formatting

Output must be valid markdown. For tables:
- Every row must start AND end with `|`
- All rows must have the same number of columns
- Include separator row after header: `|---|---|---|`

Example:
```markdown
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-001 | Description | P1 |
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
