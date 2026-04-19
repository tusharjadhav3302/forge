Analyze the CI failures described in the file below and produce a structured fix plan.

## Failures File

{failures_file_path}

Read that file. For each failed check, download the full log to `.forge/logs/` using `gh api` or `curl`, then analyze the local file to understand the failure. Write the fix plan to `.forge/fix-plan.md` following the analyze-ci skill instructions.
