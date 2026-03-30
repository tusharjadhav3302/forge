---
name: fix-ci
description: Analyze CI failures and generate fixes. Use when CI/CD pipeline fails and needs automated repair.
---

# CI Fix Skill

Diagnose CI failures and generate minimal fixes.

## Instructions

1. Analyze the CI error logs
2. Identify the root cause of failure
3. Generate a minimal fix
4. Explain the issue and solution

## Common CI Failure Types

### Test Failures
- Assertion errors
- Missing test dependencies
- Flaky tests
- Environment differences

### Build Failures
- Compilation errors
- Missing dependencies
- Version conflicts
- Configuration issues

### Lint/Format Failures
- Code style violations
- Type errors
- Import ordering
- Documentation gaps

### Security Scan Failures
- Vulnerability alerts
- Dependency issues
- Secret detection

## Output Format

```markdown
## Failure Analysis

### Error Type
[test/build/lint/security]

### Root Cause
[Brief explanation of what went wrong]

### Affected Files
- path/to/file1.py
- path/to/file2.py

## Fix

### Changes Required
[Description of the fix]

### Code Changes

```path/to/file.py
<complete file contents>
```

### Commit Message
[Suggested commit message for the fix]

## Verification
[How to verify the fix works]
```

## Fix Guidelines

1. **Minimal**: Fix only what's broken
2. **Safe**: Don't introduce new issues
3. **Tested**: Ensure the fix resolves the CI failure
4. **Documented**: Explain why the fix works
