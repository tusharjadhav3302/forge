---
name: analyze-ci
description: Analyze CI failures by fetching logs and producing a structured fix plan. Use before attempting automated CI fixes.
---

# CI Failure Analysis Skill

You are given a list of failed CI checks with their log URLs. Fetch the actual logs, understand the root cause of each failure, and produce a structured fix plan for a developer agent to follow.

## Workflow

1. Read the failures file at the path provided in the prompt using `read_file`
2. For each failed check that has a log URL, fetch the log — but retrieve **only the last 200 lines**. CI failures almost always appear at the end.
3. Categorize each failure (see categories below)
4. For fixable failures, determine exactly what needs to change
5. Produce a structured fix plan (see output format)

**Important**: Do not include full log content in your response. Summarise findings in the fix plan only.

## Failure Categories

### Fixable by code change
- **codegen-outdated**: Generated files (zz_generated.*, CRD YAML, mocks) are out of sync with source. Fix: run the project's codegen command.
- **format**: Code formatting violations (`gofmt`, `ruff`, etc.). Fix: run the formatter on the affected files.
- **lint**: Lint rule violations with clear error messages. Fix: address the specific violations.
- **compile**: Compilation errors. Fix: correct the specific syntax/type errors.
- **unit-test**: Test assertion failures caused by a code bug. Fix: correct the implementation or update the test.

### Not fixable by code change — skip
- **e2e**: End-to-end tests requiring a real cluster or cloud environment
- **infra**: Timeouts, network errors, missing cluster resources, quota issues
- **flaky**: Non-deterministic failures with no clear code cause

## Output Format

Produce a fix plan in this exact structure so the fix agent can follow it mechanically:

```
# CI Fix Plan

## Summary
[1-2 sentences: what failed and what the fix involves]

## Fixable Failures

### [check-name]
**Category**: [codegen-outdated | format | lint | compile | unit-test]
**Root Cause**: [exact error message or description]
**Affected Files**: [list of files to change]
**Fix**:
1. [exact command or edit to apply]
2. [verification command to confirm fix]

### [next check-name]
...

## Skipped Failures

### [check-name]
**Reason**: [e2e | infra | flaky] — [brief explanation]

### [next check-name]
...
```

## Important

- Fetch the actual log content — do not guess based on the check name alone
- Be specific: include exact file paths, line numbers, and error messages
- For codegen failures, identify the exact `go:generate` directive or script to run
- If a failure log is unavailable, mark it as skipped with reason "log unavailable"
