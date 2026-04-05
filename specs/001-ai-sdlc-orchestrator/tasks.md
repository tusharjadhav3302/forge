# Tasks: AI-Integrated SDLC Orchestrator

**Input**: Design documents from `/specs/001-ai-sdlc-orchestrator/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in spec - test tasks omitted. Add if needed.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/forge/`
- **Tests**: `tests/`
- Paths follow plan.md project structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure per plan.md in src/forge/
- [x] T002 Initialize Python project with pyproject.toml (Python 3.11+, dependencies: langgraph, fastapi, redis, anthropic, gitpython, httpx)
- [x] T003 [P] Configure ruff for linting and formatting in pyproject.toml
- [x] T004 [P] Create Dockerfile for containerized deployment
- [x] T005 [P] Create docker-compose.yml with Redis service for local development
- [x] T006 [P] Create .env.example with all required environment variables

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Implement configuration management in src/forge/config.py (Pydantic settings with env vars)
- [x] T008 [P] Create domain models in src/forge/models/workflow.py (FeatureStatus, EpicStatus, TaskStatus enums)
- [x] T009 [P] Create artifact models in src/forge/models/artifacts.py (Feature, Epic, Task dataclasses)
- [x] T010 [P] Create event models in src/forge/models/events.py (WebhookEvent, EventSource, EventStatus)
- [x] T011 Implement Redis connection and LangGraph checkpointer in src/forge/orchestrator/checkpointer.py
- [x] T012 [P] Implement Jira REST client base in src/forge/integrations/jira/client.py (httpx async client with auth)
- [x] T013 [P] Implement Jira data models in src/forge/integrations/jira/models.py (JiraIssue, JiraComment)
- [x] T014 [P] Implement GitHub client base in src/forge/integrations/github/client.py (httpx async client with auth)
- [x] T015 Implement queue producer in src/forge/queue/producer.py (Redis Streams publish)
- [x] T016 Implement queue consumer in src/forge/queue/consumer.py (Redis Streams consume with FIFO per ticket)
- [x] T017 [P] Implement queue message models in src/forge/queue/models.py
- [x] T018 Create FastAPI app skeleton in src/forge/main.py (app factory, router includes)
- [x] T019 [P] Implement health check endpoint in src/forge/api/routes/health.py
- [x] T020 [P] Create shared test fixtures in tests/conftest.py (Redis mock, Jira mock, async client)
- [x] T021 Implement Langfuse tracing integration in src/forge/integrations/langfuse/tracing.py
- [x] T022 Implement workflow state definition in src/forge/orchestrator/state.py (TypedDict for LangGraph)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - PRD Generation (Priority: P1)

**Goal**: Generate structured PRDs from raw Jira Feature descriptions

**Independent Test**: Create Jira Feature with raw requirements, transition to "Drafting PRD", verify PRD appears in description within 5 minutes

### Implementation for User Story 1

- [x] T023 [P] [US1] Implement Jira webhook payload parsing in src/forge/integrations/jira/webhooks.py
- [x] T024 [P] [US1] Implement Claude Code SDK wrapper in src/forge/integrations/claude/client.py
- [x] T025 [US1] Implement PRD generation node in src/forge/orchestrator/nodes/prd_generation.py (read raw desc, generate PRD, update Jira)
- [x] T026 [US1] Implement PRD approval gate in src/forge/orchestrator/gates/prd_approval.py (pause for PM review)
- [x] T027 [US1] Implement Jira description update in src/forge/integrations/jira/client.py (ADF format)
- [x] T028 [US1] Implement Jira status transition in src/forge/integrations/jira/client.py
- [x] T029 [US1] Add PRD feedback loop handling (read comment, regenerate on rejection)
- [x] T030 [US1] Wire PRD nodes into main graph in src/forge/orchestrator/graph.py

**Checkpoint**: PRD generation workflow functional and testable independently

---

## Phase 4: User Story 2 - Specification Generation (Priority: P1)

**Goal**: Generate behavioral specifications with Given/When/Then acceptance criteria

**Independent Test**: Approve PRD, verify complete spec with user scenarios appears in Jira within 5 minutes

### Implementation for User Story 2

- [x] T031 [US2] Implement spec generation node in src/forge/orchestrator/nodes/spec_generation.py (read PRD, generate spec)
- [x] T032 [US2] Implement spec approval gate in src/forge/orchestrator/gates/spec_approval.py (pause for PM review)
- [x] T033 [US2] Implement Jira custom field update for Specification in src/forge/integrations/jira/client.py
- [x] T034 [US2] Add spec feedback loop handling (read comment, regenerate on rejection)
- [x] T035 [US2] Wire spec nodes into main graph in src/forge/orchestrator/graph.py
- [x] T036 [US2] Add spec generation prompts with Given/When/Then template

**Checkpoint**: Spec generation workflow functional and testable independently

---

## Phase 5: User Story 3 - Epic Decomposition and Planning (Priority: P1)

**Goal**: Decompose Features into logical Epics with implementation plans

**Independent Test**: Approve spec, verify 2-5 Epics created in Jira with plans within 10 minutes

### Implementation for User Story 3

- [x] T037 [US3] Implement Epic creation in src/forge/integrations/jira/client.py (create Epic, link to Feature)
- [x] T038 [US3] Implement Epic deletion in src/forge/integrations/jira/client.py (for Feature-level regeneration)
- [x] T039 [US3] Implement epic decomposition node in src/forge/orchestrator/nodes/epic_decomposition.py
- [x] T040 [US3] Implement plan approval gate in src/forge/orchestrator/gates/plan_approval.py (pause for Tech Lead review)
- [x] T041 [US3] Add Feature-level feedback handling (delete all Epics, regenerate)
- [x] T042 [US3] Add Epic-level feedback handling (update single Epic plan)
- [x] T043 [US3] Wire epic nodes into main graph in src/forge/orchestrator/graph.py
- [x] T044 [US3] Implement Epic status aggregation (track when all Epics approved)

**Checkpoint**: Epic decomposition workflow functional and testable independently

---

## Phase 6: User Story 4 - Task Generation (Priority: P2)

**Goal**: Generate implementation Tasks for each approved Epic

**Independent Test**: Approve all Epics, verify Tasks created with repository assignments within 5 minutes per Epic

### Implementation for User Story 4

- [x] T045 [US4] Implement Task creation in src/forge/integrations/jira/client.py (create Task, link to Epic, add labels)
- [x] T046 [US4] Implement task generation node in src/forge/orchestrator/nodes/task_generation.py
- [x] T047 [US4] Add repository label assignment logic (extract repo from context)
- [x] T048 [US4] Wire task generation nodes into main graph in src/forge/orchestrator/graph.py
- [x] T049 [US4] Implement Task detail generation prompts (steps, acceptance criteria)

**Checkpoint**: Task generation workflow functional and testable independently

---

## Phase 7: User Story 5 - Webhook Event Processing (Priority: P2)

**Goal**: Receive, deduplicate, and route webhook events from Jira and GitHub

**Independent Test**: Send simulated webhooks, verify acknowledgment <500ms and correct routing

### Implementation for User Story 5

- [x] T050 [P] [US5] Implement Jira webhook endpoint in src/forge/api/routes/jira.py
- [x] T051 [P] [US5] Implement GitHub webhook endpoint in src/forge/api/routes/github.py
- [x] T052 [US5] Implement webhook deduplication middleware in src/forge/api/middleware/deduplication.py
- [x] T053 [US5] Implement payload validation middleware in src/forge/api/middleware/validation.py
- [x] T054 [US5] Implement GitHub webhook payload parsing in src/forge/integrations/github/webhooks.py
- [x] T055 [US5] Implement freshness check before processing in src/forge/queue/consumer.py
- [x] T056 [US5] Implement FIFO ordering per ticket in queue consumer
- [x] T057 [US5] Wire webhook routes into FastAPI app in src/forge/main.py

**Checkpoint**: Webhook processing functional and testable independently

---

## Phase 8: User Story 6 - Single Repository Code Execution (Priority: P2)

**Goal**: Create ephemeral workspace, implement Tasks, open PR

**Independent Test**: Assign Tasks to test repo, verify PR opened with commits for each Task

### Implementation for User Story 6

- [x] T058 [P] [US6] Implement workspace manager in src/forge/workspace/manager.py (create tempdir, cleanup)
- [x] T059 [P] [US6] Implement git operations in src/forge/workspace/git_ops.py (clone, branch, commit, push)
- [x] T060 [US6] Implement guardrails loader in src/forge/workspace/guardrails.py (read constitution.md/agents.md)
- [x] T061 [US6] Implement workspace setup node in src/forge/orchestrator/nodes/workspace_setup.py
- [x] T062 [US6] Implement implementation node in src/forge/orchestrator/nodes/implementation.py (invoke Claude Code)
- [x] T063 [US6] Implement PR creation in src/forge/integrations/github/client.py
- [x] T064 [US6] Implement task router node in src/forge/orchestrator/nodes/task_router.py (group by repo)
- [x] T065 [US6] Wire execution nodes into main graph in src/forge/orchestrator/graph.py
- [x] T066 [US6] Implement workspace destruction on PR creation

**Checkpoint**: Single-repo execution functional and testable independently

---

## Phase 9: User Story 7 - CI/CD Validation and Autonomous Fix Loop (Priority: P3)

**Goal**: Monitor CI results, attempt autonomous fixes, escalate on failure

**Independent Test**: Introduce deliberate test failure, verify fix attempt before escalation

### Implementation for User Story 7

- [x] T067 [US7] Implement CI status parsing from GitHub webhooks in src/forge/integrations/github/webhooks.py
- [x] T068 [US7] Implement CI evaluator node in src/forge/orchestrator/nodes/ci_evaluator.py
- [x] T069 [US7] Implement error log extraction from CI in src/forge/integrations/github/client.py
- [x] T070 [US7] Implement autonomous fix logic (read logs, generate fix, commit)
- [x] T071 [US7] Implement retry counter with configurable limit
- [x] T072 [US7] Implement escalation to "Blocked" status on retry exhaustion
- [x] T073 [US7] Wire CI evaluator into main graph with feedback loop

**Checkpoint**: CI validation with fix loop functional and testable independently

---

## Phase 10: User Story 8 - AI Code Review (Priority: P3)

**Goal**: AI review for quality, security, spec alignment before human review

**Independent Test**: Open PR with code quality issues, verify AI review comments posted

### Implementation for User Story 8

- [x] T074 [US8] Implement AI reviewer node in src/forge/orchestrator/nodes/ai_reviewer.py
- [x] T075 [US8] Implement PR comment posting in src/forge/integrations/github/client.py
- [x] T076 [US8] Implement spec alignment checking (compare code to spec)
- [x] T077 [US8] Implement constitution compliance checking
- [x] T078 [US8] Implement review decision routing (pass to human or back to implementation)
- [x] T079 [US8] Wire AI reviewer into main graph after CI evaluator

**Checkpoint**: AI code review functional and testable independently

---

## Phase 11: User Story 9 - Human Code Review and Merge (Priority: P3)

**Goal**: Route human review feedback, transition tickets to Done on merge

**Independent Test**: Approve and merge PR, verify Jira tickets transition to Done

### Implementation for User Story 9

- [x] T080 [US9] Implement PR review event parsing from GitHub webhooks
- [x] T081 [US9] Implement review comment routing back to implementation node
- [x] T082 [US9] Implement merge event detection from GitHub webhooks
- [x] T083 [US9] Implement Task → Done transition on PR merge
- [x] T084 [US9] Implement Epic → Done aggregation (all Tasks done)
- [x] T085 [US9] Implement Feature → Done aggregation (all Epics done)
- [x] T086 [US9] Wire human review handling into main graph

**Checkpoint**: Human review and merge workflow functional and testable independently

---

## Phase 12: User Story 10 - Multi-Repository Concurrent Execution (Priority: P4)

**Goal**: Execute Tasks across multiple repositories in parallel

**Independent Test**: Assign Tasks to 3+ repos, verify PRs opened on all within 20 minutes

### Implementation for User Story 10

- [x] T087 [US10] Implement parallel task router with LangGraph Send API in src/forge/orchestrator/nodes/task_router.py
- [x] T088 [US10] Implement concurrent workspace spawning
- [x] T089 [US10] Implement parallel execution thread tracking in workflow state
- [x] T090 [US10] Implement PR aggregation across repositories
- [x] T091 [US10] Update graph to support fan-out/fan-in execution pattern

**Checkpoint**: Multi-repo concurrent execution functional and testable independently

---

## Phase 13: User Story 11 - Bug Fixing Workflow (Priority: P4)

**Goal**: Specialized bug workflow with RCA generation and TDD fix

**Independent Test**: Create Bug ticket with stack trace, verify RCA generation and TDD-style fix

### Implementation for User Story 11

- [x] T092 [US11] Implement bug router node in src/forge/orchestrator/nodes/bug_workflow.py (bypass PRD/Spec/Epic)
- [x] T093 [US11] Implement RCA generation node (analyze code, generate root cause analysis)
- [x] T094 [US11] Implement RCA approval gate in src/forge/orchestrator/gates/rca_approval.py
- [x] T095 [US11] Implement TDD bug fix logic (write failing test first, then fix)
- [x] T096 [US11] Implement modular workflow routing based on Issue Type in main graph
- [x] T097 [US11] Wire bug workflow into main graph with separate entry point

**Checkpoint**: Bug workflow functional and testable independently

---

## Phase 14: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T098 [P] Create README.md with project overview and setup instructions
- [x] T099 [P] Add API documentation with OpenAPI schema export
- [x] T100 Implement rate limiting for external API calls (Jira, GitHub, Claude)
- [x] T101 [P] Add structured logging throughout application
- [x] T102 Implement graceful shutdown handling for workers
- [x] T103 Add retry logic with exponential backoff for transient failures
- [ ] T104 Run quickstart.md validation end-to-end
- [ ] T105 Performance optimization for webhook response time (<500ms)

---

## Phase 15: User Story 12 - Observability and Tracing (Priority: P3)

**Goal**: Provide distributed tracing for all workflow executions with correlation IDs

**Independent Test**: Execute a workflow and verify trace data appears in configured backend with complete request path

**Source**: Added via spec sync (2026-04-05)

### Implementation for User Story 12

- [x] T106 [US12] Create OpenTelemetry configuration in src/forge/observability/config.py (tracer provider, exporters)
- [x] T107 [US12] Implement correlation ID middleware in src/forge/api/middleware/correlation.py (generate/propagate request IDs)
- [x] T108 [US12] Implement trace context propagation in src/forge/observability/context.py (thread-local storage)
- [x] T109 [P] [US12] Add tracing instrumentation to webhook endpoints in src/forge/api/routes/jira.py
- [x] T110 [P] [US12] Add tracing instrumentation to webhook endpoints in src/forge/api/routes/github.py
- [x] T111 [US12] Instrument LangGraph workflow execution in src/forge/orchestrator/graph.py
- [x] T112 [US12] Add trace metadata (workflow phase, ticket ID, repository) to all spans
- [x] T113 [US12] Implement trace exporter configuration (Jaeger, OTLP endpoints) in src/forge/config.py
- [x] T114 [US12] Wire tracing into FastAPI app lifecycle in src/forge/main.py

**Checkpoint**: Distributed tracing functional with end-to-end correlation IDs

---

## Phase 16: User Story 13 - System Metrics (Priority: P3)

**Goal**: Expose Prometheus-compatible metrics for monitoring and alerting

**Independent Test**: Send requests and verify counters/histograms update at /metrics endpoint

**Source**: Added via spec sync (2026-04-05)

### Implementation for User Story 13

- [x] T115 [US13] Create Prometheus metrics registry in src/forge/api/routes/metrics.py
- [x] T116 [US13] Implement /metrics endpoint in src/forge/api/routes/metrics.py
- [x] T117 [P] [US13] Add workflow counter metrics (total, by phase, by status)
- [x] T118 [P] [US13] Add phase duration histogram metrics
- [x] T119 [P] [US13] Add error rate counter metrics with labels (error type, phase)
- [x] T120 [US13] Add queue depth gauge metrics in src/forge/queue/consumer.py
- [x] T121 [US13] Instrument external API calls (Jira, GitHub, Claude) with latency histograms
- [x] T122 [US13] Wire metrics middleware into FastAPI app in src/forge/main.py

**Checkpoint**: Prometheus metrics endpoint functional and scrape-ready

---

## Phase 17: User Story 14 - Command Line Interface (Priority: P3)

**Goal**: CLI tool for operators to manage workflows, query status, and view logs

**Independent Test**: Run CLI commands and verify expected output and system state changes

**Source**: Added via spec sync (2026-04-05)

### Implementation for User Story 14

- [x] T123 [US14] Create CLI entry point in src/forge/cli.py (uses argparse)
- [x] T124 [US14] Implement `forge check <ticket-id>` command in src/forge/cli.py (status query)
- [x] T125 [US14] Implement `forge list` command (active workflows) in src/forge/cli.py
- [x] T126 [US14] Implement `forge retry <ticket-id>` command in src/forge/cli.py
- [x] T127 [US14] Implement `forge logs <ticket-id>` command in src/forge/cli.py
- [x] T128 [US14] Implement `forge run <ticket-id>` command (manual workflow start) in src/forge/cli.py
- [ ] T129 [US14] Add CLI configuration (API endpoint, auth) in src/forge/cli/config.py
- [x] T130 [US14] Register CLI as console script in pyproject.toml

**Checkpoint**: CLI functional for status queries, retries, and manual triggers

---

## Phase 18: Edge Case Hardening

**Goal**: Address edge cases identified in spec sync drift analysis

**Source**: align-tasks.md from spec sync (2026-04-05)

### Implementation for Edge Cases

- [x] T131 [US9] Fix _check_epic_completion stub in src/forge/orchestrator/nodes/human_review.py (query Jira for child Tasks)
- [x] T132 Add Jira rate limit handling with exponential backoff in src/forge/integrations/jira/client.py
- [x] T133 Implement webhook retry queue in src/forge/queue/retry.py (persist failed events, dead-letter queue)
- [x] T134 Add branch conflict detection before push in src/forge/workspace/git_ops.py
- [x] T135 Verify and document checkpoint recovery in src/forge/orchestrator/checkpointer.py
- [x] T136 Add missing guardrails validation warnings in src/forge/workspace/guardrails.py
- [x] T137 Add merge conflict detection before PR creation in src/forge/orchestrator/nodes/pr_creation.py

**Checkpoint**: Edge cases handled, system more resilient to failures

---

## Phase 19: Error Handling & Resilience

**Goal**: Improve error visibility, user notification, and workflow resilience

**Source**: Error handling analysis (2026-04-05)

### User-Facing Error Communication

- [ ] T138 [P] Post Jira comment on node failures in src/forge/orchestrator/nodes/prd_generation.py
- [ ] T139 [P] Post Jira comment on node failures in src/forge/orchestrator/nodes/spec_generation.py
- [ ] T140 [P] Post Jira comment on node failures in src/forge/orchestrator/nodes/epic_decomposition.py
- [ ] T141 [P] Post Jira comment on node failures in src/forge/orchestrator/nodes/task_generation.py
- [ ] T142 [P] Post Jira comment on node failures in src/forge/orchestrator/nodes/implementation.py
- [ ] T143 [P] Post Jira comment on node failures in src/forge/orchestrator/nodes/workspace_setup.py
- [ ] T144 Create shared error reporting helper in src/forge/orchestrator/nodes/error_handler.py

### Retry Logic & Circuit Breakers

- [ ] T145 Add max retry cap checking to all nodes (compare retry_count vs settings.max_retries)
- [ ] T146 Implement exponential backoff helper in src/forge/utils/backoff.py
- [ ] T147 Add retry logic with backoff to GitHub client in src/forge/integrations/github/client.py
- [ ] T148 Handle 5xx server errors with retry in Jira client (currently only handles 429)

### Queue Consumer Resilience

- [ ] T149 Fix silent exception handling in src/forge/queue/consumer.py:165 (add logging with context)
- [ ] T150 Improve freshness check error handling in src/forge/queue/consumer.py (don't silently proceed)
- [ ] T151 Add structured error logging with correlation IDs to consumer

### State & Idempotency

- [ ] T152 Track created resources in state for idempotent retries (avoid duplicate Jira tickets)
- [ ] T153 Add checkpoint freshness validation before workflow resume
- [ ] T154 Implement partial failure recovery (skip already-completed tasks on retry)

### API Client Error Handling

- [ ] T155 Handle specific HTTP error codes in Jira client (404, 403, 400) with meaningful errors
- [ ] T156 Handle specific HTTP error codes in GitHub client with meaningful errors
- [ ] T157 Add connection timeout and retry for network errors in both clients

### Structured Error Context

- [ ] T158 Enhance WorkflowState with error_type, error_timestamp, error_traceback fields
- [ ] T159 Add structured error logging middleware with context dict (task_key, repo, node)
- [ ] T160 Update ForgeLabel enum with BLOCKED_ERROR label for permanent failures

### Error Escalation

- [ ] T161 Implement error threshold escalation (after N retries, post summary to Jira and stop)
- [ ] T162 Add Slack/webhook notification option for critical failures in src/forge/integrations/notifications/

**Checkpoint**: Errors visible to users, workflows resilient to transient failures

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-13)**: All depend on Foundational phase completion
  - US1-3 (P1) can proceed in parallel or sequentially
  - US4-6 (P2) depend on US1-3 completion
  - US7-9 (P3) depend on US6 (execution must work first)
  - US10-11 (P4) depend on US6 (extends single-repo execution)
- **Polish (Phase 14)**: Depends on all desired user stories being complete
- **Observability (Phase 15)**: Foundational only - can run in parallel with other work
- **Metrics (Phase 16)**: Foundational only - can run in parallel with other work
- **CLI (Phase 17)**: Depends on API endpoints existing (Phase 2+)
- **Edge Case Hardening (Phase 18)**: Can run anytime after relevant features exist
- **Error Handling (Phase 19)**: Can run anytime after relevant nodes exist

### User Story Dependencies

- **US1 (PRD Generation)**: Foundational only - no story dependencies
- **US2 (Spec Generation)**: Depends on US1 (PRD must exist)
- **US3 (Epic Decomposition)**: Depends on US2 (Spec must exist)
- **US4 (Task Generation)**: Depends on US3 (Epics must exist)
- **US5 (Webhooks)**: Foundational only - enables all other stories
- **US6 (Execution)**: Depends on US4-5 (Tasks + webhooks must work)
- **US7 (CI/CD)**: Depends on US6 (PRs must be created first)
- **US8 (AI Review)**: Depends on US7 (CI must pass first)
- **US9 (Human Review)**: Depends on US8 (AI review must pass first)
- **US10 (Multi-Repo)**: Extends US6 (single-repo must work)
- **US11 (Bug Workflow)**: Foundational + US6 (separate entry but uses execution)
- **US12 (Observability)**: Foundational only - can run in parallel with other stories
- **US13 (Metrics)**: Foundational only - can run in parallel with other stories
- **US14 (CLI)**: Foundational only - needs API endpoints to query

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel
- US1-US3 can theoretically run in parallel (but have logical dependencies)
- US5 can run in parallel with US1-4 (independent webhook infrastructure)
- Within each story, tasks marked [P] can run in parallel

---

## Implementation Strategy

### MVP First (Phase 1 Shadow Mode - LLD Weeks 2-4)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3-5: US1-3 (PRD, Spec, Epic generation)
4. Complete Phase 7: US5 (Webhooks - needed for triggers)
5. **STOP and VALIDATE**: AI generates plans, humans implement code
6. Deploy for planning-only shadow mode

### Phase 2 Milestone (Single-Repo Execution - LLD Weeks 4-6)

1. Add Phase 6: US4 (Task Generation)
2. Add Phase 8: US6 (Single-Repo Execution)
3. **STOP and VALIDATE**: AI writes code to single test repo
4. Deploy for single-repo execution pilot

### Phase 3 Milestone (CI/CD Feedback - LLD Weeks 7-8)

1. Add Phases 9-11: US7-9 (CI, AI Review, Human Review)
2. **STOP and VALIDATE**: Full loop with self-healing
3. Deploy for CI/CD feedback loop

### Phase 4 Milestone (Full Orchestration - LLD Weeks 9+)

1. Add Phases 12-13: US10-11 (Multi-Repo, Bug Workflow)
2. Add Phase 14: Polish
3. **STOP and VALIDATE**: Full feature complete
4. Deploy for full orchestration

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story checkpoint = independently testable increment
- Follow LLD phased rollout: Planning Only → Single-Repo → CI/CD → Multi-Repo
- Commit after each task or logical group

## Summary

- **Total Tasks**: 162 (T001-T162)
- **Completed**: 134 tasks
- **Remaining**: 28 tasks
- **New Phases Added** (2026-04-05 via spec sync):
  - Phase 15: US12 Observability (9 tasks) - 9 done
  - Phase 16: US13 Metrics (8 tasks) - 8 done
  - Phase 17: US14 CLI (8 tasks) - 7 done
  - Phase 18: Edge Case Hardening (7 tasks) - 7 done
  - Phase 19: Error Handling & Resilience (25 tasks) - 0 done
