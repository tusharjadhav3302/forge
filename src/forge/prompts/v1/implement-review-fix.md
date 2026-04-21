Implement the code changes described in `.forge/review-plan.md`, then ensure the project builds cleanly.

## Instructions

1. Read `.forge/review-plan.md`. If it says `# No actionable items`, exit without changes.

2. Implement each item — minimal, targeted edits only.

3. After making changes, run the project's standard post-change steps (codegen, lint, build). Check `README.md`, `CONTRIBUTING.md`, `Makefile`, or `CLAUDE.md` for the correct commands. A typical sequence:
   - Regenerate any auto-generated files if source templates changed
   - Run the linter/formatter on changed files
   - Verify the build compiles

4. Commit everything (implementation + any generated or formatted files) in a single commit:
   `git commit -m "[{ticket_key}] review: address PR feedback"`

5. Do NOT push — the orchestrator handles that.

Ticket: {ticket_key}
