# Quality Validation & Self-Review Skill

## Purpose

Validate generated artifacts before submitting for human review. This skill catches errors, hallucinations, and incompleteness automatically, reducing feedback loops and improving first-pass approval rates.

## When to Use

Use this skill when:
- Completing PRD generation (before transition to "Pending PRD Approval")
- Completing spec generation (before transition to "Pending Spec Approval")
- Completing plan generation (before transition to "Pending Plan Approval")
- After incorporating feedback (validate revised artifact)
- Before any human review gate

## Core Principles

### 1. Validate Before Submit

Never submit unchecked work. Always run validation before transitioning to review status.

### 2. Auto-Fix Simple Issues

If an issue can be fixed automatically (e.g., hallucinated repo removed), fix it. Don't bother humans with trivial problems.

### 3. Flag Complex Issues

If an issue needs judgment (e.g., ambiguous requirement), flag for human review. Don't guess.

### 4. Completeness > Perfection

Better to have 85% complete artifact flagged for minor issues than to block on perfection.

### 5. Validation is Fast

Don't spend 5 minutes validating a 2-minute generation. Keep validation under 30 seconds.

## Validation Process

### Step 1: Structural Completeness Check

**For PRD**:
- [ ] **Problem Statement** exists and is specific
- [ ] **Goals** exist (2-5 goals minimum)
- [ ] **Success Metrics** exist (at least 2 measurable metrics)
- [ ] **Requirements** section exists (functional + non-functional)
- [ ] **Scope** section exists (in-scope + out-of-scope)
- [ ] **Risks** section exists (at least 2 risks with mitigations)
- [ ] **Assumptions** section exists
- [ ] **Dependencies** section exists (if applicable)
- [ ] **Non-Functional Requirements** section exists

**Scoring**:
- 9/9 sections → 100% complete ✓
- 7-8/9 sections → 85% complete ⚠️ (flag missing sections)
- < 7/9 sections → < 75% complete ✗ (regenerate)

**For Spec**:
- [ ] **User Story** exists (As a/I want/So that)
- [ ] **Acceptance Criteria** exists (at least 3 Given/When/Then scenarios)
- [ ] **Edge Cases** section exists (at least 2 edge cases)
- [ ] **Definition of Done** exists (at least 3 items)
- [ ] **Technical Notes** section exists (if applicable)

**Scoring**:
- 5/5 sections → 100% complete ✓
- 4/5 sections → 80% complete ⚠️ (flag missing section)
- < 4/5 sections → < 75% complete ✗ (regenerate)

**For Plan**:
- [ ] **Overview** section exists
- [ ] **Affected Repositories** section exists (at least 1 repo)
- [ ] **Implementation Steps** exist (at least 3 steps)
- [ ] **Data Model Changes** section exists (if applicable)
- [ ] **Integration Points** section exists
- [ ] **Testing Strategy** section exists
- [ ] **Quality Attributes** section exists (scalability, reliability, security, observability)
- [ ] **Dependencies** section exists
- [ ] **Risks and Mitigations** section exists (at least 2 risks)
- [ ] **Rollback Plan** section exists

**Scoring**:
- 10/10 sections → 100% complete ✓
- 8-9/10 sections → 85% complete ⚠️ (flag missing sections)
- < 8/10 sections → < 80% complete ✗ (regenerate)

### Step 2: Content Quality Check

**Vague Language Detection**:

❌ **Avoid**:
- "user-friendly"
- "fast"
- "scalable"
- "robust"
- "efficient"
- "appropriate"
- "correct"
- "properly"

✅ **Require**:
- Specific metrics: "< 500ms response time"
- Concrete criteria: "Handles 1000 req/sec sustained"
- Clear definitions: "User-friendly = accessible (WCAG 2.1 AA), intuitive (< 3 clicks to goal)"

**Check each section**:
- Count vague terms
- If > 3 vague terms in PRD → Flag ⚠️
- If > 1 vague term in success metrics → Flag ✗ (must be specific)

**Specificity Check**:

**Success Metrics Examples**:
- ❌ "Improve performance" → Too vague
- ✅ "Response time < 500ms p95" → Specific

**Requirements Examples**:
- ❌ "Must be secure" → Too vague
- ✅ "Must use HMAC signature validation on all webhook endpoints" → Specific

**Goals Examples**:
- ❌ "Make users happy" → Too vague
- ✅ "Reduce password reset support tickets by 40%" → Specific

**Scoring**:
- 0-2 vague terms → ✓ Good specificity
- 3-5 vague terms → ⚠️ Some vagueness (flag for review)
- > 5 vague terms → ✗ Too vague (regenerate with specificity prompt)

### Step 3: Hallucination Detection

**Check all references against System Catalog**:

```python
def detect_hallucinations(artifact, system_catalog):
    hallucinations = []

    # Extract all mentioned repos/services
    mentioned_repos = extract_repo_references(artifact)
    mentioned_services = extract_service_references(artifact)
    mentioned_apis = extract_api_references(artifact)

    # Validate repos
    for repo in mentioned_repos:
        if repo not in system_catalog.repositories:
            hallucinations.append({
                "type": "unknown_repo",
                "value": repo,
                "severity": "high"
            })

    # Validate services
    for service in mentioned_services:
        if service not in system_catalog.services:
            hallucinations.append({
                "type": "unknown_service",
                "value": service,
                "severity": "high"
            })

    # Validate APIs (if documented in catalog)
    for api in mentioned_apis:
        if api.is_internal() and api not in system_catalog.apis:
            hallucinations.append({
                "type": "unknown_api",
                "value": api,
                "severity": "medium"
            })

    return hallucinations
```

**Auto-Fix Strategy**:
- **Unknown repo/service** → Remove mention, add note: "(reference removed - not found in System Catalog)"
- **Unknown API** → Mark as "needs verification" rather than removing

**Example**:
```
Original: "Integrate with password-manager-service for hashing"
Validation: password-manager-service not in System Catalog
Auto-Fix: "Integrate with auth-service for password hashing"
Note: "(Changed from password-manager-service - not found in catalog. Verified auth-service handles password operations.)"
```

### Step 4: Constitution.md Compliance Check

**For Plans Only** (PRD/Spec don't need this):

```python
def check_constitution_compliance(plan, constitutions):
    violations = []

    for repo, constitution in constitutions.items():
        # Check technology mandates
        for mandate in constitution.mandates:
            if mandate.technology == "database":
                if mandate.required == "PostgreSQL":
                    if "mysql" in plan.lower() or "mongodb" in plan.lower():
                        violations.append({
                            "repo": repo,
                            "rule": "Must use PostgreSQL",
                            "violation": "Plan mentions MySQL or MongoDB",
                            "severity": "critical",
                            "auto_fix": "replace with PostgreSQL"
                        })

        # Check forbidden patterns
        for forbidden in constitution.forbidden:
            if forbidden.pattern in plan:
                violations.append({
                    "repo": repo,
                    "rule": f"Forbidden: {forbidden.pattern}",
                    "violation": f"Plan contains {forbidden.pattern}",
                    "severity": "high"
                })

    return violations
```

**Auto-Fix Strategy**:
- **Technology violation** → Replace (MySQL → PostgreSQL)
- **Pattern violation** → Flag for manual fix (requires design change)

### Step 5: Length and Detail Check

**Minimum Lengths** (rule of thumb):

| Artifact | Minimum Words | Ideal Words | Too Long |
|----------|--------------|-------------|----------|
| PRD | 500 | 800-1500 | > 3000 |
| Spec (per Story) | 200 | 300-600 | > 1000 |
| Plan | 800 | 1200-2500 | > 5000 |

**Section Depth Check**:

**PRD Sections**:
- Problem Statement: 50-150 words (2-3 paragraphs)
- Goals: 2-5 goals, each 1-2 sentences
- Success Metrics: 2-5 metrics, specific and measurable
- Risks: 2-5 risks, each with mitigation

**Spec Scenarios**:
- Acceptance Criteria: 3-7 Given/When/Then scenarios
- Each scenario: 1 Given, 1 When, 1-2 Then clauses
- Edge Cases: 2-5 items
- DoD: 3-7 items

**Scoring**:
- Meets all depth minimums → ✓
- 1-2 sections under minimum → ⚠️ Flag shallow sections
- > 2 sections under minimum → ✗ Regenerate with more depth

### Step 6: Scenario Coverage Check (Specs Only)

**Ensure acceptance criteria cover**:
- [ ] **Happy path** (at least 1 scenario)
- [ ] **Alternative path** (at least 1 scenario)
- [ ] **Error case** (at least 1 scenario)
- [ ] **Edge case** (at least 1 scenario)

**Example**:
```
✓ Happy path: "Given valid credentials, When user logs in, Then redirect to dashboard"
✓ Error case: "Given invalid password, When user logs in, Then show error message"
✓ Edge case: "Given account locked, When user logs in, Then show locked message"
✗ Missing: Alternative path (e.g., "Given user forgot password, When clicks reset link, Then...")
```

**Scoring**:
- 4/4 coverage types → ✓ Complete
- 3/4 coverage types → ⚠️ Flag missing type
- < 3/4 coverage types → ✗ Regenerate with more scenarios

### Step 7: Cross-Reference Consistency

**Check internal consistency**:

**In PRDs**:
- Requirements mentioned in Goals? ✓
- Risks align with Requirements? ✓
- Success metrics measure Goals? ✓

**In Specs**:
- Edge Cases covered by Acceptance Criteria? ✓
- DoD covers all Acceptance Criteria? ✓

**In Plans**:
- Implementation Steps address all Affected Repos? ✓
- Testing Strategy covers all Integration Points? ✓
- Risks cover all identified constraints? ✓

**Example Inconsistency**:
```
Goal: "Enable real-time notifications"
Success Metric: "95% email delivery rate"
→ Inconsistency: Goal says "real-time", metric is about "email" (not real-time)
```

## Validation Report Format

```markdown
# Validation Report: [Artifact Name]

## Overall Score: 85% ⚠️

### Completeness: 90% ✓
- ✓ All required sections present
- ✓ Adequate depth in most sections
- ⚠️ Risks section: Only 1 risk (recommend 2-3)

### Quality: 80% ⚠️
- ✓ Specific success metrics
- ⚠️ 3 vague terms detected: "user-friendly" (Goals), "robust" (Requirements), "fast" (NFRs)
- ✓ No excessive length

### Hallucination Check: 100% ✓
- ✓ All repos validated against System Catalog
- ✓ All services validated against System Catalog
- ✓ No invented references

### Constitution Compliance: N/A
(Not applicable for PRDs)

### Recommendations:
1. Add 1-2 more risks to Risks section
2. Replace vague terms with specific criteria:
   - "user-friendly" → Define specific usability metrics
   - "robust" → Define specific error handling requirements
   - "fast" → Specify response time thresholds

### Auto-Fixes Applied:
- None

### Action: Submit for Review ✓
Artifact is 85% complete and acceptable for human review. Recommendations are minor improvements.
```

## Auto-Fix vs Flag Decision Tree

```
Issue detected
├─ Can it be fixed objectively?
│  ├─ Yes → Auto-fix
│  │  └─ Examples: hallucinated repo removed, MySQL→PostgreSQL, typo fixed
│  └─ No → Flag for human
│     └─ Examples: vague requirement needs clarification, missing section needs content
└─ Is it critical?
   ├─ Yes → Block submission, regenerate
   │  └─ Examples: < 75% complete, critical constitution violation
   └─ No → Flag but allow submission
      └─ Examples: minor vagueness, 1 missing risk
```

## Quality Gates

### Gate 1: Minimum Viable (75% threshold)
- **If < 75% completeness** → ✗ Regenerate, do not submit
- **If < 75% quality** → ✗ Regenerate with quality prompts
- **If critical hallucination** → ✗ Auto-fix and re-validate

### Gate 2: Good Enough (85% threshold)
- **If 75-85% complete** → ⚠️ Flag issues, but allow submission
- **If 75-85% quality** → ⚠️ Flag recommendations, but allow submission
- **If medium hallucinations** → ⚠️ Auto-fix and note

### Gate 3: Excellent (95%+ threshold)
- **If > 95% complete** → ✓ Submit with confidence
- **If > 95% quality** → ✓ Minimal review needed
- **If no issues** → ✓ Praise quality

```python
def (state):
    # Generate PRD
    prd = generate_prd(...)
    # Validate before submitting
    validation = validate_artifact(
        artifact=prd,
        artifact_type="PRD",
        system_catalog=state["system_catalog"]
    )
    if validation.score < 75:
        # Critical issues, regenerate
        prd = regenerate_prd_with_improvements(
            original=prd,
            issues=validation.critical_issues
        )
        validation = validate_artifact(prd, "PRD", state["system_catalog"])
    # Apply auto-fixes
    prd = apply_auto_fixes(prd, validation.auto_fixable_issues)
    # Add validation notes if flagged issues
    if validation.flagged_issues:
        prd += f"\n\n---\n**Validation Notes**:\n{format_issues(validation.flagged_issues)}"
    # Submit
    jira_update(state["ticket_id"], description=prd)
    return state
```
## Common Validation Patterns

### Pattern 1: Missing Section Detection

```python
required_sections = {
    "PRD": ["Problem Statement", "Goals", "Success Metrics", "Requirements", "Scope", "Risks"],
    "Spec": ["User Story", "Acceptance Criteria", "Edge Cases", "Definition of Done"],
    "Plan": ["Overview", "Affected Repositories", "Implementation Steps", "Testing Strategy", "Risks"]
}

def check_sections(artifact, artifact_type):
    missing = []
    for section in required_sections[artifact_type]:
        if section not in artifact:
            missing.append(section)
    return missing
```

### Pattern 2: Vague Language Scanner

```python
vague_terms = [
    "user-friendly", "intuitive", "easy", "simple",
    "fast", "slow", "quick", "responsive",
    "scalable", "robust", "reliable", "stable",
    "efficient", "optimized", "performant",
    "appropriate", "correct", "proper", "suitable"
]

def count_vague_terms(text):
    count = 0
    found = []
    for term in vague_terms:
        if term.lower() in text.lower():
            count += text.lower().count(term.lower())
            found.append(term)
    return count, found
```

### Pattern 3: Reference Validator

```python
def validate_references(artifact, system_catalog):
    # Extract references using regex or NLP
    repo_pattern = r'`([a-z-]+(?:-[a-z]+)*)`'  # e.g., `auth-service`
    service_pattern = r'\b([a-z-]+(?:-[a-z]+)*-service)\b'

    repos = re.findall(repo_pattern, artifact)
    services = re.findall(service_pattern, artifact)

    invalid = []
    for repo in repos:
        if repo not in system_catalog.repositories:
            invalid.append(("repo", repo))

    for service in services:
        if service not in system_catalog.services:
            invalid.append(("service", service))

    return invalid
```

## References

- Code Quality Metrics: https://www.softwaretestinghelp.com/code-quality-metrics/
- Hallucination Detection in LLMs: https://arxiv.org/abs/2305.14251
- Technical Writing Best Practices: https://developers.google.com/tech-writing
