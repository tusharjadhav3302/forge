<!--
SYNC IMPACT REPORT
==================
Version change: N/A → 1.0.0 (initial ratification)
Modified principles: N/A (initial creation)
Added sections:
  - Core Principles (8 principles derived from LLD ADRs)
  - Technology Stack & Architecture
  - Development Workflow & Quality Gates
  - Governance
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ (Constitution Check section already present)
  - .specify/templates/spec-template.md ✅ (user scenarios aligned with SDD principle)
  - .specify/templates/tasks-template.md ✅ (phase structure aligned with workflow)
Follow-up TODOs: None
-->

# Forge Constitution

## Core Principles

### I. Spec-Driven Development (SDD)

All work MUST be anchored to approved specifications following a strict hierarchy:
PRD → Spec → Plan → Tasks.

- AI agents MUST NOT generate code without an approved spec
- The PRD defines business goals, user personas, and strategic value
- The Spec defines user scenarios with Given/When/Then acceptance criteria
- The Plan defines architecture, technical approach, and Epic breakdown
- Tasks define implementation steps with target repository assignments

**Rationale:** Eliminates "vibe coding" hallucinations where AI generates functionally
correct but requirement-misaligned code. Ensures predictability and scope control.

### II. Human-in-the-Loop (HITL) Gates

Human approval MUST be obtained at key workflow transitions. Execution MUST halt at
designated pause gates until human review is complete.

- **Product Manager owns "WHAT"**: Approves PRD and Spec (business requirements)
- **Technical Lead owns "HOW"**: Approves Epic breakdown and Plans (implementation architecture)
- **Engineers review "EXECUTION"**: Code review and merge approval

Feedback loops route back to generation nodes when approval is denied, preserving
revision comments for context.

**Rationale:** Maintains human accountability for critical decisions while enabling AI
to handle execution. Prevents autonomous drift from business intent.

### III. Jira as Single Source of Truth (Zero-UI Architecture)

All artifacts MUST be stored in Jira. NO custom dashboards or parallel tracking systems.

- PRD stored in Jira Feature description field
- Spec stored in Jira Feature custom field or attachment
- Plan stored in Epic description field
- Tasks stored in Task description fields with target repository labels
- Comments serve as feedback mechanism for revision loops

**Rationale:** Eliminates adoption friction and information silos. Product Managers,
Tech Leads, and Developers interact with AI exactly as they do with human engineers.

### IV. Trust but Verify

Specs and plans represent the *intended outline*, but the codebase is the *absolute truth*.

- AI agents MUST read the current state of the codebase before implementing
- When spec and codebase conflict, the agent MUST adapt implementation to reality
- Agents MUST NOT blindly overwrite code based on potentially outdated specifications
- Agents SHOULD flag significant divergences between spec and codebase

**Rationale:** Accommodates upstream-first open-source models where external contributors
may merge changes without updating internal specs. Prevents breaking upstream code.

### V. Localized Guardrails

Technical constraints MUST be defined at the repository level, not globally.

- Each repository contains `constitution.md` or `agents.md` defining repo-specific rules
- MCP skills are mounted contextually based on the repository being worked on
- Global system prompts MUST NOT contain repository-specific linting, schema, or deployment rules
- Custom tools (linters, validators, deployment checks) load only for relevant workspaces

**Rationale:** Portfolio diversity (multiple languages, CI/CD systems, compliance needs)
requires context-specific guidance. Reduces LLM token consumption and hallucination risk.

### VI. Repository-Grouped Concurrency

Parallel execution MUST be grouped by repository, not by individual task.

- All tasks targeting the same repository execute sequentially on a single feature branch
- Each repository produces one PR containing all changes across relevant Epics
- Tasks MUST specify target repository via component or label
- Concurrent PRs open across repositories, but commits within a repo are ordered

**Rationale:** Prevents competing PRs and merge conflict chaos that would result from
parallel task-level execution within the same codebase.

### VII. Ephemeral Workspaces

Execution environments MUST be pristine and short-lived.

- Workspaces are generated on-the-fly for each repository/ticket combination
- Workspaces MUST be destroyed after the PR is opened
- No leftover build artifacts, uncommitted files, or state from previous runs
- Git tokens and API secrets exposure window MUST be minimized

**Rationale:** Prevents "state rot" from persistent clones and minimizes security exposure.
Guarantees reproducible execution regardless of prior activity.

### VIII. Modular Workflow Routing

The workflow entry point MUST match the ticket type and required rigor level.

- **Features**: Full SDD pipeline (PRD → Spec → Plan → Tasks → Execution)
- **Bugs**: RCA generation → Approval → TDD bug fix → CI/CD → Review
- **Tech Debt**: Skip PRD/Spec → Enter at Planning → Execute refactor
- **Security Patches**: Skip all planning → Direct execution with restricted scope
- **Documentation**: Dedicated doc-gen subgraph, text-only changes

**Rationale:** Forcing simple bug fixes through full planning cycles wastes compute and
frustrates teams. Issue type determines appropriate rigor.

## Technology Stack & Architecture

### Core Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| Orchestrator | LangGraph (Python) | State machine and concurrent routing |
| Webhook Gateway | FastAPI | Inbound event handling |
| State Persistence | Redis + LangGraph Checkpointer | Workflow pause/resume |
| Coding Engine | Claude Code (Anthropic SDK) | Task execution |
| Source of Truth | Jira REST API + Webhooks | Work tracking |
| Traceability | Langfuse + Python logging | Observability |
| Secret Management | Vault | Credential storage |

### Architectural Requirements

- **Message Queue**: Events MUST be buffered through a message broker for resilience
- **FIFO Ordering**: Events for the same ticket MUST process sequentially
- **Freshness Check**: Workers MUST verify current Jira status before consuming tokens
- **Rate Limiting**: Worker pools MUST respect external API rate limits
- **Distributed Locking**: No concurrent state modifications for the same ticket

## Development Workflow & Quality Gates

### Phase Transitions

1. **Drafting PRD** → PM approval → **Drafting Spec**
2. **Drafting Spec** → PM approval → **Planning**
3. **Planning** → Epics created → **Pending Plan Approval** (per Epic)
4. **Pending Plan Approval** → Tech Lead approval → **Ready for Breakdown**
5. **Ready for Breakdown** → Tasks generated → **In Development**
6. **In Development** → Code written → **Pending CI/CD**
7. **Pending CI/CD** → Tests pass → **Pending AI Review**
8. **Pending AI Review** → AI review passes → **In Review**
9. **In Review** → Human approval → **Done**

### Quality Gates

- **CI/CD Validation**: Autonomous fix loop (max 3-5 retries), then escalate
- **AI Code Review**: Security, quality, spec alignment, constitution compliance
- **Human Code Review**: Final approval before merge
- All gates MUST pass before workflow advancement

### Feedback Loops

- **Feature-level feedback**: Deletes and regenerates all Epics
- **Epic-level feedback**: Updates only the affected Epic's plan
- **PR feedback**: Routes comments back to implementation node for fixes

## Governance

### Amendment Procedure

1. Propose amendment via PR to this constitution
2. Document rationale and impact assessment
3. Obtain approval from project maintainers
4. Update dependent templates if principles change
5. Increment version according to semantic versioning

### Versioning Policy

- **MAJOR**: Backward-incompatible principle removals or redefinitions
- **MINOR**: New principles added or materially expanded guidance
- **PATCH**: Clarifications, wording, typo fixes, non-semantic refinements

### Compliance Review

- All PRs MUST be verified against constitution principles
- AI agents MUST read constitution before planning or coding
- Violations MUST be flagged and justified in Complexity Tracking
- Runtime guidance in `agents.md` supplements but MUST NOT contradict this constitution

**Version**: 1.0.0 | **Ratified**: 2026-03-30 | **Last Amended**: 2026-03-30
