---
name: fix-ci
description: Apply CI fixes from a pre-analyzed fix plan. Use after analyze-ci has produced a structured plan.
---

# CI Fix Skill

You are running inside a container with the full repository workspace. You have been given a pre-analyzed fix plan. Follow it exactly — do not re-diagnose or second-guess it.

## Workflow

For each **Fixable Failure** in the fix plan:

1. Read the affected files listed in the plan
2. Apply the fix as described:
   - Run codegen commands with `execute`
   - Apply code edits with `edit_file`
   - Run formatters with `execute`
3. Run the verification command from the plan to confirm the fix works
4. Move to the next failure

Skip anything listed under **Skipped Failures** — do not attempt to fix them.

## After All Fixes

1. Stage only the files you changed (never `git add .` or `-A`)
2. Commit with a clear message referencing what was fixed
3. Do NOT push — the orchestrator handles that

## Guidelines

- Follow the plan — do not invent additional fixes
- Be surgical: only change files listed in the plan
- If a step in the plan fails or doesn't apply, skip it and note it in your output
- Do not reformat files not mentioned in the plan
