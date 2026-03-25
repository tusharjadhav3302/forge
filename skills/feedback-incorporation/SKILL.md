# Feedback Incorporation & Revision Skill

## Purpose

Parse human feedback from Jira comments and incorporate revisions into regenerated artifacts (PRD, spec, plan) with surgical precision. This skill ensures AI agents respond accurately to PM/Tech Lead feedback without unnecessary full regeneration.

## When to Use

Use this skill when:
- Regenerating PRD after PM rejection (node_1)
- Regenerating spec after PM/Tech Lead rejection (node_4)
- Regenerating plan after Tech Lead rejection (node_6)
- Handling any human feedback loop in the workflow
- Responding to clarification requests

## Core Principles

### 1. Always Fetch Current Ticket State

Never rely on cached/stale data. Always fetch the latest ticket state via Jira MCP to see all comments, even rapid edits.

### 2. Surgical Updates Over Full Regeneration

Preserve what works. Only regenerate sections that feedback addresses. Full regeneration wastes tokens and risks losing good parts.

### 3. Vague Feedback Requires Clarification

Don't guess. If feedback is ambiguous, ask for specifics via Jira comment. Better to ask than implement the wrong thing.

### 4. Conflicting Feedback Stops Work

If PM and Tech Lead give conflicting instructions, flag the conflict and wait for resolution. Never make arbitrary decisions.

### 5. Document What Changed

Always add revision notes showing what changed and why. Transparency builds trust.

## Feedback Parsing Process

### Step 1: Fetch Latest Ticket State

```python
# Use Jira MCP to get current ticket with all comments
ticket = jira_get_issue(ticket_id)

# Ticket includes:
# - description (current artifact content)
# - comments (all feedback, including bot comments)
# - status (current state)
# - updated timestamp
```

### Step 2: Filter Human Comments

```python
# Separate human comments from bot comments
human_comments = [
    c for c in ticket.comments
    if c.author.display_name != "AI Agent Bot"  # Filter out our own comments
]

# Sort by created date descending (newest first)
human_comments.sort(key=lambda c: c.created, reverse=True)

# Get latest human comment
latest_feedback = human_comments[0] if human_comments else None
```

**Why Filter Bot Comments?**
- Prevent feedback loops (don't incorporate AI's own comments)
- Focus on human intent

**Should We Read All Comments or Just Latest?**
- **Latest only** for simple edits: "Add X section"
- **All comments** for complex threads: PM asks question, Tech Lead answers, PM clarifies
- Default: Read latest + scan previous 2-3 for context

### Step 3: Classify Feedback Type

Determine what kind of feedback this is:

1. **Specific Addition**: "Add GDPR compliance section"
   - Action: Add new section/content
   - Regeneration: Partial (targeted addition)

2. **Specific Modification**: "Change success metric from '< 1s' to '< 500ms'"
   - Action: Update existing section
   - Regeneration: Partial (targeted edit)

3. **Vague Request**: "Make security section more detailed"
   - Action: Ask for clarification
   - Regeneration: Wait for specifics

4. **Removal**: "Remove multi-tenancy requirement, out of scope"
   - Action: Delete section/content
   - Regeneration: Partial (targeted removal)

5. **Approval**: "Looks good" or status change to approved state
   - Action: Proceed to next node
   - Regeneration: None

6. **Fundamental Rejection**: "This misunderstands the problem, start over"
   - Action: Full regeneration
   - Regeneration: Complete restart

### Step 4: Extract Actionable Instructions

Parse the comment text to extract what needs to change:

**Example 1: Specific Addition**
```
PM Comment: "Add GDPR compliance requirements - we're handling EU user data"

Extracted Actions:
- Add section: "GDPR Compliance"
- Location: Non-Functional Requirements → Security
- Content: Requirements for GDPR compliance with EU data
- Also update: Risks section (add "GDPR violation" risk)
```

**Example 2: Specific Modification**
```
Tech Lead Comment: "Reuse existing accounts table instead of creating new users table"

Extracted Actions:
- Modify section: Data Model Changes
- Change: Remove "users" table creation
- Add: Integration with existing accounts service
- Update: Implementation Steps (add API integration step)
```

**Example 3: Vague Request**
```
PM Comment: "Security section needs more"

Extracted Actions:
- Clarification needed
- Ask: "Which security aspects? (authentication, authorization, encryption, audit logging, etc.)"
- Wait for response
```

### Step 5: Determine Regeneration Scope

Decision tree for regeneration scope:

```
Is feedback specific and actionable?
├─ Yes → Can we surgically update?
│  ├─ Yes → Partial regeneration (update specific section)
│  └─ No → Why not?
│     ├─ Change affects multiple sections → Regenerate all affected sections
│     └─ Fundamental architecture change → Full regeneration
└─ No → Is feedback vague or conflicting?
   ├─ Vague → Ask for clarification, don't regenerate
   └─ Conflicting → Flag conflict, wait for resolution
```

## Surgical Update Strategies

### Strategy 1: Section Addition

**When**: Feedback asks to add new content

**Process**:
1. Identify insertion point (which section, where in document)
2. Generate only the new section
3. Insert at appropriate location
4. Update table of contents if needed
5. Add revision note

**Example**:
```markdown
# PRD v1.1 - Password Reset Feature

[Existing sections...]

## Non-Functional Requirements

### Security

[Existing security content...]

### GDPR Compliance *(Added v1.1)*

**Requirement**: All user data handling must comply with GDPR.

**Details**:
- User consent required for data collection
- Right to access personal data (API endpoint)
- Right to deletion (hard delete within 30 days)
- Data portability (export to JSON format)

**Validation**: Annual GDPR audit by legal team

---

**Revision History**:
- v1.1 (2026-03-25): Added GDPR Compliance section per PM feedback
```

### Strategy 2: Section Modification

**When**: Feedback asks to change existing content

**Process**:
1. Locate section to modify
2. Regenerate only that section with feedback incorporated
3. Replace old section with new version
4. Add revision note showing what changed

**Example**:
```markdown
## Success Metrics *(Updated v1.1)*

- **Response Time**: < 500ms p95 *(changed from < 1s)*
- **Email Delivery**: 95% delivered within 5s
- **User Adoption**: 60% of users reset password via self-service (down from support calls)

---

**Revision History**:
- v1.1 (2026-03-25): Tightened response time metric from < 1s to < 500ms per PM feedback
```

### Strategy 3: Section Removal

**When**: Feedback asks to remove content (out of scope, incorrect)

**Process**:
1. Remove entire section
2. Update any cross-references to that section
3. Add revision note explaining removal

**Example**:
```markdown
## Scope

### In Scope
- Password reset via email
- Security question fallback

### Out of Scope *(Updated v1.1)*
- Multi-tenancy support *(removed - out of scope for Phase 1)*
- OAuth integration
- Biometric authentication

---

**Revision History**:
- v1.1 (2026-03-25): Removed multi-tenancy from scope per Tech Lead feedback
```

### Strategy 4: Cross-Section Update

**When**: Feedback impacts multiple sections

**Process**:
1. Identify all affected sections
2. Update each section
3. Ensure consistency across all updates
4. Add comprehensive revision note

**Example Feedback**: "Reuse existing accounts table"

**Affected Sections**:
1. Data Model Changes: Remove users table, add accounts service integration
2. Implementation Steps: Add API integration step
3. Dependencies: Add accounts-service dependency
4. Testing Strategy: Update to test accounts service integration

All sections updated with revision notes.

## Handling Vague Feedback

### Detection Patterns

Feedback is vague if it contains:
- Subjective terms without definition: "better", "cleaner", "more professional"
- Missing specifics: "needs more detail" (which areas?)
- Ambiguous scope: "improve security" (which aspects?)
- No actionable instruction: "I don't like this"

### Response Pattern

When vague feedback detected:

1. **Add Jira comment** asking for clarification:
```
Thanks for the feedback! To ensure I address your concerns accurately, could you please specify:

[For "needs more detail"]
- Which sections need more detail? (e.g., Architecture, Testing, Security)
- What level of detail are you looking for? (e.g., specific code examples, more scenarios)

[For "improve security"]
- Which security aspects? (e.g., authentication, authorization, data encryption, audit logging, input validation)
- Are there specific security requirements or standards to follow? (e.g., OWASP Top 10, SOC 2)

I'm happy to revise once I understand the specific areas to focus on.
```

2. **Do NOT regenerate** - Wait for clarification
3. **Do NOT guess** - Guessing wastes time and may be wrong
4. **Update ticket status** to "Needs Clarification" if available

## Handling Conflicting Feedback

### Detection

Conflict exists when:
- PM says "add X", Tech Lead says "remove X"
- PM says "in scope", Tech Lead says "out of scope"
- Two reviewers give contradictory instructions

### Response Pattern

1. **Add Jira comment** tagging both parties:
```
@PM @TechLead - I've received conflicting feedback:

**PM Comment**: "Add real-time notifications"
**Tech Lead Comment**: "No real-time features in Phase 1, out of scope"

Could you please align on whether real-time notifications should be included? I'll wait for confirmation before proceeding with the revision.
```

2. **Do NOT proceed** - Wait for conflict resolution
3. **Do NOT choose a side** - Let humans decide
4. **Update status** to "Blocked - Conflicting Feedback"

## Full Regeneration Triggers

When surgical updates aren't sufficient, full regeneration is needed:

### Trigger 1: Fundamental Misunderstanding

**Feedback**: "This completely misses the point - the feature is about X, not Y"

**Action**: Full regeneration
- Re-read original ticket description
- Incorporate all historical comments
- Regenerate entire artifact from scratch

### Trigger 2: Cascading Changes

**Feedback**: "Change the target persona from developers to end users"

**Impact**: Affects every section (language, examples, metrics, risks)

**Action**: Full regeneration
- Persona change is fundamental
- Every section needs rewriting
- Surgical updates would miss subtle changes

### Trigger 3: Scope Expansion Beyond 50%

**Feedback**: Multiple additions that expand scope by >50%

**Action**: Full regeneration
- Too many sections affected
- Surgical updates become more complex than full rewrite
- Risk of inconsistency

## Quality Checklist for Revised Artifacts

After incorporating feedback, verify:

- [ ] **All feedback addressed**: Every instruction from comment incorporated
- [ ] **No new issues introduced**: Revision didn't break existing good content
- [ ] **Consistency maintained**: Updated sections align with unchanged sections
- [ ] **Revision notes added**: Clear documentation of what changed and why
- [ ] **Cross-references updated**: Any links/mentions updated if sections moved
- [ ] **No hallucinations**: If feedback mentioned services/repos, validated they exist
- [ ] **Format preserved**: Markdown/Jira markup consistent with original

## Examples

### Example 1: Specific Feedback (Surgical Update)

**Original PRD Section**:
```markdown
## Success Metrics
- Response time < 1s
- 90% email delivery rate
```

**Feedback**: "Tighten response time to < 500ms and email delivery to 95%"

**Updated Section**:
```markdown
## Success Metrics *(Updated v1.1)*
- Response time < 500ms p95 *(changed from < 1s)*
- Email delivery rate: 95% *(changed from 90%)*

---
**Revision History**:
- v1.1 (2026-03-25): Tightened performance metrics per PM feedback
```

### Example 2: Vague Feedback (Clarification)

**Feedback**: "Security section needs work"

**Response (Jira Comment)**:
```
Thanks for reviewing! To address your security concerns accurately, could you specify:

1. Which aspects need more detail?
   - Authentication mechanisms?
   - Authorization/access control?
   - Data encryption (at rest, in transit)?
   - Audit logging?
   - Input validation?

2. Are there specific security standards or requirements?
   - OWASP Top 10 compliance?
   - SOC 2 controls?
   - Company security policies?

3. Any specific threats or attack vectors to address?

I'll revise once I understand the specific areas to focus on.
```

**Action**: Wait for clarification, do not regenerate

### Example 3: Conflicting Feedback (Flag)

**PM Comment**: "Add multi-language support"
**Tech Lead Comment**: "No i18n in Phase 1, out of scope"

**Response (Jira Comment)**:
```
@PM @TechLead - I've received conflicting feedback on multi-language support:

**PM**: Add multi-language support
**Tech Lead**: No i18n in Phase 1

Could you please align on scope? Should multi-language support be:
- Included in Phase 1?
- Moved to Phase 2/Future?
- Out of scope entirely?

I'll wait for confirmation before revising the PRD.
```

**Action**: Block until resolved

### Example 4: Cascading Change (Full Regeneration)

**Feedback**: "Change architecture from synchronous API to event-driven async"

**Impact Analysis**:
- Architecture diagram: Complete redesign
- Components: Message queue added, API flow changes
- Data flow: Async patterns instead of request/response
- Testing: New async testing requirements
- Risks: New async-related risks
- Dependencies: Add message broker

**Decision**: Full regeneration
- Too many sections affected (6+ major sections)
- Architectural change is fundamental
- Surgical updates would be more complex than full rewrite

### In  (PRD Regeneration)
```python
def (state):
    ticket_id = state["ticket_id"]
    # Fetch current ticket (always fresh)
    ticket = jira_mcp.get_issue(ticket_id)
    # Get latest human feedback
    feedback = get_latest_human_comment(ticket.comments)
    if not feedback:
        # First time generating PRD (no feedback yet)
        prd = generate_prd_from_scratch(ticket.description)
    else:
        # Incorporating feedback
        feedback_type = classify_feedback(feedback.text)
        if feedback_type == "vague":
            # Ask for clarification
            jira_mcp.add_comment(ticket_id, clarification_request(feedback))
            return state  # Don't regenerate yet
        elif feedback_type == "conflicting":
            # Flag conflict
            jira_mcp.add_comment(ticket_id, conflict_flag(feedback))
            return state  # Block until resolved
        elif feedback_type == "specific":
            # Surgical update
            current_prd = parse_prd_from_jira(ticket.description)
            updated_prd = apply_feedback_surgically(current_prd, feedback)
        else:  # fundamental_rejection
            # Full regeneration
            updated_prd = generate_prd_from_scratch(
                ticket.description,
                history=ticket.comments
            )
    # Update Jira with revised PRD
    jira_mcp.update_issue(ticket_id, description=updated_prd)
    jira_mcp.transition_issue(ticket_id, "Pending PRD Approval")
    return state
```
### In  (Spec Regeneration)
Same pattern as node_1, but for spec.md feedback.
### In  (Plan Regeneration)
Same pattern as node_1, but for plan.md feedback.
## Common Pitfalls to Avoid

1. **Using Cached/Stale Ticket Data**
   - ❌ Relying on state from hours ago
   - ✅ Always fetch fresh ticket state before regenerating

2. **Guessing at Vague Feedback**
   - ❌ "Security needs work" → Add random security sections
   - ✅ Ask for specifics: Which security aspects?

3. **Full Regeneration by Default**
   - ❌ Any feedback → Regenerate entire artifact
   - ✅ Surgical updates when possible

4. **Ignoring Bot Comments Filtering**
   - ❌ Incorporate AI's own comments as feedback
   - ✅ Filter to human comments only

5. **Not Documenting Changes**
   - ❌ Silently update content
   - ✅ Add revision notes explaining what changed

6. **Choosing Sides in Conflicts**
   - ❌ "PM outranks Tech Lead, use PM's feedback"
   - ✅ Flag conflict, let humans resolve

## References

- Jira Comment API: https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-comments/
- Feedback Loop Patterns: https://martinfowler.com/articles/qa-in-production.html
- Revision Control in Documents: https://en.wikipedia.org/wiki/Revision_control
