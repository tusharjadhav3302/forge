---
name: generate-spec
description: Generate a Technical Specification with behavioral acceptance criteria from a PRD. Use when asked to create a spec, technical specification, or detailed requirements.
---

# Specification Generation Skill

Generate a Technical Specification using the template and guidelines below.

## Instructions

1. Read the template from `plugins/forge-sdlc/templates/spec-template.md`
2. Analyze the PRD content provided
3. Extract user scenarios and prioritize them
4. Define Given/When/Then acceptance criteria
5. Document all functional requirements
6. Validate against the quality checklist

## Generation Rules

1. **Gherkin Format**: All acceptance criteria must use Given/When/Then.
2. **Testable**: Every requirement must be verifiable through testing.
3. **Complete Scenarios**: Include happy path, error cases, and edge cases.
4. **Trace to PRD**: Reference FR/US IDs from the parent PRD.
5. **No Ambiguity**: Use precise language. Avoid "should", "might", "could".
6. **Security First**: Include authentication/authorization for all endpoints.

## Priority Definitions

- **P1 (Critical)**: Must work for MVP - blocks release if not complete
- **P2 (Important)**: Required for full release - can ship MVP without
- **P3 (Enhancement)**: Nice to have - can be deferred to future release

## Markdown Formatting

Output must be valid markdown. For tables:
- Every row must start AND end with `|`
- All rows must have the same number of columns
- Include separator row after header: `|---|---|---|`

Example:
```markdown
| Scenario | Priority | Status |
|----------|----------|--------|
| Happy path | P1 | Required |
```

## Quality Checklist

Before returning the specification:

- [ ] All P1 scenarios have complete Gherkin acceptance criteria
- [ ] Every scenario includes error handling
- [ ] API contracts include request/response schemas
- [ ] State transitions are fully documented
- [ ] Performance targets are quantified
- [ ] Test scenarios cover all acceptance criteria
- [ ] Open questions documented with owners

## Output Format

Follow the structure in `plugins/forge-sdlc/templates/spec-template.md` exactly.

IMPORTANT: Return ONLY the specification content. Do not include any planning text, explanations of what you're doing, or meta-commentary. Start directly with the specification title.
