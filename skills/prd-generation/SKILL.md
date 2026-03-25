---
name: prd-generation
description: Use when converting raw feature ideas into formal Product Requirements Documents, refining vague product concepts, or responding to feedback on existing PRDs. Defines what to build and why, ensuring business value and strategic alignment.
---

# PRD Generation Skill

## Purpose

Generate comprehensive, high-quality Product Requirements Documents (PRDs) that define **what** to build and **why**, serving as the single source of truth for product, engineering, design, and stakeholder alignment.

## When to Use

Use this skill when:
- Converting raw feature ideas into formal PRDs
- Refining vague product concepts into concrete requirements
- Responding to PM feedback on existing PRDs
- Validating that a feature has clear business value and strategic alignment

## Core Principles

### 1. Focus on "What," Not "How"
PRDs outline **what** the product should do from the user's perspective, not **how** to build it. Avoid implementation details to allow designers and engineers to use their expertise.

### 2. Single Source of Truth
The PRD ensures product, engineering, design, and go-to-market teams have **shared understanding** of what is being built and why. It serves as a compass once stakeholders are aligned.

### 3. Testable and Specific
Use concrete, testable statements. Prefer specific thresholds ("p95 response time < 500ms") over vague adjectives ("fast"). Avoid ambiguous language like "user-friendly" or "intuitive" without definition.

### 4. Business Value First
If you cannot articulate clear **business value** and **success metrics**, the feature should not be built. Every PRD must answer: "Why does this matter to users and the business?"

### 5. Living Document
PRDs are not static. They evolve with the product. Treat them as living documents that are continuously updated based on learning and feedback.

## PRD Template Structure

```markdown
# [Feature Name] - Product Requirements Document

## Document Information

**Author**: [Name]
**Status**: Draft | Under Review | Approved | In Development
**Created**: [Date]
**Last Updated**: [Date]
**Stakeholders**: [PM, Tech Lead, Design Lead, etc.]

---

## 1. Overview

### Problem Statement
[What pain are we solving? For whom? Why now?]

**Current Situation**:
[What's broken or missing today?]

**Desired Outcome**:
[What does success look like?]

### Strategic Alignment
[How does this fit into overall company objectives? Which strategic initiative does this support?]

### Target Audience
[Who is this for?]

**Primary Personas**:
- **[Persona 1]**: [Brief description, key needs]
- **[Persona 2]**: [Brief description, key needs]

**Secondary Personas**:
- [If applicable]

---

## 2. Objectives and Goals

### Business Goals
[Why are we building this from a business perspective?]

- [Goal 1]: [Description]
- [Goal 2]: [Description]
- [Goal 3]: [Description]

### User Goals
[What do users want to accomplish?]

- [User Goal 1]: [Description]
- [User Goal 2]: [Description]

### Success Metrics (KPIs)

**Primary Metrics**:
- [Metric 1]: [Target value] - [How measured]
- [Metric 2]: [Target value] - [How measured]

**Secondary Metrics**:
- [Metric 3]: [Target value] - [How measured]

**Release Criteria** (Must achieve before launch):
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

---

## 3. User Stories and Use Cases

### High-Level User Stories

**Story 1**: [Title]
- **As a** [user role]
- **I want** [capability]
- **So that** [business value]

**Story 2**: [Title]
- **As a** [user role]
- **I want** [capability]
- **So that** [business value]

[Continue for 3-7 high-level stories]

### Use Cases

**Use Case 1**: [Scenario Name]
- **Actor**: [Who]
- **Trigger**: [What starts this]
- **Flow**: [Step-by-step user journey]
- **Success Outcome**: [What happens when successful]
- **Failure Outcome**: [What happens if it fails]

[Add 2-5 key use cases]

---

## 4. Requirements

### Functional Requirements

**FR-1**: [Requirement Name]
- **Description**: [What the system must do]
- **Priority**: Must-Have | Want-to-Have | Nice-to-Have
- **User Story Reference**: [Link to user story]
- **Acceptance Criteria**: [How we know it's complete]

**FR-2**: [Requirement Name]
[Repeat pattern]

[List 5-15 functional requirements]

### Non-Functional Requirements

**Performance**:
- [Requirement]: [Specific threshold, e.g., "Response time < 500ms p95"]
- [Requirement]: [Specific threshold]

**Reliability**:
- [Requirement]: [Specific threshold, e.g., "99.9% uptime"]
- [Requirement]: [Specific threshold]

**Usability**:
- [Requirement]: [Specific threshold or guideline]

**Security**:
- [Requirement]: [Specific security control]
- [Requirement]: [Specific security control]

**Compatibility**:
- [Requirement]: [Platforms, browsers, devices supported]

**Maintainability**:
- [Requirement]: [Code quality, documentation standards]

**Scalability**:
- [Requirement]: [Load capacity, growth expectations]

---

## 5. Scope

### In Scope (This Release)

**Must-Haves** (P0):
- [Feature/capability 1]
- [Feature/capability 2]

**Want-to-Haves** (P1):
- [Feature/capability 3]
- [Feature/capability 4]

**Nice-to-Haves** (P2):
- [Feature/capability 5]

### Out of Scope (Future Releases)
- [Explicitly excluded feature 1] - [Why excluded, when might it be included]
- [Explicitly excluded feature 2] - [Why excluded, when might it be included]

---

## 6. User Experience and Design

### Wireframes/Mockups
[Links to design files or embedded wireframes]

### User Flow
[Describe the end-to-end user journey]

1. [Step 1]: [What user sees/does]
2. [Step 2]: [What user sees/does]
3. [Step 3]: [What user sees/does]

### Key Screens/Components
- **[Screen 1]**: [Purpose, key elements]
- **[Screen 2]**: [Purpose, key elements]

---

## 7. Technical Context

### Affected Systems/Repositories
- [System/Repo 1]: [What changes are needed]
- [System/Repo 2]: [What changes are needed]

### Dependencies
- **Internal Dependencies**:
  - [Dependency 1]: [Why needed, who owns it]
  - [Dependency 2]: [Why needed, who owns it]

- **External Dependencies**:
  - [External service/API]: [Why needed]

### Constraints
- **Technical Constraints**: [Limitations from existing architecture]
- **Business Constraints**: [Budget, timeline, resource limitations]
- **Regulatory Constraints**: [Compliance requirements, legal constraints]

---

## 8. Assumptions and Open Questions

### Assumptions
- [Assumption 1]: [What we're assuming is true]
- [Assumption 2]: [What we're assuming is true]

### Open Questions
- [ ] [Question 1]: [What we need to decide/clarify]
- [ ] [Question 2]: [What we need to decide/clarify]

---

## 9. Risks and Mitigations

### Risk 1: [Risk Name]
- **Impact**: High | Medium | Low
- **Likelihood**: High | Medium | Low
- **Mitigation**: [How to prevent or reduce risk]

### Risk 2: [Risk Name]
[Repeat pattern for top 3-5 risks]

---

## 10. Timeline and Milestones

### Key Dates
- **PRD Approval**: [Target date]
- **Design Complete**: [Target date]
- **Development Start**: [Target date]
- **Alpha/Beta**: [Target date]
- **Launch**: [Target date]

### Milestones
- **Milestone 1**: [Description] - [Date]
- **Milestone 2**: [Description] - [Date]
- **Milestone 3**: [Description] - [Date]

---

## 11. Appendix

### References
- [Market research]
- [Customer interviews]
- [Related documents]
- [System documentation]
- [Related tickets]

### Glossary
- **[Term 1]**: [Definition]
- **[Term 2]**: [Definition]

### Revision History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | [Date] | [Name] | Initial draft |
| 1.1 | [Date] | [Name] | [What changed] |
```

## Generation Process

### Step 1: Understand the Raw Input

**Read the feature request**:
- What problem are they trying to solve?
- Who is it for?
- Why does it matter?
- What constraints or context did they mention?

**Identify gaps**:
- What's missing from the raw input?
- What questions need answering?
- What assumptions need validating?

### Step 2: Research Context

**Search system documentation**:
- What existing systems are relevant?
- What capabilities already exist?
- What patterns should we follow?

**Review technical constraints**:
- What technical guardrails apply?
- What constraints must we respect?

**Review related work**:
- Have we done something similar before?
- What lessons can we learn?
- Are there dependencies or conflicts?

**Customer/User Research**:
- What do we know about user needs?
- What pain points have been reported?
- What usage patterns exist?

### Step 3: Synthesize the Problem

**Write the Problem Statement**:
- Be specific about the pain
- Identify the user(s) affected
- Explain why this matters now

**Define Strategic Alignment**:
- Which company/product goals does this support?
- Why is this a priority?

**Identify Target Audience**:
- Primary personas (who will use this most)
- Secondary personas (who else benefits)

### Step 4: Define Objectives and Success

**Business Goals**:
- What does the business get from this?
- How does this move key metrics?

**User Goals**:
- What do users want to accomplish?
- How does this make their lives better?

**Success Metrics**:
- What KPIs will we track?
- What are the target values?
- How will we measure them?
- What must be true before we launch?

### Step 5: Create User Stories and Use Cases

**High-Level User Stories** (3-7 stories):
- As a [role], I want [capability], so that [value]
- Focus on the "why" and "what", not "how"
- Prioritize by user impact

**Key Use Cases** (2-5 scenarios):
- Walk through the user journey
- Include happy path and error cases
- Describe triggers and outcomes

### Step 6: Define Requirements

**Functional Requirements** (5-15 items):
- What must the system do?
- Use testable statements
- Prioritize: Must-have, Want-to-have, Nice-to-have
- Link to user stories

**Non-Functional Requirements**:
- Use ISO/IEC 25010 quality attributes checklist
- Be specific with thresholds (not "fast", but "< 500ms p95")
- Cover: Performance, Reliability, Usability, Security, Compatibility, Maintainability, Scalability

### Step 7: Define Scope Boundaries

**In Scope**:
- Must-haves for this release (P0)
- Want-to-haves if time permits (P1)
- Nice-to-haves if resources available (P2)

**Out of Scope**:
- Explicitly list what's NOT included
- Explain why it's excluded
- Mention when it might be included (future release)

### Step 8: Document Risks and Assumptions

**Assumptions**:
- What are we assuming is true?
- What happens if assumptions are wrong?

**Risks**:
- Top 3-5 risks (technical, business, user adoption)
- Impact and likelihood
- Mitigation strategies

**Open Questions**:
- What do we still need to decide?
- Who needs to answer these questions?

### Step 9: Quality Check

Run through the **Quality Checklist** (see below) before finalizing.

## Quality Checklist

Before finalizing a PRD, verify:

- [ ] **Clear problem statement**: Specific pain, affected users, why now
- [ ] **Strategic alignment**: Explicitly linked to company/product goals
- [ ] **Business value articulated**: Clear why this matters to business
- [ ] **User value articulated**: Clear why this matters to users
- [ ] **Success metrics defined**: Specific, measurable KPIs with target values
- [ ] **What, not how**: Focuses on requirements, not implementation
- [ ] **Testable requirements**: All requirements are verifiable
- [ ] **No vague language**: No "user-friendly", "intuitive", "appropriate" without definition
- [ ] **Prioritization clear**: Must-haves vs want-to-haves vs nice-to-haves
- [ ] **Scope boundaries**: In-scope and out-of-scope explicitly stated
- [ ] **Non-functional requirements**: Performance, security, reliability, etc. included
- [ ] **User stories present**: 3-7 high-level user stories with business value
- [ ] **Risks identified**: Top risks with impact, likelihood, mitigation
- [ ] **Assumptions documented**: What we're assuming is true
- [ ] **Context researched**: System documentation and related work reviewed
- [ ] **Stakeholders identified**: Who needs to approve, who will implement
- [ ] **No hallucinations**: Only references real systems from documentation
- [ ] **Consistent terminology**: Uses domain language from existing docs

## Common Pitfalls to Avoid

1. **Over-specifying (Too Much "How")**
   - ❌ "Use PostgreSQL with connection pooling via pg_bouncer"
   - ✅ "Store user data persistently with < 100ms read latency"

2. **Under-specifying (Too Vague)**
   - ❌ "The system should be user-friendly"
   - ✅ "90% of users complete onboarding in < 5 minutes without support"

3. **Missing Business Value**
   - ❌ "Build a dashboard"
   - ✅ "Build a dashboard so PMs can track feature adoption (current manual process takes 2 hours/week)"

4. **No Success Metrics**
   - ❌ "Users should like it"
   - ✅ "NPS > 40, 80% weekly active user retention"

5. **Ignoring Non-Functional Requirements**
   - ❌ Only lists functional features
   - ✅ Includes performance, security, reliability, usability requirements

6. **Hallucinated References**
   - ❌ "Integrate with user-profile-service" (doesn't exist)
   - ✅ Validate against system documentation before mentioning any component

7. **No Prioritization**
   - ❌ Flat list of 20 features
   - ✅ Must-haves (5), Want-to-haves (3), Out-of-scope (rest)

## Handling Feedback

When stakeholders request PRD changes:

1. **Read all feedback** - Review all comments and change requests
2. **Identify specific gaps** - What's missing? What needs clarification?
3. **Preserve good parts** - Don't regenerate everything, update specific sections
4. **Incorporate feedback** - Address each point explicitly
5. **Re-validate** - Run through quality checklist again

### Example Feedback Loop

**Feedback**: "Add GDPR compliance section - we're handling EU user data"

**Response**:
1. Update **Non-Functional Requirements → Security** section:
   - Add: "GDPR Compliance: All EU user data encrypted at rest and in transit, 30-day data retention policy"
2. Update **Risks** section:
   - Add Risk: "GDPR Violation" with mitigation steps
3. Update **Technical Context → Constraints**:
   - Add: "Regulatory Constraints: GDPR compliance required for EU users"
4. Update **Requirements**:
   - Add FR-6: "Data privacy controls for EU users (right to deletion, data export)"

## References

- How to Write Product Requirements: https://www.parallelhq.com/blog/how-to-write-product-requirements
- Product School PRD Template: https://productschool.com/blog/product-strategy/product-template-requirements-document-prd
- Atlassian PRD Guide: https://www.atlassian.com/agile/product-management/requirements
- How to Write a PRD - Perforce: https://www.perforce.com/blog/alm/how-write-product-requirements-document-prd
- Effective PRD Writing: https://www.jamasoftware.com/requirements-management-guide/writing-requirements/how-to-write-an-effective-product-requirements-document/
