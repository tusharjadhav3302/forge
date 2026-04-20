Analyze the CI failures described in the file below and produce a structured fix plan.

## Failures File

{failures_file_path}

## Attempt

This is fix attempt **{attempt}**.

Read that file. Before downloading any logs, follow Step 0 of the analyze-ci skill: check `.forge/fix-plan.md` for prior attempts and `git log --oneline -10` for prior commits. If this is attempt 2 or higher, identify what was already tried and do not repeat approaches that did not resolve the failure. Then download the full log for each check, analyze locally, and write the updated fix plan to `.forge/fix-plan.md`.
