# Dynamic Skill Loading by Jira Project

## Overview

Allow Forge to load project-specific skill overrides based on the Jira project derived from a ticket key. When a project-specific skill directory exists, it replaces the default skill set entirely for that project.

## Problem

Forge currently loads all agent skills from a single directory (`plugins/forge-sdlc/skills/`). As Forge manages tickets across multiple Jira projects (e.g. AISOS, OPENSHIFT), those projects may require different coding standards, tooling conventions, or workflow behaviors. There is currently no way to customize agent instructions per project without modifying shared defaults.

## Design

- The Jira project name is extracted from the ticket key: `AISOS-123` → `aisos` (lowercased)
- If `plugins/{project}/skills/` exists, it is used as the skill directory for that ticket
- If no project-specific directory exists, the default `plugins/forge-sdlc/skills/` is used
- This is an all-or-nothing replacement — no per-skill merging
- The same resolution logic applies to both the orchestrator agent (PRD, spec, epic, task generation) and the container agent (implementation, CI fix)
- A shared resolver utility encapsulates the lookup so both consumers use identical logic

## Directory Structure

```
plugins/
├── forge-sdlc/               # default skills (always present)
│   └── skills/
│       ├── generate-prd/
│       ├── generate-spec/
│       ├── fix-ci/
│       └── ...
└── aisos/                    # project-specific override (optional)
    └── skills/
        ├── generate-prd/     # replaces default entirely for AISOS tickets
        └── fix-ci/
```

## Implementation Plan

**New: `src/forge/plugins/resolver.py`**
- `resolve_skill_path(ticket_key, base_dir)` — extracts project prefix, returns project-specific path if it exists, otherwise default

**Modified: `src/forge/sandbox/runner.py`**
- Pass `ticket_key` into `_get_skill_mounts()`, call resolver to determine which skill directory to mount

**Modified: `src/forge/integrations/agents/agent.py`**
- Call resolver when constructing the orchestrator agent's skill context

No changes to skill file formats, agent prompts, or existing defaults.

## Rollout & Testing

- Unit tests for `resolve_skill_path()`: project override present, absent (fallback), malformed key, missing base dir
- Integration smoke test: run a task against a ticket with an override directory present, confirm override is used
- No behavior change for projects without an override directory — always falls back to default

## Future Work

Out of scope for this feature:

- **Per-skill fallback** — a project provides some skills, missing ones fall back to defaults (avoided now to prevent forced naming constraints)
- **Skills from the project repo** — pulling skill definitions from the target repository rather than Forge itself, enabling project teams to own their skills
- **Broader plugin mechanism** — project-specific configuration beyond skills (custom gates, workflow steps, label conventions) using the same `plugins/{project}/` namespace
