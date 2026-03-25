---
name: epic-generation
description: Use when converting an approved PRD into Epic-level work breakdown, decomposing Feature tickets into 2-5 logical groupings, or responding to feedback on Epic structure. Ensures clear boundaries, single purpose per Epic, and enables parallel work.
---

# Epic Generation Skill

## Purpose

Generate well-scoped, logically grouped Epics that decompose Feature-level requirements into manageable work units while maintaining clear business value and technical coherence.

## When to Use

Use this skill when:
- Converting an approved PRD into Epic-level work breakdown
- Decomposing Feature tickets into 2-5 logical groupings
- Responding to feedback on Epic structure or scope
- Validating that Epics have clear boundaries and single purpose

## Core Principles

### 1. Epics Represent Coherent Work Units

An Epic groups related User Stories around a single theme or capability. Good Epics have:
- **Clear scope**: You can describe what's in/out in one sentence
- **Single theme**: All Stories relate to the same capability or area
- **Deliverable value**: The Epic represents a meaningful increment
- **Right-sized**: 3-7 User Stories per Epic (not too small, not too large)

### 2. Logical Decomposition, Not Arbitrary Splitting

Epics should emerge from natural boundaries in the work:
- **By capability**: "User Authentication", "Dashboard UI", "Reporting Engine"
- **By system layer**: "API Layer", "Data Pipeline", "Frontend Components"
- **By user journey**: "Onboarding Flow", "Core Workflow", "Admin Functions"
- **NOT by**: arbitrary splitting ("Part 1", "Part 2"), implementation phases, or artificial divisions

### 3. Epics Enable Parallel Work

Well-formed Epics minimize dependencies between them. Teams should be able to work on multiple Epics concurrently without constant coordination.

### 4. Naming Conventions Matter

Epic names should be:
- **Concise**: 3-6 words maximum
- **Descriptive**: Clear what the Epic covers
- **Consistent**: Follow project naming patterns
- **Value-focused**: What capability, not how it's built

Good: "Payment Processing", "User Dashboard", "Notification System"
Bad: "Backend Work", "Implementation Phase 1", "Miscellaneous Tasks"

## Epic Template Structure

```markdown
# Epic: [Capability Name]

## Scope

### What's Included
- [Capability 1 within this Epic]
- [Capability 2 within this Epic]
- [Capability 3 within this Epic]

### What's Excluded (Out of Scope)
- [Related but separate capability]
- [Future enhancement not in this Epic]

## Business Value

[Why this Epic matters to users/business - 2-3 sentences]

## Technical Approach (High-Level)

[Brief overview of how this will be built - key technologies, patterns, integrations]

## Dependencies

- **Depends on**: [Other Epics that must complete first, if any]
- **Blocks**: [Other Epics that wait on this, if any]
- **Integrates with**: [Related systems/components]

## Success Criteria

- [ ] [Measurable outcome 1]
- [ ] [Measurable outcome 2]
- [ ] [Measurable outcome 3]

## Risks

- [Risk 1 and mitigation]
- [Risk 2 and mitigation]
```

## Generation Process

### Step 1: Read and Analyze the PRD

1. **Extract key capabilities** - What distinct capabilities are described?
2. **Identify natural boundaries** - Where do responsibilities clearly separate?
3. **Look for cohesion signals** - What work items naturally cluster together?
4. **Check dependencies** - What must be built before what?

### Step 2: Identify Epic Candidates

List 4-8 potential Epic groupings. For each, ask:
- Does this represent a coherent capability?
- Can it be described in 3-6 words?
- Would it contain 3-7 User Stories?
- Does it have clear boundaries?

### Step 3: Validate and Refine

For each Epic candidate:
1. **Test the name** - Is it clear and descriptive?
2. **Define scope** - Can you list what's in and what's out?
3. **Check size** - Too big (>7 stories) or too small (<3 stories)?
4. **Verify value** - Does completing this Epic deliver something meaningful?
5. **Assess dependencies** - How does it relate to other Epics?

### Step 4: Optimize the Set

Target: **2-5 Epics per Feature**
- **Too many (>5)**: Look for Epics to merge - are any too granular?
- **Too few (<2)**: Look for Epics to split - are any too broad?
- **Dependencies**: Can Epics be reordered to minimize blocking?

### Step 5: Write Epic Descriptions

For each Epic:
1. Write summary (Epic name)
2. Define scope (what's in/out)
3. Articulate business value
4. Outline high-level technical approach
5. List dependencies and integrations
6. Define success criteria
7. Identify risks

### Step 6: Create Epics in Issue Tracking System

For each Epic:
1. Create issue with appropriate type/hierarchy level
2. Link to parent Feature ticket
3. Include complete description with scope and value
4. Record Epic identifier for reference

## Quality Checklist

Before finalizing Epics, verify:

- [ ] **Count**: 2-5 Epics total (not too many, not too few)
- [ ] **Naming**: Each Epic has clear, concise name (3-6 words)
- [ ] **Scope**: Each Epic has explicit in/out boundaries
- [ ] **Value**: Each Epic delivers meaningful business value
- [ ] **Size**: Each Epic will contain 3-7 User Stories
- [ ] **Coherence**: Stories within an Epic relate to single theme
- [ ] **Independence**: Epics minimize cross-dependencies
- [ ] **Parent linking**: All Epics link to Feature
- [ ] **Completeness**: All PRD capabilities covered by some Epic
- [ ] **No overlap**: No capability appears in multiple Epics

## Epic Decomposition Patterns

### Pattern 1: By User-Facing Capability

**Example**: E-commerce Platform Feature

**Epics**:
1. **User Authentication** - Login, registration, password reset, SSO
2. **Product Catalog** - Browse, search, filter, product details
3. **Shopping Cart** - Add items, update quantities, apply coupons
4. **Checkout Process** - Shipping info, payment, order confirmation
5. **Order Management** - View orders, track shipping, returns

**Why Good**: Each Epic is a distinct user-facing capability with clear value

### Pattern 2: By System Layer

**Example**: Real-Time Analytics Platform Feature

**Epics**:
1. **Data Ingestion Layer** - Event collection, validation, buffering
2. **Stream Processing** - Real-time aggregation, transformation, filtering
3. **Storage Layer** - Time-series database, data retention, archival
4. **Query API** - REST endpoints, query optimization, caching
5. **Visualization Dashboard** - Charts, graphs, real-time updates

**Why Good**: Natural technical boundaries enable parallel development

### Pattern 3: By User Journey

**Example**: Employee Onboarding System Feature

**Epics**:
1. **Pre-Arrival Preparation** - Document submission, equipment request, access setup
2. **First Day Experience** - Welcome portal, orientation, initial training
3. **First Week Setup** - Team introductions, workspace config, tool access
4. **Ongoing Integration** - Progress tracking, mentor check-ins, feedback

**Why Good**: Follows natural user timeline, each phase has clear completion

## Common Pitfalls to Avoid

1. **Too Many Epics**
   - ❌ "Let's create 10 Epics for this Feature"
   - ✅ "This Feature naturally breaks into 4 coherent Epics"

2. **Implementation-Focused Splitting**
   - ❌ "Epic 1: Database, Epic 2: API, Epic 3: Frontend"
   - ✅ "Epic 1: User Management, Epic 2: Reporting, Epic 3: Admin Tools"

3. **Vague or Generic Names**
   - ❌ "Backend Work", "Phase 1", "Miscellaneous"
   - ✅ "Payment Processing", "Notification System", "Admin Dashboard"

4. **No Clear Scope**
   - ❌ Epic description: "Implement backend features"
   - ✅ Epic description: "API endpoints for user management: create, update, delete accounts with role-based access control"

5. **Ignoring Dependencies**
   - ❌ Plan Epics that all depend on each other sequentially
   - ✅ Structure Epics to enable parallel work where possible

6. **Testing/Docs as Separate Epics**
   - ❌ "Epic: Write All Tests", "Epic: Documentation"
   - ✅ Testing and docs are part of each feature Epic's Definition of Done

7. **Arbitrary Splitting**
   - ❌ "Epic: Implementation Part 1", "Epic: Implementation Part 2"
   - ✅ Split by logical capability boundaries, not arbitrary phases

## Handling Feedback

When stakeholders request Epic restructuring:

1. **Read all comments** - Review all feedback on Epic structure
2. **Understand the request** - What's the specific issue? (scope, naming, dependencies)
3. **Analyze impact** - Which Epics need changes? Which Stories move?
4. **Restructure** - Merge, split, or rename Epics as needed
5. **Update tracking system** - Modify Epic descriptions, re-parent Stories if needed
6. **Re-validate** - Run through quality checklist again

### Example Feedback Loop

**Feedback**: "Epic 'Backend Services' is too broad - split into API layer and worker layer"

**Response**:
1. Create new Epic: "API Gateway Services" (endpoints, validation, routing)
2. Create new Epic: "Background Workers" (async tasks, job processing, state management)
3. Archive/close original Epic 3
4. Move User Stories to appropriate new Epics
5. Update Feature description to reference new Epic structure

## Epic Naming Patterns

### Pattern: [Component/Layer] + [Capability]

Good examples:
- "API Gateway & Routing"
- "Data Pipeline Processing"
- "Frontend User Interface"
- "State Management System"

### Pattern: [User-Facing Feature]

Good examples:
- "User Authentication"
- "Dashboard Analytics"
- "Report Generation"
- "Admin Management Tools"

### Pattern: [System Integration]

Good examples:
- "Payment Gateway Integration"
- "Email Service Integration"
- "Third-Party API Connectors"

### Anti-Patterns to Avoid

Bad examples:
- "Backend Part 1" (vague, arbitrary)
- "Implement Features" (not specific)
- "Bug Fixes" (not an Epic, should be individual Stories)
- "Testing and QA" (testing is part of every Epic)
- "Nice to Have Items" (scope creep dump)

## Size Guidelines

**Epic Size** (measured in User Stories):
- **Too small**: 1-2 stories → Merge with another Epic or make it a single Story
- **Right-sized**: 3-7 stories → Good Epic scope
- **Too large**: 8+ stories → Split into multiple Epics

**Epic Duration** (rough estimate):
- **Small Epic**: 1-2 weeks (3-4 stories)
- **Medium Epic**: 2-4 weeks (5-6 stories)
- **Large Epic**: 4-6 weeks (7 stories)

If an Epic would take >6 weeks, it's likely too large and should be split.

## Parent-Child Hierarchy

```
Feature (ID-1)
├── Epic 1 (ID-14)
│   ├── Story 1.1 (ID-46)
│   ├── Story 1.2 (ID-47)
│   └── Story 1.3 (ID-48)
├── Epic 2 (ID-15)
│   ├── Story 2.1 (ID-51)
│   └── Story 2.2 (ID-52)
└── Epic 3 (ID-16)
    └── Story 3.1 (ID-58)
```

**Key Points**:
- Every Epic has exactly one parent (the Feature)
- Every Story has exactly one parent (an Epic)
- Features can have 2-5 Epics
- Epics can have 3-7 Stories

## References

- Epic Definition & Best Practices: https://www.atlassian.com/agile/project-management/epics
- Splitting Features into Epics: https://www.mountaingoatsoftware.com/blog/stories-epics-and-themes
- Epic Sizing Guidelines: https://www.scrum.org/resources/blog/epics-vs-stories-and-why-it-matters
