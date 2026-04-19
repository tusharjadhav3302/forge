# Proposal: Dynamic Skill Loading by Jira Project

**Author:** eshulman2
**Date:** 2026-04-19
**Status:** Draft

## Summary

Forge currently loads agent skills from a single shared directory, applying the same instructions to every ticket regardless of which Jira project it belongs to. This proposal adds project-specific skill overrides: when a `plugins/{project}/skills/` directory exists, it replaces the default skill set for tickets in that project, allowing different teams and repositories to customize agent behavior without touching shared defaults.

## Motivation

### Problem Statement

All Forge agent skills (PRD generation, spec generation, CI fix, implementation guidance, etc.) are loaded from `plugins/forge-sdlc/skills/`. As Forge manages tickets across multiple Jira projects — each potentially representing a different team, codebase, or technology stack — the one-size-fits-all skill set creates friction:

- A Go project and a Python project need different implementation conventions
- An OpenShift project may have specific CI tooling and testing requirements  
- A team may want custom PRD or spec formats without affecting all other projects

There is currently no way to customize agent instructions per project without modifying the shared defaults, which affects every team using Forge.

### Current Workarounds

Teams embed project-specific instructions inside ticket descriptions or comments, rely on `CLAUDE.md` in the target repository (which helps for implementation but not for orchestrator-side generation), or accept the shared defaults and manually revise generated artifacts.

## Proposal

### Overview

Introduce a resolver that derives the Jira project key from a ticket key (`AISOS-123` → `aisos`) and looks for a project-specific skill directory at `plugins/{project}/skills/`. If found, that directory is used instead of the default. If not found, behavior is unchanged — the default `plugins/forge-sdlc/skills/` is used. This is an all-or-nothing directory replacement; no per-skill merging.

The same resolver is used by both the orchestrator agent (PRD, spec, epic, task generation) and the container agent (implementation, CI fix), so behavior is consistent across the full workflow.

### Detailed Design

#### Directory structure

```
plugins/
├── forge-sdlc/               # default skills (always present)
│   └── skills/
│       ├── generate-prd/
│       ├── generate-spec/
│       ├── analyze-ci/
│       ├── fix-ci/
│       └── ...
└── aisos/                    # project-specific override (optional)
    └── skills/
        ├── generate-prd/     # replaces the default entirely for AISOS tickets
        └── fix-ci/
```

If `plugins/aisos/skills/` exists, all AISOS tickets use it. Skills not present in the override directory are simply absent — the orchestrator will not fall back to the default for missing skills. This all-or-nothing approach avoids forcing project maintainers to copy skills they don't need to override.

#### New: `src/forge/plugins/resolver.py`

```python
def resolve_skill_dir(ticket_key: str, base_dir: Path) -> Path:
    """Return project-specific skill dir if it exists, else the default."""
    project = ticket_key.split("-")[0].lower()
    override = base_dir.parent / project / "skills"
    if override.is_dir():
        return override
    return base_dir / "forge-sdlc" / "skills"
```

Simple, pure function. Testable without any Forge dependencies.

#### Modified: `src/forge/sandbox/runner.py`

Pass `ticket_key` into `_get_skill_mounts()` and call `resolve_skill_dir` to determine which directory to mount into the container.

#### Modified: `src/forge/integrations/agents/agent.py`

Call `resolve_skill_dir` when constructing the orchestrator agent's skill context, replacing the current hardcoded path.

No changes to skill file formats, agent prompts, or the container entrypoint.

### User Experience

A team maintaining the `OPENSHIFT` Jira project creates `plugins/openshift/skills/generate-prd/SKILL.md` with their own PRD format requirements. From that point, any `OPENSHIFT-*` ticket processed by Forge uses their custom PRD skill. No config change, no restart — just a new directory.

```
# For AISOS-123 with plugins/aisos/skills/ present:
resolver("AISOS-123") → plugins/aisos/skills/

# For OPENSHIFT-456 with no override:
resolver("OPENSHIFT-456") → plugins/forge-sdlc/skills/  (default)

# For MYPROJ-789 with plugins/myproj/skills/ present:
resolver("MYPROJ-789") → plugins/myproj/skills/
```

Projects without an override directory see no behavior change.

## Alternatives Considered

| Alternative | Pros | Cons | Why Not |
|-------------|------|------|---------|
| Per-skill fallback (override some, inherit rest) | More granular; teams only override what they need | Requires naming constraints and merge logic; ambiguous precedence | Adds complexity without strong demand; can be added later |
| Skills from the target repository (`CLAUDE.md`-style) | Teams own their skills in their repo | Requires Forge to clone the repo before knowing which skills to use; chicken-and-egg for PRD generation | Out of scope; valid future direction |
| Config file mapping project keys to skill directories | Explicit, auditable | Yet another config file to maintain; same effect as directory convention | Convention over configuration is simpler |
| Per-skill override files (patch files on top of defaults) | Minimal duplication | Complex merge semantics; hard to reason about which instructions apply | Over-engineered for the current need |

## Implementation Plan

### Phases

1. **Phase 1:** `resolver.py` + unit tests. No production impact. (~2 hours)
2. **Phase 2:** Wire resolver into `runner.py` (container agent) and `agent.py` (orchestrator agent). (~half day)
3. **Phase 3:** Integration smoke test: create a minimal override directory for a test project, run a task, confirm override is used. (~half day)

### Dependencies

- [ ] No external dependencies
- [ ] Resolver must be importable from both `forge.sandbox` and `forge.integrations.agents` without circular imports — place in `forge.plugins.resolver`

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Project override missing a required skill causes agent failure | Med | Med | Document that an override directory must be complete or empty; consider logging a warning when a required skill is not found in the override dir |
| Malformed ticket key (no `-` separator) crashes resolver | Low | Low | Guard with `if "-" not in ticket_key: return default` |
| Override directory accidentally applied to wrong project due to key prefix collision (e.g. `AI` matching `AISOS`) | Low | Low | Match on full prefix before `-`, not substring |

## Open Questions

- [ ] Should per-skill fallback (override some skills, inherit the rest) be in scope? The all-or-nothing approach is simpler now but may frustrate teams who only need to override one skill.
- [ ] Should Forge log which skill directory was selected on each invocation? Useful for debugging but adds noise.
- [ ] Future: should project teams be able to keep their skills in their own repository rather than in Forge's `plugins/` directory?
