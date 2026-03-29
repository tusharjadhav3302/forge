# **LLD: AI-Integrated SDLC Orchestrator**

**Formatted with Gemini. Date: Mar 23, 2026 Status: live/in progress document**

## **Notes**

* The mission statement of this document is to establish a fully integrated, AI-driven development cycle that utilizes webhooks and Human-in-the-Loop (HITL) to ensure seamless flow and rigorous quality control.
* This implementation proposal serves as a conceptual framework. While specific technical details, such as Jira workflows and layouts, are subject to refinement, the core architecture and strategic objectives remain constant.
* This proposal is based on the concept of SDD (Spec Driven Development) and uses ideas from projects like “[spec-kit](https://github.com/github/spec-kit%20)” and others.
* This proposal requires additional configuration of webhooks in GitHub and Jira (+ possible Slack integration) for triggering.
* This workflow is a state machine and should allow opt-in in different stages of the process, TBD on the mechanism.
* MCP and skills should be leveraged to empower agents at every step, leveraging an easy-to-use/change mechanism and avoiding making the orchestrator into a monolith.
* The orchestrator flow is aligned with the agile and scrum process to provide visibility, transparency, and simplify usability.
* The workflow is feature-centric but modular by design, allowing users to initiate the process at any stage to accommodate bugs and alternative workstreams.

## **1\. Technology Stack & Core Components**

* **Orchestrator:** LangGraph (Python) for state management and concurrent routing.
* **Webhook Gateway:** FastAPI for handling inbound events (Jira transitions, CI/CD results, Git reviews).
* **State Persistence:** Redis with LangGraph Checkpointer.
* **Coding Engine and AI Engine:** Claude Code (Anthropic Python SDK)/deep-agents for task execution. With skills and MCP access for Jira creation/planning.
* **Workspace Manager:** Python tempfile and GitPython for ephemeral, isolated code generation environments.
* **Source of Truth:** Jira (REST API & Webhooks) for tracking work, plus the code repositories (constitution.md) for technical guardrails.
* **Agents.md (Localized Context):** Rather than relying purely on global, high-level rules, the orchestrator leverages localized context. Each repository contains an agents.md file
* **Repo-Level Skills:**  If a specific repository requires custom linting, schema compilation, or proprietary deployment checks, those skills are mounted exclusively when the AI operates within that repository's workspace, giving it the exact custom tools a human engineer would use.
* **Traceability tool:** Langfuse, Pythonpython logging.
* **Vault:** For secret management and keeping.

## **2\. The Hierarchical SDD Pipeline**

This design maps Spec-Driven Development documents to a three-level Jira hierarchy, ensuring the AI strictly adheres to the approved scope at every level. **All content is stored in Jira** \- Jira is the single source of truth.

* **The Feature/Initiative Level:** Driven by the **PRD** (Product Requirements Document) and **Spec**.

  * **PRD**: Stored in Jira Feature description field. Focuses on business goals, user personas, and strategic value.
  * **Spec**: Stored in Jira Feature as an attachment. Focuses on user scenarios, acceptance criteria, functional requirements, and success metrics for the entire Feature.


* **The Epic Level:** Driven by **Logical Work Units** and **Plan**.

  * Epics represent cohesive capabilities or system components (e.g., "Payment Gateway Integration", "Checkout UI", "Order Processing")
  * Epic summary \= capability name
  * Epic description \= implementation plan for this capability (architecture, technical approach, dependencies, risks)
  * Each Epic is independently reviewable and deliverable
  * Epics may span multiple repositories if the capability requires cross-repo changes


* **The Task Level:** Driven by **Implementation Details**.

  * Stored in the Jira Task description field
  * Each task includes: overview, scope, implementation steps, acceptance criteria, risks, and **target repository**
  * Tasks are linked to a parent Epic representing the logical capability
  * Tasks are repository-specific for execution purposes

### Key Workflow Principles

1. **Jira as Single Source of Truth**: All content (PRD, Spec, Plan, Tasks) stored exclusively in Jira ticket fields.
2. **PM Ownership of "WHAT"**: Product Manager defines and approves PRD and Spec (business requirements and user scenarios).
3. **SCRUM Team Ownership of "HOW"**: Technical Lead defines and approves Epic breakdown and Plans (implementation architecture organized by logical capabilities).
4. **Spec-Kit as Reference Architecture**: Use spec-kit templates and structure as the blueprint for content quality.
5. **AI-Generated Content**: Skills leverage spec-kit commands to generate content, then store output in Jira.
6. **Cross-Repository Support**: Epics can span multiple repositories; tasks specify the target repo for execution.

### Example Hierarchy

```
Feature: E-commerce Checkout Flow (PROJ-123)
├── Description field: PRD (business goals, user personas, success metrics)
├── Custom field "Spec": Complete specification (user scenarios with Given/When/Then criteria)
│
├── Epic 1: Payment Gateway Integration (PROJ-124)
│   ├── Summary: "Payment Gateway Integration"
│   ├── Description: Plan (architecture for payment processing, Stripe SDK integration, security)
│   ├── Task: Configure Stripe SDK in backend (PROJ-125) [repo: backend-api]
│   │   └── Description: Detailed implementation steps for SDK setup
│   ├── Task: Create payment processing endpoints (PROJ-126) [repo: backend-api]
│   │   └── Description: API design, error handling, validation
│   └── Task: Add payment transaction tables (PROJ-127) [repo: infrastructure]
│       └── Description: Schema design, migration scripts
│
├── Epic 2: Checkout UI Components (PROJ-128)
│   ├── Summary: "Checkout UI Components"
│   ├── Description: Plan (component architecture, state management, form validation)
│   ├── Task: Build checkout form component (PROJ-129) [repo: frontend-web]
│   ├── Task: Implement form validation logic (PROJ-130) [repo: frontend-web]
│   └── Task: Add cart state management (PROJ-131) [repo: frontend-web]
│
└── Epic 3: Order Processing Service (PROJ-132)
    ├── Summary: "Order Processing Service"
    ├── Description: Plan (order workflow, queue integration, notification system)
    ├── Task: Create order service endpoints (PROJ-133) [repo: backend-api]
    ├── Task: Setup order processing queue (PROJ-134) [repo: infrastructure]
    └── Task: Implement order confirmation emails (PROJ-135) [repo: notification-service]
```

## **3\. The Feature Lifecycle: Phase Execution & LangGraph Nodes (updated)**

### **Phase 1: PRD Generation (Feature-Level Business Case)**

This phase captures raw business requirements and refines them into a formal Product Requirements Document.

* **The Trigger:** A Product Manager creates a new Jira Feature ticket, writes their raw thoughts into the description, and transitions the ticket to **"Drafting PRD"**. This fires a webhook to the FastAPI gateway.

* **node\_1\_prd\_generation:** The AI agent:

  1. Reads the raw description from the Jira Feature ticket
  2. Uses MCP tools to research existing documentation or previous tickets
  3. Synthesizes a coherent, structured PRD (using spec-kit PRD template as reference)
  4. Updates the Jira Feature description field with formal PRD
  5. Transitions Feature to **"Pending PRD Approval"**


* **pause\_gate\_prd\_approval (The PRD Feedback Loop):** Execution halts, waiting for PM review.

  * **Revision Path:** PM leaves a Jira comment (e.g., "Include mobile requirements") and transitions back to **"Drafting PRD"**. The webhook routes back to node\_1. AI reads the comment, regenerates PRD, and resubmits.
  * **Happy Path:** PM approves by transitioning to **"Drafting Spec"**.

### **Phase 2: Specification (Feature-Level Acceptance Scenarios)**

Once the PRD is approved, the AI generates the complete behavioral specification.

* **The Trigger:** Feature transitions to **"Drafting Spec"** (PRD approved).

* **node\_2\_spec\_generation:** The AI agent:

  1. Reads the approved PRD from the Jira Feature description
  2. Invokes `/speckit.specify` (or similar) to generate specification content following the spec-kit template:
     - User scenarios with priorities (P1, P2, P3)
     - Given/When/Then acceptance criteria
     - Functional requirements
     - Success criteria
     - Edge cases
  3. Stores generated spec in Jira Feature custom field "Specification" (or attachment)
  4. Transitions Feature to **"Pending Spec Approval"**


* **pause\_gate\_spec\_approval (The Spec Feedback Loop):** Execution halts, waiting for PM review.

  * **Revision Path:** PM reviews spec in Jira custom field, leaves comment (e.g., "Missing GDPR scenario"), transitions back to **"Drafting Spec"**. AI regenerates spec with updates.
  * **Happy Path:** PM approves by transitioning to **"Planning"**.

### **Phase 3: Epic Decomposition & Planning (Immediate Epic Creation)**

Once the "WHAT" (spec) is approved, the AI decomposes the Feature into logical Epics and creates them immediately in Jira. Feedback can happen at two levels: Feature-level (restructure all Epics) or Epic-level (refine individual Epic plan).

* **The Trigger:** Feature transitions to **"Planning"** (spec approved).

* **node\_3\_epic\_decomposition\_and\_planning:** The AI agent:

  1. Reads spec from Jira Feature custom field (complete user scenarios and requirements)
  2. Fetches constitution.md from relevant repositories (technical constraints)
  3. Analyzes spec to identify logical work units (capabilities, system components)
  4. Invokes plan (logical equivalent of `/speckit.plan`) to decompose Feature into 2-5 logical Epics
  5. For each Epic, generate agenerates detailed plan:
     - Architecture overview
     - Technical approach
     - Cross-repository changes
     - Dependencies and risks
  6. **Creates Epic tickets immediately** via Jira MCP:
     - Epic summary \= capability name
     - Epic description \= implementation plan
     - Links to Feature parent
     - Sets Epic status to **"Pending Plan Approval"**
  7. Transitions Feature to **"In Progress"**
  8. Records Epic keys in LangGraph state

**No Feature-level approval gate** \- Epics are created immediately and reviewed individually.

### **Two-Level Feedback Model**

**Level 1: Feature-Level Feedback (Major Restructuring)**

If the Epic decomposition is fundamentally wrong (wrong boundaries, missing capabilities, etc.):

* **Revision Path:**
  * Tech Lead reviews Epic tickets in Jira
  * Leaves comment on Feature: "Split Payment Epic into Gateway \+ Processing. Merge UI Epics."
  * Transitions Feature back to **"Planning".**
  * Webhook triggers node\_3 again
  * AI reads the comment, **deletes old Epic tickets**, regenerates a new Epic breakdown, and creates new Epic tickets
  * Feature transitions to **"In Progress"** again

**Level 2: Epic-Level Feedback (Minor Plan Adjustments)**

If an individual Epic's plan needs tweaking (architecture changes, different approach, etc.):

* **Revision Path:**
  * Tech Lead reviews Epic description (plan)
  * Leaves a comment on Epic: "Use PostgreSQL instead of MySQL for payment tables."
  * Transitions Epic back to **"Planning"** (or keeps in "Pending Plan Approval")
  * Webhook triggers the Epic-specific node
  * AI reads Epic comment, fetches Feature spec, regenerates **just this Epic's plan**
  * Updates Epic description with revised plan
  * Transitions Epic to **"Pending Plan Approval"** again
  * **Other Epics remain unchanged**

**Happy Path:**

* Tech Lead reviews Epics and approves them individually
* Each Epic transitions from "Pending Plan Approval" to **"Ready for Breakdown"**
* Once **all Epics** for Feature are "Ready for Breakdown", Feature transitions to **"Ready for Breakdown"**
* Triggers Phase 4 (Task Generation)

### **Phase 4: Task Generation (Jira Task Creation)**

Once all Epic plans are approved, the AI generates Tasks for each Epic.

* **The Trigger:** Feature transitions to **"Ready for Breakdown"** (all Epics approved).
* **node\_4\_task\_generation:** The AI agent:
  1. Reads all approved Epic tickets for this Feature (status \= "Ready for Breakdown")
  2. **For each Epic, invokes tasks (equivalent of `/speckit.tasks`)** to generate task breakdown:
     - Reads the Epic plan from the Epic description
     - Reads Feature spec for context
     - Generates tasks per Epic
     - Each task includes: overview, scope, implementation steps, acceptance criteria, risks, and **target repository**
     - Creates Jira Task tickets via MCP
     - Task summary \= task title (e.g., "Configure Stripe SDK in backend")
     - Task description \= complete implementation plan for the task
     - Task component/label \= target repository (e.g., "backend-api")
     - Links the taskTask to the parent Epic
  3. Transitions all Epics to **"In Progress"**
  4. Transitions Feature to **"In Development"**

**Artifacts Created (all in Jira):**

- Task tickets (linked to Epics, descriptions contain implementation details, tagged with target repository)
- Epics already exist (created in Phase 3\)

### **Phase 5: Concurrent Execution (AI Implementation)**

The orchestrator can execute work across multiple repositories and phases simultaneously.

* **node\_5\_task\_router:** Groups pending Jira Tasks by their assigned repository and spawns parallel execution threads.

* **node\_6\_workspace\_setup (Parallel):** For each repo, creates an ephemeral directory, clones the repository, and checks out a new feature branch.

* **node\_7\_implementation (Parallel):** Invokes the AI coding engine (e.g., Claude Code SDK) within the workspace.

  * **Guardrails:** AI reads constitution.md and task details from Jira before coding
  * **Action:** AI writes code for assigned tasks, runs tests, commits, pushes the branch, opens Pull Request
  * **Trust but Verify:** AI verifies codebase state matches documentation before implementing

### Cross-Repository Execution

tasks are grouped by target repository:

```
Repository: backend-api → [PROJ-125, PROJ-126, PROJ-133]
Repository: frontend-web → [PROJ-129, PROJ-130, PROJ-131]
Repository: infrastructure → [PROJ-127, PROJ-134]
Repository: notification-service → [PROJ-135]
```

This creates **4 parallel PRs** (one per repository) **with commits for each task**, regardless of which Epic the tasks belong to. Each PR contains all changes for that repository across all Epics.

### **Phase 6: CI/CD Validation, AI Review & Human Review**

* **node\_8\_ci\_cd\_evaluator:** Listens for CI/CD webhooks on opened PRs.

  * **Autonomous Fix Loop:** If tests fail, feeds error logs back to node\_7 to fix (capped at 3-5 retries)
  * **Escalation:** If unfixable after retries, transitions the taskTask to "Blocked" and notifies a human
  * **Happy Path:** Once CI/CD passes, transitions the taskTask to **"Pending AI Review"** and triggers node\_9


* **node\_9\_ai\_code\_reviewer:** AI code review (CodeRabbit-style analysis) runs automatically on the PR.

  * **What it checks:**
    - Code quality issues (complexity, duplication, potential bugs)
    - Security vulnerabilities (SQL injection, XSS, hardcoded secrets)
    - Best practices violations (error handling, logging, naming conventions)
    - Alignment with spec and plan (does code implement what was specified?)
    - Constitution.md compliance (technical constraints, forbidden patterns)
  * **Revision Path:** If AI reviewer finds critical issues:
    - Posts review comments on PR (via GitHub/GitLab API)
    - Feeds comments back to node\_7 (AI implementation)
    - AI fixes issues and pushes new commit
    - Loops back to node\_8 (CI/CD validation)
  * **Happy Path:** If AI review passes (or only minor suggestions), transitions Task to **"In Review"** for human review


* **node\_10\_human\_code\_review (The PR Feedback Loop):** Human engineer performs final review.

  * **Revision Path:** Human reviews PR, requests changes, leaves comments. Webhook routes comments back to node\_7. AI/developer applies fixes, pushes new commit, loops back through CI/CD \+ AI review.
  * **Happy Path:** Human approves and merges PR. Webhook transitions Task to **"Done"**. When all Tasks in Epic are done, Epic transitions to **"Done"**. When all Epics are done, Feature transitions to **"Done"**.

**Note:** AI code reviewer acts as a quality gate before human review, catching obvious issues early and reducing human reviewer burden. It's not a replacement for human review but a supplement that ensures only high-quality code reaches human reviewers.

### **Workflow Summary Diagram**

```
PM creates Feature → node_1_prd_generation → PM approves PRD
                  ↓
            node_2_spec_generation → PM approves Spec (all scenarios in Jira)
                  ↓
     node_3_epic_decomposition_and_planning → Creates Epics immediately (no gate)
                  ↓
          Feature: "In Progress"
          Epics: "Pending Plan Approval"
                  ↓
         ┌────────┴────────┐
         │                 │
    Epic-level         Feature-level
    feedback           feedback (major)
    (minor tweaks)     (restructure)
         │                 │
    Update Epic       Delete + regenerate
    plan only         all Epics
         │                 │
         └────────┬────────┘
                  ↓
    Tech Lead approves all Epics individually → All Epics "Ready for Breakdown"
                  ↓
      node_4_task_generation → Tasks created for all Epics
                  ↓
         node_5_task_router → Group tasks by repository
                  ↓
    node_6_workspace_setup + node_7_implementation → Code written (parallel PRs per repo)
                  ↓
  node_8_ci_cd_evaluator → Tests pass
                  ↓
  node_9_ai_code_reviewer → AI review (quality, security, spec alignment)
                  ↓
  node_10_human_code_review → Human approval & merge → Done
```

### **4\. System Evaluation: Pros, Cons, and Risks**

#### **Pros (The Strategic Advantages)**

* **Unprecedented Predictability:** By enforcing Spec-Driven Development (SDD), the AI is strictly anchored to the spec.md and plan.md. This eliminates the "vibe coding" hallucinations where AI generates code that functionally works but misses the business requirements.
* **Native User Experience:** Humans do not need to learn a new AI dashboard. Product Managers and Tech Leads interact with the AI exactly as they do with human engineers-by dragging Jira tickets and leaving comments.
* **Built-in Guardrails:** The constitution.md acts as a structural firewall. By forcing the AI to read the repo-specific rules before planning or coding, it natively adheres to your company’s security, styling, and architectural standards.
* **Massive Concurrency:** Using LangGraph’s fan-out capabilities, the AI can work on the frontend, backend, and infrastructure repositories simultaneously for a single Jira feature, drastically reducing lead times.

#### **Cons (The Trade-offs)**

* **High Token Cost & Compute:** Generating specs, plans, and task lists before writing any code consumes significantly more LLM tokens than direct code generation.
* **High Pipeline Latency:** This is not an instantaneous system. Waiting for API calls, git cloning, test execution, and multiple AI reasoning loops means a ticket might take 10-20 minutes to move from "Ready for Dev" to "In Review."
* **The "Spec Drift" Vulnerability:** The entire system relies on the spec.md and plan.md being the absolute source of truth. If a human engineer manually edits the repository without updating the Jira spec, the AI will operate on outdated assumptions during its next task, leading to breaking changes. **(Mitigated by the "Trust but Verify" pattern in Phase 5).**

#### **Possible Setbacks & Technical Risks**

* **Legacy Code Blindness:** Claude Code performs exceptionally well in modern, well-structured codebases. If your existing repositories lack tests, have massive monolithic files, or lack clear documentation, the AI will struggle to navigate the workspace, regardless of the constitution.md.
* **Merge Conflict Paralysis:** If human engineers and the AI agent are working on the same files concurrently, the AI may struggle to resolve complex git merge conflicts autonomously, requiring frequent human escalation.
* **Jira Rate Limiting & Webhook Drops:** Relying heavily on Jira APIs means your FastAPI server must gracefully handle Jira API rate limits and network timeouts. If a webhook drops, a LangGraph thread could pause indefinitely.

### **5\. Recommended Implementation Phases**

Building this entire architecture at once is risky. To ensure success, implement the system in a "Crawl, Walk, Run" phased approach. The timeframe assumes major attention from the team to this work effort.

#### **Phase 0: The "Exploratory phase", learning the ropes, identifying edge cases (week 1\)**

* **Goal:** Validate the concepts and the phases, semi-manually identify gaps in the architecture and flow.
* **Implementation:** Verify the process stages manually (no code needed).
* **Outcome:** A list of pitfalls, issues, and changes required to the suggested process and nodes.

#### **Phase 1: The "Planning Only" Shadow Mode (Weeks 2-4)**

* **Goal:** Validate the Spec-Driven Development prompts without touching code.
* **Implementation:** Build the FastAPI webhook receiver and the LangGraph nodes for Phase 1 and Phase 2 (node\_1 through node\_6).
* **Outcome:** The AI listens to Jira, generates spec.md and plan.md, and attaches them. Human engineers read the plans and write the actual code themselves. This allows you to tune the LLM prompts and the constitution.md files until the architecture plans are flawless.
* [Pilot Jira Project](https://redhat.atlassian.net/jira/software/c/projects/AISOS/list)

#### **Phase 2: Single-Repo Execution (Weeks 4-6)**

* **Goal:** Introduce Claude Code execution safely.
* **Implementation:** Build the LangGraph execution nodes (node\_7 through node\_10). Restrict the AI to operate on a single, low-risk repository (a test repo or a fork).
* **Outcome:** The AI takes the approved plan, writes the code, and opens a PR. Humans review the PR heavily. This phase tests the ephemeral workspace setup and Claude's ability to follow the constitution.

\*\*Target phase for 60-day60 days pilot\*\*

#### **Phase 3: The CI/CD Feedback Loop (Weeks 7-8)**

* **Goal:** Enable autonomous self-healing.
* **Implementation:** Connect the GitHub/GitLab webhooks (node\_11 and node\_12). Implement the 3-attempt circuit breaker.
* **Outcome:** When the AI opens a PR and tests fail, it reads the logs and pushes a fix without human intervention.

#### **Phase 4: Multi-Repo Concurrency (Weeks 9+)**

* **Goal:** Full orchestration.
* **Implementation:** Enable the LangGraph Send API to spawn parallel threads for tasks spanning multiple repositories.
* **Outcome:** A single Jira User Story automatically triggers coordinated, parallel PRs across the backend API, frontend web, and infrastructure repositories.

###

### **6\. Workflow Modularity: Adapting to Other SDLC Processes**

The AI Orchestrator is not a rigid, linear pipeline. It is a modular state machine. By inspecting the Jira Issue Type (or another field we can create in the future) in the inbound webhook, the FastAPI router acts as a dispatcher, bypassing unnecessary planning phases and dropping the AI into the specific node required for the job.

#### **A. Bug Fixing (The "Hotfix" Flow)**

Bugs do not require Product Requirements Documents or new architectural plans; they require reproduction, debugging, and resolution.

* **Trigger:** A Jira ticket is created with the type Bug.
* **Entry Point:** Bypasses Phases 1, 2, and 3\. Enters a modified Phase 4 (Execution).
* **The Process:** \* The AI reads the bug description and stack trace from Jira.
  * It clones the relevant repository and reads the [constitution.md](http://constitution.md).
  * It tries to root-cause the issue and identify the reason for it in the code.
  * **Test-First Execution:** Claude Code is prompted to write a failing unit/integration test that reproduces the bug based on the Jira description.
  * Once the test fails, it modifies the application code until the test passes.
  * It pushes the fix, and the standard Phase 6 (CI/CD and Human Review) takes over.

#### **B. Technical Debt & Refactoring**

Refactoring doesn't change the business logic (the Spec), but it heavily changes the structure (the Plan).

* **Trigger:** A Jira ticket is created with the type Tech Debt (or another field set to reflect it).
* **Entry Point:** Bypasses Phases 1 and 2\. Enters directly at Phase 3 (Architecture Planning).
* **The Process:**
  * The AI skips generating a spec.md because the feature already exists.
  * It reads the Jira description outlining the desired refactor (e.g., "Migrate this component from Class to Functional").
  * It generates a refactor\_plan.md outlining the structural changes and files affected.
  * A Tech Lead approves the plan in Jira.
  * The AI breaks the plan into tasks and executes them (Phases 4 and 5).

#### **C. Security Patches & Dependency Updates**

Routine maintenance should be entirely zero-touch for human engineers until the final review.

* **Trigger:** An automated security tool creates a Jira Task/CVE/Bug (with an appropriate field set).
* **Entry Point:** Bypasses all planning phases. Enters directly at Phase 5 (Concurrent Execution).
* **The Process:**
  * The AI agent is given a highly restricted prompt: "Bump the version of library X to version Y. Do not modify any other logic."
  * It updates the package files (e.g., package.json, requirements.txt).
  * It runs the existing test suite locally and makes fixes if required.
  * It opens a PR for human review.

#### **D. Documentation Generation**

Sometimes the code is fine, but the documentation is missing or outdated.

* **Trigger:** A Jira Task tagged with the label Documentation.
* **Entry Point:** Bypasses all coding phases. Uses a dedicated "Doc-Gen" subgraph.
* **The Process:**
  * The AI clones the repository.
  * It reads the source code for a specific module or the entire repo.
  * It generates or updates Markdown files, API specs (like Swagger/OpenAPI), or the constitution.md itself.
  * It opens a PR with only markdown/text file changes.

###

### **7\. Proposed System Architecture**

To transition this orchestrator from a synchronous prototype to a highly scalable, fault-tolerant enterprise system, the production environment relies on an asynchronous, event-driven architecture. This design prevents dropped webhooks, handles massive traffic spikes, and eliminates race conditions when multiple actions occur simultaneously on the same ticket.

#### **A. The API Listener (FastAPI)**

#### This is the internet-facing service responsible for catching webhooks from external systems (Jira, GitHub, Slack). It does no heavy lifting or AI processing.

* **Instant Acknowledgement:** Its primary directive is to accept payloads and return an HTTP 200 OK within milliseconds to prevent external systems from timing out and aggressively retrying.
* **Network De-duplication:** It acts as the first line of defense against network retries. It extracts the unique Webhook Event ID from the incoming request, checks its cache, and instantly drops exact duplicates.
* **Payload Forwarding:** Valid, unique payloads are packaged and pushed immediately into the Message Broker.

#### **B. The Message Broker / Queue (The Buffer & Router)**

The queue decouples the fast ingestion layer from the slower execution layer. It allows the system to scale, taking care of more requests while allowing the decoupled orchestrator to run with multiple instances behind it.

* **Strict FIFO Ordering (Per Ticket):** To prevent race conditions (e.g., processing a "Reject" event before an "Approve" event), the queue must guarantee First-In-First-Out ordering *grouped by the Ticket ID*. All events for PROJ-123 are processed sequentially, never concurrently.

#### **C. The Orchestrator Workers (The State Machine Engine)**

These are the scalable background processes running the actual LangGraph state machine. They pull messages from the queue and execute the specific phases of the SDLC workflow.

* **The "Freshness Check" (Defensive Execution):** Before a worker spends expensive LLM tokens, its first action is an API call to the Source of Truth (Jira) to verify the *current* status. If the queue message says "Approved" but the live Jira ticket says "Needs Revision" (because a human changed their mind while the message was queued), the worker safely discards the stale event and goes back to sleep.
* **Concurrency & Rate Limiting:** The worker pool can be scaled up and down based on queue depth, but is strictly capped by the rate limits of your external dependencies (LLM token-per-minute limits, Jira API limits).

#### **D. The State & Persistence Layer (The Memory)**

Because the orchestrator pauses execution to wait for human-in-the-loop (HITL) feedback, it must persist its exact place in the workflow to disk.

* **State Checkpointing:** A persistent database stores the complete graph state (the current spec, task lists, and retry counts) tied to the Ticket ID. When a worker wakes up via a new webhook, it reloads this exact state from the database.
* **Distributed Locking:** The database layer enforces locks. If a worker is currently processing a state change for a specific ticket, no other worker can load or modify that ticket's state until the first worker finishes.

#### **E. The Ephemeral Execution Workspaces (The Hands)**

When the orchestrator reaches the execution phases, it dynamically provisions secure, isolated environments for the AI to interact with the code.

* **Isolation & Cleanup:** Workspaces are generated on-the-fly (e.g., containerized or temporary local directories) for a specific repo and ticket. Once the code is pushed and the Pull Request is opened, the workspace is destroyed to prevent artifact leakage and save disk space.

###

###

### **8\. Architectural Design Record**

#### **ADR 1: Using a Cyclical State Machine (LangGraph) vs. Linear Pipelines**

* **Context:** Standard automation often relies on Directed Acyclic Graphs (DAGs) or linear CI/CD pipelines (like Jenkins or GitHub Actions).
* **Decision:** I chose LangGraph to model the orchestrator as a cyclical state machine with a persistent Postgres checkpointer.
* **Reasoning:** Software development is inherently cyclical, not linear. CI/CD pipeline failures require autonomous retry loops, and human-in-the-loop (HITL) code reviews require backward routing for revisions. LangGraph natively supports these cycles. Furthermore, its checkpointer allows the orchestrator to pause an execution thread indefinitely while waiting days for a human PM to approve a spec in Jira, and then wake up with its exact memory state intact.

#### **ADR 2: The "Zero-UI" Architecture (Jira as the Sole Interface)**

* **Context:** AI orchestrators often come with custom web dashboards for humans to interact with the agents, approve plans, and view logs.
* **Decision:** We rejected building a custom UI. Jira acts as the absolute Source of Truth and the sole human interaction layer.
* **Reasoning:** Building a new UI creates adoption friction and isolated silos. Product Managers, Tech Leads, and Developers already live in Jira. By mapping LangGraph execution gates directly to native Jira Status transitions and Comments, the AI seamlessly integrates into the exact same workflow used for managing human engineers.

#### **ADR 3: Event-Driven Webhook Ingestion (Message Broker)**

* **Context:** Jira and GitHub send webhooks when events happen. Processing these synchronously means the AI does its thinking while the HTTP request is kept open.
* **Decision:** We placed an asynchronous Message Broker (Queue) behind a blazing-fast FastAPI gateway.
* **Reasoning:** External platforms expect an HTTP 200 OK acknowledgment within seconds, or they will assume failure, drop the webhook, or aggressively retry. A queue decouples the fast ingestion layer from the slow AI execution layer. It protects against LLM rate limits by buffering requests, and prevents database race conditions by ensuring events for the same Jira ticket are processed sequentially (FIFO) rather than concurrently.

#### **ADR 4: The "Trust but Verify" Model vs. 100% Strict SDD**

* **Context:** Pure Spec-Driven Development (SDD) assumes the spec.md is the infallible law, and code is generated strictly from it. However, Red Hat operates in an "upstream-first" open-source model (e.g., openshift-installer, capo). External community members merge code without updating our internal spec.md files.
* **Decision:** We treat SDD artifacts as the *intended outline*, but the codebase as the *absolute truth*.
* **Reasoning:** If we enforce strict SDD, the AI will break upstream code based on outdated internal assumptions (Spec Drift). By injecting a "Trust but Verify" step, the AI is explicitly instructed to read the actual, current state of the codebase before writing code, empowering it to adapt its implementation to reality.

#### **ADR 5: Localized Guardrails (agents.md) & MCP Skills**

* **Context:** The orchestrator needs guardrails to ensure it writes secure, compliant code.
* Decision: We rejected a bloated, global "System Prompt" in favor of repository-level constitution.md/agents.md files and dynamically loaded Model Context Protocol (MCP) skills.
* **Reasoning:** Our portfolio includes diverse projects written in different languages with vastly different CI/CD requirements. Pushing context down to the repository level ensures the Claude agent only loads the exact guardrails and tools needed for the codebase it is currently touching. This saves LLM tokens, reduces hallucinations, and allows the orchestrator to remain a lightweight "traffic cop."

#### **ADR 6: Grouping Concurrency by Repository, Not Task**

* **Context:** A single Jira feature might require 5 backend tasks and 3 frontend tasks. The orchestrator must fan out to execute these quickly.
* **Decision:** Parallel execution threads are grouped by *Repository*, not by individual *Task*.
* **Reasoning:** If we fanned out execution per task, three tasks assigned to openshift-installer would spawn three isolated workspace clones. This would result in three competing Pull Requests or massive Git merge conflicts. Grouping by repository ensures all tasks for a specific codebase are executed sequentially on a single feature branch, producing one clean PR per repo.

#### **ADR 7: Ephemeral Workspaces**

* **Context:** Claude Code needs a local environment to clone code, read files, edit, and run tests.
* **Decision:** Workspaces are generated on-the-fly (e.g., /tmp/story-123/repo\_name/) and completely destroyed after the PR is opened.
* **Reasoning:** Persistent clones suffer from "state rot" (leftover build artifacts, uncommitted files from previous runs). Ephemeral directories guarantee a pristine state for every execution. Additionally, destroying the workspace minimizes the security exposure window for injected Git tokens and API secrets.

#### **ADR 8: Modular Workflow Routing by Issue Type**

* **Context:** Features require rigorous planning, PRDs, and architecture specs. Bugs and dependency updates do not.
* **Decision:** The FastAPI gateway inspects the Jira Issue Type and drops the AI into the specific LangGraph node required for the job, bypassing unnecessary phases.
* **Reasoning:** Forcing a 1-line bug fix through a multi-stage Spec-Driven Development pipeline frustrates engineering teams and wastes expensive LLM compute. Modularity ensures the AI operates with the appropriate level of rigor for the specific task at hand.
