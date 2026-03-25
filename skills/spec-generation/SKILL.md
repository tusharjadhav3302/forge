---
name: spec-generation
description: Use when converting Epic requirements into User Story specifications, refining vague requirements into concrete acceptance criteria, or responding to feedback on existing specs. Ensures BDD-style Given/When/Then scenarios that are user-centric, testable, and demonstrate business value.
---

# Spec Generation Skill

## Purpose

Generate high-quality, BDD-style specifications with Given/When/Then acceptance criteria for user stories. This skill ensures specifications are user-centric, testable, and focused on observable behavior.

## When to Use

Use this skill when:
- Converting Epic requirements into User Story specifications
- Refining vague requirements into concrete acceptance criteria
- Responding to feedback on existing specs
- Validating that a story has clear business value

## Core Principles

### 1. Write Scenarios Before Code
Specifications define what to build, not how to build it. Complete specs before implementation begins.

### 2. One Scenario = One Behavior
Each Given/When/Then scenario tests a single behavior. Avoid compound conditions or multiple outcomes in one scenario.

### 3. Business Value Focus
**Critical Rule**: If you cannot write a meaningful Given/When/Then scenario demonstrating business value, the story should not be built.

### 4. Observable Outcomes Only
Focus on what the user sees/experiences, not implementation details. "Then the user receives an email" not "Then the SendEmailService is called".

## Given-When-Then Structure

### Given (Context/Preconditions)
- **Purpose**: Establish the state of the system before the action
- **Format**: `Given [context/precondition]`
- **Examples**:
  - `Given the user is logged in`
  - `Given a Feature ticket in "Drafting PRD" status`
  - `Given the shopping cart contains 3 items`
- **Best Practices**:
  - Use present tense
  - Describe state, not actions
  - Include only relevant context (avoid noise)

### When (Action/Trigger)
- **Purpose**: Describe the action that triggers the behavior
- **Format**: `When [action occurs]`
- **Examples**:
  - `When the user clicks "Submit"`
  - `When the webhook fires with ticket_id`
  - `When the user enters an invalid email`
- **Best Practices**:
  - Use active voice
  - Single action per When clause
  - Focus on user/system action, not internal processes

### Then (Observable Outcome)
- **Purpose**: State the expected, observable result
- **Format**: `Then [observable outcome]`
- **Examples**:
  - `Then the user sees a success message`
  - `Then the Jira ticket transitions to "Pending Approval"`
  - `Then an error message "Invalid email format" is displayed`
- **Best Practices**:
  - Clear, explicit terms
  - Observable by user or test
  - Avoid implementation details
  - Measurable/verifiable

## Specification Template

```markdown
## User Story

**As a** [role]
**I want** [capability]
**So that** [business value]

## Acceptance Criteria

### Scenario: [Descriptive scenario name]

**Given** [context/precondition]
**When** [action]
**Then** [observable outcome]

### Scenario: [Another scenario name]

**Given** [different context]
**When** [action]
**Then** [different outcome]

[Continue for 3-7 scenarios covering main flow, edge cases, error cases]

## Edge Cases

- [List edge cases to consider]
- [Boundary conditions]
- [Error scenarios]

## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Edge cases handled
- [ ] Error messages are user-friendly
- [ ] [Domain-specific criteria]
```

## Generation Process

### Step 1: Understand Context
- Read the Epic/Feature description
- Review related tickets for context
- Identify the user role(s)
- Clarify business value

### Step 2: Identify Behaviors
- List 3-7 distinct behaviors to test
- Include:
  - Main happy path (1-2 scenarios)
  - Alternative paths (1-2 scenarios)
  - Edge cases (1-2 scenarios)
  - Error conditions (1-2 scenarios)

### Step 3: Write Scenarios
For each behavior:
1. Name the scenario descriptively
2. Write Given (context)
3. Write When (action)
4. Write Then (outcome)
5. Validate: Is this observable? Testable? Valuable?

### Step 4: Add Edge Cases
List additional considerations:
- Boundary conditions (empty lists, max values)
- Concurrency scenarios
- Timeout/failure conditions
- Permission/authorization edge cases

### Step 5: Define Done Criteria
What must be true for this story to be complete?
- Functional criteria (all scenarios pass)
- Non-functional criteria (performance, security)
- Documentation/logging requirements

## Quality Checklist

Before finalizing a spec, verify:

- [ ] **User-centric**: Written from user perspective, not technical implementation
- [ ] **Observable**: All "Then" clauses describe something observable
- [ ] **Single behavior**: Each scenario tests one behavior
- [ ] **Business value**: Clear why this matters to users/business
- [ ] **Testable**: Each scenario can be automated or manually tested
- [ ] **Complete**: Covers happy path, alternatives, errors, edge cases
- [ ] **Unambiguous**: No vague terms like "appropriate", "correct", "properly"
- [ ] **Consistent**: Uses same terminology as domain/project

## Examples

### Good Spec Example

```markdown
## User Story

**As a** Product Manager
**I want** to approve or reject the PRD with comments
**So that** the AI can refine it based on my feedback

## Acceptance Criteria

### Scenario: PM approves PRD

**Given** PRD in "Pending PRD Approval" status
**When** PM transitions ticket to "In Analysis"
**Then** the system proceeds to the next workflow step

### Scenario: PM rejects PRD with feedback

**Given** PRD in "Pending PRD Approval" status
**When** PM adds comment "Add GDPR compliance section" and transitions to "Drafting PRD"
**Then** webhook sends ticket_id to queue
**Then** worker fetches latest ticket state with comment
**Then** AI regenerates PRD incorporating GDPR section

### Scenario: PM rejects without comment

**Given** PRD in "Pending PRD Approval" status
**When** PM transitions to "Drafting PRD" without adding comment
**Then** AI regenerates PRD with generic improvements

## Edge Cases

- Multiple rapid comments before status transition
- Very long comments (>10,000 characters)
- Comments with special characters or code blocks

## Definition of Done

- [ ] All three scenarios pass
- [ ] Comment text preserved in regenerated PRD
- [ ] Handles rapid edits (race conditions)
- [ ] Logs all feedback incorporation
```

### Bad Spec Example (Anti-Pattern)

```markdown
## Acceptance Criteria

**Given** the system is working
**When** the user does something
**Then** the system behaves correctly

[Problems: Vague, not observable, no business value, not testable]
```

## Handling Feedback

When PM/Tech Lead requests spec changes:

1. **Read all comments** - Fetch current ticket state from Jira
2. **Identify gaps** - What scenarios are missing? Which need refinement?
3. **Preserve good parts** - Don't regenerate everything, improve specific scenarios
4. **Incorporate feedback** - Add new scenarios or modify existing ones
5. **Validate** - Run through quality checklist again

### Example Feedback Loop

**Feedback**: "Add pagination edge case"

**Response**: Add new scenario:
```markdown
### Scenario: Large result set requires pagination

**Given** there are 1000+ stories in the Epic
**When** user views the story list
**Then** stories are paginated with 50 per page
**Then** pagination controls are displayed
```

## Common Pitfalls to Avoid

1. **Implementation details in Then clauses**
   - ❌ "Then the database is updated"
   - ✅ "Then the user sees their profile changes saved"

2. **Compound scenarios**
   - ❌ "Given user is logged in and has admin role and feature flag enabled"
   - ✅ Split into separate scenarios

3. **Vague outcomes**
   - ❌ "Then the system works properly"
   - ✅ "Then the user receives confirmation email within 5 seconds"

4. **Too many Givens/Whens/Thens**
   - ❌ 5+ Then clauses in one scenario
   - ✅ Multiple focused scenarios instead

5. **Testing implementation, not behavior**
   - ❌ "Then the cache is invalidated"
   - ✅ "Then the updated data is displayed on next page load"

## References

- Cucumber BDD Documentation: https://cucumber.io/docs/bdd/
- Given-When-Then Best Practices: https://www.parallelhq.com/blog/given-when-then-acceptance-criteria
- BDD Guide for 2026: https://monday.com/blog/rnd/behavior-driven-development/
