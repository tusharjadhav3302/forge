---
name: analyze-ci
description: Analyze CI failures by fetching logs and producing a structured fix plan. Use before attempting automated CI fixes.
---

# CI Failure Analysis Skill

You are given a list of failed CI checks with their log URLs. Fetch the actual logs, understand the root cause of each failure, and produce a structured fix plan for a developer agent to follow.

## Workflow

1. Read the failures file at the path provided in the prompt using `read_file`
2. Create `.forge/logs/` in the workspace if it doesn't exist: `mkdir -p .forge/logs`
3. For each failed check that has a log URL, **download to `.forge/logs/`** first — one download, then analyze locally:

   **Single log file** (GitHub Actions, plain Prow log URL):
   - GitHub Actions: `gh api repos/{owner}/{repo}/actions/jobs/{job-id}/logs > .forge/logs/{check-name}.txt`
   - Plain URL: `curl -sL "{url}" -o .forge/logs/{check-name}.txt`

   **Log bundle / archive** (Prow often uploads a `.tar.gz` bundle of all logs):
   - Download: `curl -sL "{url}" -o .forge/logs/{check-name}.tar.gz`
   - Extract: `tar -xzf .forge/logs/{check-name}.tar.gz -C .forge/logs/{check-name}/`
   - The bundle typically contains `build-log.txt`, controller logs, and test output

   **GitHub Actions artifacts** (uploaded on failure):
   - `gh run download {run-id} -n {artifact-name} -D .forge/logs/{check-name}/`

4. Analyze the downloaded files using local tools — use your judgment:
   - `grep -i "error\|fail\|panic\|FAIL" .forge/logs/{check-name}.txt | tail -50`
   - `tail -100 .forge/logs/{check-name}/build-log.txt`
   - Search through extracted bundle files for the root cause
4. Categorize each failure (see categories below)
5. For fixable failures, determine exactly what needs to change
6. Write the fix plan to `.forge/fix-plan.md` in the workspace (see output format)

**Important**: Do not print large log content to the conversation. Analyse locally and write only the structured fix plan to the output file.

## Failure Categories

### Fixable by code change
- **codegen-outdated**: Generated files (zz_generated.*, CRD YAML, mocks) are out of sync with source. Fix: run the project's codegen command.
- **format**: Code formatting violations (`gofmt`, `ruff`, etc.). Fix: run the formatter on the affected files.
- **lint**: Lint rule violations with clear error messages. Fix: address the specific violations.
- **compile**: Compilation errors. Fix: correct the specific syntax/type errors.
- **unit-test**: Test assertion failures caused by a code bug. Fix: correct the implementation or update the test.
- **e2e-code-bug**: An e2e/integration test fails with a consistent, reproducible assertion error pointing to a code logic defect — not an infrastructure problem. The failure message is the same across runs and environments. Fix: correct the implementation. Examples: wrong condition status, missing requeue, incorrect state machine transition.

### Not fixable by code change — skip
- **e2e-infra**: End-to-end tests that fail due to infrastructure problems: DevStack/cluster startup failures, OpenStack API timeouts, networking errors, resource quota issues, or missing environment resources. The failure is in the test harness or cloud environment, not the code under test.
- **infra**: Timeouts, network errors, missing cluster resources, quota issues outside of e2e test context.
- **flaky**: Genuinely non-deterministic failures — fails with *different* errors across runs, or fails <30% of the time with no consistent root cause.

### Distinguishing e2e-code-bug from e2e-infra and flaky

Before marking any e2e failure as skipped, apply these checks:

1. **Failure rate**: Does the same test fail in ≥70% of runs across multiple environments? High, consistent failure rates indicate a code bug, not a flaky environment. A test that fails 3 out of 4 runs with the same error is almost certainly a code bug.

2. **Error consistency**: Is the *same assertion* failing with the *same error message* across runs and environments? Consistent errors point to code; varied errors (different steps, timeouts vs. assertion mismatches) point to infrastructure or true flakiness.

3. **Error type**: Does the failure message mention assertion mismatches on computed values (condition status, timestamps, counts) vs. infrastructure errors (connection refused, resource not found in OpenStack, DevStack not ready)?

4. **Failure isolation**: Does the failure happen at a specific, named test step that exercises business logic, rather than during setup/teardown or cluster bootstrapping?

If any of these checks points to a code defect, classify as **e2e-code-bug** and investigate the implementation, not the test harness. Read the relevant source code to confirm the root cause before writing the fix plan.

## Output Format

Write the fix plan to `.forge/fix-plan.md` in this exact structure so the fix agent can follow it mechanically:

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
**Reason**: [e2e-infra | infra | flaky] — [brief explanation]

### [next check-name]
...
```

## Important

- Fetch the actual log content — do not guess based on the check name alone
- Be specific: include exact file paths, line numbers, and error messages
- For codegen failures, identify the exact `go:generate` directive or script to run
- If a failure log is unavailable, mark it as skipped with reason "log unavailable"
