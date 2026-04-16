---
name: local-code-review
description: Review local code changes for breaking issues and fix them in-place. Use before PR creation to catch critical problems early.
---

# Local Code Review Skill

Review the provided diff for **breaking issues only** and fix them directly in the workspace files.

## Scope — What to Review

Only flag and fix issues that would cause:
- **Build or compile failures** — code that won't compile or import correctly
- **Runtime crashes** — null pointer dereferences, unhandled exceptions on the happy path, type errors
- **Security holes** — hardcoded secrets, SQL injection, shell injection, arbitrary code execution
- **Broken tests** — test failures introduced by the changes
- **Spec violations** — core acceptance criteria from the spec that are clearly unimplemented or inverted

## Scope — What to Ignore

Do NOT flag or attempt to fix:
- Code style, formatting, or naming conventions
- Minor improvements or refactoring opportunities
- Performance optimisations unless catastrophic
- Missing documentation or comments
- "Could be done better" feedback
- Anything already handled by the project's linter

## Workflow

1. Run `git diff origin/main...HEAD --no-color` to get all changes on this branch
2. If the diff is empty, output `NO_BREAKING_ISSUES` and stop
3. For each breaking issue found:
   a. Identify the exact file and location
   b. Read the current file content using `read_file`
   c. Apply a targeted fix using `edit_file`
   d. Verify the fix compiles / passes a targeted test if possible
4. If no breaking issues are found, output `NO_BREAKING_ISSUES` and stop
5. After fixing, output a summary of what was fixed

## Output Format

If no breaking issues:
```
NO_BREAKING_ISSUES
```

If breaking issues were found and fixed:
```
BREAKING_ISSUES_FIXED

Fixed:
- [file:line] Brief description of issue and fix applied
- [file:line] ...

Unfixed (could not resolve):
- [file:line] Brief description of why it couldn't be fixed
```

## Important

- Fix directly in the workspace files — do NOT post GitHub comments
- Be surgical: change only what is broken, nothing more
- If you cannot safely fix an issue, document it in the Unfixed section rather than making a risky change
