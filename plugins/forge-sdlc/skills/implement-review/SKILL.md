---
name: implement-review
description: Analyze PR review comments against the current codebase, then produce a structured plan of actionable items and a list of any contested comments.
---

# PR Review Analysis Skill

You are analyzing code review feedback on a pull request. Your workspace contains the full repository. Use your tools to understand the code, not just the diff.

## Workflow

1. Read the review comments from `.forge/review-comments.md`
2. Understand the current state of the code:
   - Run `git log --oneline -10` to see recent commits
   - Run `git diff origin/main..HEAD --stat` to see what changed
   - Read the specific files mentioned in the review comments
   - Use `grep` to find the relevant code sections
3. For each review comment, decide:
   - **ACTIONABLE**: you agree the change is correct and will include it in the implementation plan
   - **CONTESTED**: you have a strong technical objection (change contradicts the spec, introduces a bug, or is factually wrong)
4. Write your analysis to two files:

### `.forge/review-plan.md` (always write this file)

List only the ACTIONABLE items. Format each as:

```
## Item N: <short title>

**File:** path/to/file.go
**Location:** function name or line range
**Change:** what to do and why
```

If all comments are contested, write: `# No actionable items` and nothing else.

### `.forge/review-objections.md` (only if there are CONTESTED items)

For each contested comment:

```
## Contested: <short title>

**Reviewer said:** exact quote of the review comment
**Why I object:** technical reasoning (spec reference, potential bug, factual error)
**Counter-proposal:** what I suggest instead (if anything)
```

If there are no objections, do NOT create this file.

## Important

- Read the actual source files — do not guess at the code structure
- Base objections on technical facts, not preferences
- Be specific about file paths and line numbers
- Do NOT make any code changes in this phase — analysis only
