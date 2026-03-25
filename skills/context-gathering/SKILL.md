# Context Gathering & Repository Analysis Skill

## Purpose

Gather comprehensive technical context from affected repositories to inform architectural planning, including constitution.md guardrails, agents.md workflows, codebase structure, and existing patterns. This ensures plans respect repository constraints and align with existing architecture.

## When to Use

Use this skill when:
- Preparing to generate plan.md for User Stories
- Identifying affected repositories from approved specs
- Responding to feedback requiring deeper repository understanding
- Validating technical feasibility against existing codebase
- Understanding patterns, conventions, and constraints in target repos

## Core Principles

### 1. Constitution.md is Law

Repository constitution.md files define non-negotiable constraints (e.g., "Always use PostgreSQL, never MySQL", "All API endpoints must use JWT authentication"). These are mandatory and violations should block plan generation.

### 2. Read-Only Exploration

Context gathering is investigative, not modificative:
- **DO**: Read files, analyze structure, understand patterns
- **DO NOT**: Modify code, create branches, or make changes
- **Purpose**: Learn what exists to inform what should be built

### 3. Targeted, Not Exhaustive

Don't read the entire codebase. Focus on:
- **Guardrail files**: constitution.md, agents.md
- **Related modules**: Areas spec.md mentions or that plan will touch
- **Key patterns**: How similar features are implemented
- **Integration points**: APIs, schemas, interfaces the plan will interact with

### 4. System Catalog as Starting Point

The System Catalog (if available) maps:
- Repository names and locations
- Primary technologies/languages
- Ownership and contact info
- High-level architecture

Use it to identify which repos to investigate before diving into code.

## Context Gathering Process

### Step 1: Identify Affected Repositories

**From spec.md**:
- Which repos does the spec mention explicitly?
- Which systems/services does the feature interact with?
- What schemas/APIs need modification?

**From System Catalog**:
- What repos own the mentioned services?
- Are there related repos that might be affected?

**Output**: List of 1-5 repositories to investigate

### Step 2: Fetch Guardrail Files

For each affected repository:

1. **constitution.md** (mandatory constraints)
   - Location: Repository root `/constitution.md`
   - Contains: Technology mandates, forbidden patterns, security rules, data governance
   - If missing: Log warning, proceed without repo-specific constraints

2. **agents.md** (AI agent workflows)
   - Location: Repository root `/agents.md`
   - Contains: How AI agents should interact with this repo, special workflows, automation rules
   - If missing: No special agent considerations for this repo

3. **.claude.md / CLAUDE.md** (Claude-specific instructions)
   - Location: Repository root
   - Contains: How Claude Code should work in this repo
   - If present: Note any relevant conventions or workflows

**Method**: Use GitHub API, git clone, or file read tools depending on access

### Step 3: Explore Repository Structure (Read-Only)

**Goal**: Understand existing patterns to maintain consistency

**What to Read**:
1. **README.md**: Project overview, setup instructions, architecture summary
2. **Directory structure**: How is code organized? What's the module layout?
3. **Key configuration files**:
   - `pyproject.toml` / `requirements.txt` / `Pipfile` (Python dependencies)
   - `package.json` (Node.js dependencies)
   - `go.mod` (Go dependencies)
   - `pom.xml` / `build.gradle` (Java dependencies)
4. **Existing similar features**:
   - If spec mentions "webhook endpoint", find existing webhook code
   - If spec mentions "database migration", find existing migrations
   - If spec mentions "API route", find existing route patterns

**Method**:
- Use `Glob` tool to find files matching patterns
- Use `Read` tool to examine specific files
- Use `Grep` tool to search for patterns or references
- Use `Bash` tool for read-only commands (`ls`, `find`, `tree`)
- **Never modify**: This is read-only exploration

### Step 4: Document Patterns and Conventions

For each repository, note:

**Technology Stack**:
- Languages and versions (Python 3.11+, Go 1.21, etc.)
- Frameworks (web framework, Django, Express, etc.)
- Databases (PostgreSQL, Redis, MongoDB, etc.)
- Key libraries and their versions

**Code Organization Patterns**:
- How are modules structured?
- Where do tests live? (e.g., `tests/`, co-located `*_test.py`)
- Where are configs stored? (e.g., `config/`, `env/`)
- What's the import/package naming convention?

**Development Conventions**:
- How are API routes defined? (decorators, routers, controllers)
- How are database models structured? (ORM, schema files)
- How is error handling done? (exceptions, error codes, middleware)
- How are dependencies injected? (DI container, manual, web framework Depends)

**Testing Patterns**:
- Unit test framework (pytest, jest, JUnit, etc.)
- Integration test patterns
- Mocking/stubbing approach
- Test data management

### Step 5: Identify Integration Points

**What to Find**:
- **APIs this repo exposes**: Endpoints, methods, authentication
- **APIs this repo consumes**: External services, internal microservices
- **Databases this repo accesses**: Schema names, table patterns, migrations
- **Message queues**: Topics, exchanges, queue names
- **Shared libraries**: Common utilities other repos depend on

**Why**: Plan must account for these when adding new features

### Step 6: Check for Existing Work

**Search for**:
- Similar features already implemented
- Related tickets or PRs (if accessible)
- TODOs or FIXMEs in relevant areas
- Deprecated patterns to avoid

**Use `Grep` to find**:
- Comments mentioning the feature area
- TODOs related to the work
- References to similar functionality

### Step 7: Synthesize Context Document

**Create a structured summary** to pass to plan generation:

```markdown
# Context: [Repository Name]

## Repository Overview
- **Location**: https://github.com/org/repo
- **Primary Language**: Python 3.11
- **Framework**: web framework 0.110.0
- **Purpose**: Webhook gateway and event processing

## Constitution.md Constraints
- Must use PostgreSQL for persistence (no MySQL, no MongoDB)
- All secrets via environment variables (no hardcoded credentials)
- Python 3.11+ required
- All API endpoints must have HMAC signature validation

## Agents.md Workflows
- Use web framework Depends for dependency injection
- All background tasks use task queue, not BackgroundTasks
- Rate limiting via Redis middleware

## Existing Patterns

### API Route Pattern
```python
@app.post("/api/v1/resource")
async def create_resource(
    payload: ResourceSchema,
    db: Session = Depends(get_db)
):
    # validate, process, return
```

### Database Model Pattern
```python
class Resource(Base):
    __tablename__ = "resources"
    id = Column(UUID, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Testing Pattern
- Unit tests in `tests/unit/`
- Integration tests in `tests/integration/`
- Fixtures in `tests/conftest.py`
- Use pytest with pytest-asyncio

## Integration Points
- **Exposes**: POST /webhooks/jira (receives Jira events)
- **Consumes**: Jira MCP server via langchain-mcp-adapters
- **Database**: PostgreSQL DB "orchestrator" (tables: webhook_events, workflow_state)
- **Message Queue**: Redis (task queue broker)

## Relevant Existing Code
- `api/webhooks.py`: Existing webhook patterns (GitHub, GitLab)
- `middleware/auth.py`: HMAC signature validation implementation
- `db/migrations/`: Database migration examples

## Notes
- Repo recently migrated to web framework 0.110 (use latest patterns)
- Avoid older SQLAlchemy 1.x patterns, use 2.x declarative syntax
- Redis connection pooling already configured in `core/redis.py`
```

## Quality Checklist

Before finishing context gathering, verify:

- [ ] **Constitution.md fetched** for each affected repo (or noted as missing)
- [ ] **Agents.md fetched** for each affected repo (or noted as missing)
- [ ] **Technology stack documented**: Languages, frameworks, databases, key libraries
- [ ] **Code organization understood**: Module structure, testing approach, config locations
- [ ] **Patterns identified**: How similar features are implemented
- [ ] **Integration points mapped**: APIs, databases, message queues, shared libraries
- [ ] **Constraints extracted**: What's forbidden, what's required, what's preferred
- [ ] **Context synthesized**: Structured summary document created for plan generation
- [ ] **Read-only guarantee**: No modifications made to any repository

## Examples

### Good Context Gathering: Webhook Feature in Orchestrator Repo

**Step 1: Identify Repos**
- Spec mentions: "web framework webhook endpoint", "task queue task queue", "Redis locks"
- Affected repos: `your project` (primary), `shared-utils` (if HMAC lib exists)

**Step 2: Fetch Guardrails**
```bash
# GitHub API or git clone
constitution.md found at github.com/org/your project/constitution.md
agents.md found at github.com/org/your project/agents.md
```

**Step 3: Explore Structure**
```bash
# Use Glob tool
your project/
├── api/
│   ├── webhooks.py (existing GitHub webhook patterns)
│   └── routes.py
├── core/
│   ├── redis.py (connection pooling setup)
│   └── celery_app.py (task queue configuration)
├── middleware/
│   └── auth.py (HMAC validation implementation)
├── tests/
│   ├── unit/
│   └── integration/
└── pyproject.toml

# Use Read tool on key files
Read api/webhooks.py → See existing webhook pattern with HMAC validation
Read core/celery_app.py → See task queue broker config (Redis already configured)
Read middleware/auth.py → See reusable HMAC validator
```

**Step 4: Document Patterns**
- API routes use web framework `@app.post()` decorators
- HMAC validation via `auth.validate_hmac()` middleware
- task queue tasks defined in `tasks/` module
- Tests use pytest with `@pytest.mark.asyncio`

**Step 5: Identify Integrations**
- Exposes: Various webhook endpoints (GitHub, GitLab - pattern to follow)
- Consumes: Jira MCP (new integration)
- Database: PostgreSQL "orchestrator" DB (existing)
- Message Queue: Redis (existing, DB 0 for task queue)

**Step 6: Check Existing Work**
```bash
# Use Grep tool
grep -r "jira" → No existing Jira integration (green field)
grep -r "webhook" → Existing patterns in api/webhooks.py to follow
grep -r "TODO.*webhook" → No relevant TODOs
```

**Step 7: Synthesize**
- Create structured context document with all findings
- Include code snippets of patterns to follow
- List constitution.md constraints (PostgreSQL only, env vars for secrets, Python 3.11+)
- Ready to pass to plan generation

### Bad Context Gathering (Anti-Pattern)

❌ **Skipping constitution.md**:
- "I'll just assume PostgreSQL is fine"
- Reality: Constitution might mandate SQLite for this use case

❌ **Reading entire codebase**:
- Spending hours reading every file
- Reality: Only need relevant modules, patterns, and integration points

❌ **Making modifications**:
- "Let me fix this while I'm here"
- Reality: Context gathering is read-only, plan generation is separate step

❌ **Surface-level only**:
- Just reading README.md and stopping
- Reality: Need to understand actual code patterns, not just docs

❌ **Ignoring existing patterns**:
- "I'll design it my way"
- Reality: Must follow existing conventions for consistency

## Handling Private Repositories

If repositories are private:

**Option 1: GitHub API with Auth**
- Use GitHub token from environment variables
- Fetch files via REST API: `GET /repos/:owner/:repo/contents/:path`

**Option 2: Git Clone (if accessible)**
- Clone repo to temporary directory
- Read files locally
- Clean up after context gathering

**Option 3: Request from User**
- If no access available, ask user to provide key files
- Minimize burden: Only request constitution.md, agents.md, and specific modules

When executing :
## Repository Discovery Methods

### Method 1: System Catalog (Preferred)

If System Catalog exists:
```yaml
# system-catalog.yaml
repositories:
  - name: your project
    url: https://github.com/org/your project
    language: Python
    framework: web framework
    owner: platform-team

  - name: shared-utils
    url: https://github.com/org/shared-utils
    language: Python
    framework: N/A
    owner: platform-team
```

Query catalog to find repos by name, technology, or ownership.

### Method 2: Spec Analysis

Extract repo references from spec.md:
- Direct mentions: "in the `your project` repo"
- Service mentions: "webhook gateway service" → lookup service-to-repo mapping
- API mentions: "POST /webhooks/jira" → find repo that owns this path

### Method 3: User Prompt

If ambiguous, ask:
> "Spec mentions webhook processing. Which repository should I examine? (e.g., your project, event-gateway)"

## Constitution.md Structure (What to Look For)

Typical constitution.md sections:

```markdown
# Repository Constitution

## Technology Mandates
- **Database**: PostgreSQL only (version 14+)
- **Python**: 3.11 or higher
- **API Framework**: web framework 0.100+

## Forbidden Patterns
- No MySQL or MongoDB (PostgreSQL mandated)
- No hardcoded credentials (use environment variables)
- No synchronous blocking calls in async routes

## Security Requirements
- All API endpoints require HMAC signature validation
- All secrets stored in environment variables or Vault
- No PII in logs

## Testing Requirements
- 80% code coverage minimum
- All new endpoints have integration tests
- Use pytest for all tests

## Dependencies
- Pin all dependencies in pyproject.toml
- Use Dependabot for updates
- No GPL-licensed dependencies
```

**Extract and enforce** these constraints in plan generation.

## Agents.md Structure (What to Look For)

Typical agents.md sections:

```markdown
# AI Agent Instructions

## Development Workflow
- Use web framework Depends for dependency injection
- All background tasks use task queue (not web framework BackgroundTasks)
- Database sessions via `get_db()` dependency

## Code Style
- Follow Black formatting (line length 100)
- Use type hints on all functions
- Docstrings in Google format

## Testing
- Unit tests in `tests/unit/`
- Integration tests in `tests/integration/`
- Run `pytest` before committing

## Common Patterns
- Webhook validation: `auth.validate_hmac(request, secret)`
- Task queuing: `task_name.delay(arg1, arg2)`
- Error handling: Raise `HTTPException` from `fastapi`
```

**Follow these conventions** when generating plan.md.

## Read-Only Repository Exploration Tools

**Available Tools**:
- `Glob`: Find files matching patterns (`*.py`, `**/test_*.py`, `config/*.yaml`)
- `Read`: Read specific file contents
- `Grep`: Search for text/regex across files (`grep -r "webhook"`, `grep "TODO.*jira"`)
- `Bash` (read-only): `ls`, `cat`, `find`, `head`, `tail`, `tree` (NO modifications)

**Example Exploration Session**:
```bash
# Find all Python files in api module
Glob("your project/api/**/*.py")

# Read existing webhook implementation
Read("your project/api/webhooks.py")

# Search for existing task queue task patterns
Grep("your project", pattern="@celery_app.task")

# Find database models
Glob("your project/db/models/*.py")

# Read model example
Read("your project/db/models/webhook.py")

# List directory structure
Bash("tree -L 3 your project/")
```

## Common Pitfalls to Avoid

1. **Skipping Constitution.md**
   - ❌ "I'll just use what I think is best"
   - ✅ Always fetch and enforce constitution.md constraints

2. **Over-Reading (Analysis Paralysis)**
   - ❌ Reading every file in the repo
   - ✅ Targeted reading: guardrails, related modules, patterns

3. **Making Modifications**
   - ❌ "Let me fix this typo while I'm here"
   - ✅ Read-only exploration, no changes

4. **Ignoring Existing Patterns**
   - ❌ "I'll design this from scratch"
   - ✅ Follow existing conventions for consistency

5. **Not Documenting Findings**
   - ❌ "I read the code, I remember the patterns"
   - ✅ Create structured context document for plan generation

6. **Assuming Repo Structure**
   - ❌ "All web framework projects organize code the same way"
   - ✅ Explore actual structure, don't assume

## Output Format

**Context Gathering Output** (saved to workflow engine state):

```python
{
  "repositories": {
    "your project": {
      "location": "https://github.com/org/your project",
      "constitution": {
        "database": "PostgreSQL 14+",
        "python_version": "3.11+",
        "framework": "web framework 0.110+",
        "forbidden": ["MySQL", "hardcoded credentials", "sync calls in async routes"],
        "security": ["HMAC validation required", "env vars for secrets"]
      },
      "agents_instructions": {
        "di_pattern": "web framework Depends",
        "background_tasks": "task queue (not BackgroundTasks)",
        "testing": "pytest in tests/"
      },
      "tech_stack": {
        "language": "Python 3.11",
        "framework": "web framework 0.110.0",
        "database": "PostgreSQL 15",
        "cache": "Redis 7.0",
        "task_queue": "task queue 5.3.0"
      },
      "patterns": {
        "api_routes": "@app.post decorator pattern",
        "hmac_validation": "middleware/auth.py:validate_hmac()",
        "celery_tasks": "tasks/ module with @celery_app.task",
        "testing": "pytest with @pytest.mark.asyncio"
      },
      "integration_points": {
        "exposes": ["POST /webhooks/github", "POST /webhooks/gitlab"],
        "consumes": ["Jira MCP (new)"],
        "database": "orchestrator DB on PostgreSQL",
        "message_queue": "persistent storage (task queue)"
      }
    }
  }
}
```

This structured output feeds directly into .

## References

- GitHub API for File Access: https://docs.github.com/en/rest/repos/contents
- Constitution.md Best Practices: (internal pattern, no public ref)
- Repository Pattern Discovery: https://martinfowler.com/articles/repository-pattern.html
