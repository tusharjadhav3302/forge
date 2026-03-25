# Research & Discovery Skill

## Purpose

Systematically find and leverage relevant context before generating artifacts. This skill prevents hallucinations, improves quality, and ensures AI agents build on existing knowledge rather than inventing from scratch.

## When to Use

Use this skill when:
- Starting PRD generation (node_1) - research similar features, domain patterns
- Starting spec generation (node_4) - find related specs, implementation patterns
- Starting plan generation (node_6) - discover existing repos, constitution.md, patterns
- Validating references - ensure mentioned repos/services/APIs actually exist
- Responding to feedback - find examples of what was requested

## Core Principles

### 1. Search Before You Create

Never generate from a blank slate. Always research:
- What similar work has been done?
- What existing systems/services are relevant?
- What patterns have worked before?
- What constraints apply?

### 2. System Catalog is Ground Truth

For repos, services, APIs - if it's not in the System Catalog, it may not exist. Validate every reference.

### 3. Recent Work > Old Work

Prioritize patterns from recent tickets (last 3-6 months). Old tickets may reference deprecated approaches.

### 4. Conservative > Confident

If you're unsure whether something exists:
- **Don't invent it** - Hallucinations waste human review time
- **Ask the user** - Or omit the uncertain reference
- **Search more** - Try different keywords

## Research Process

### Step 1: Understand the Domain

**Read the source material**:
- Feature request description
- Epic requirements
- Story spec
- Any attached documents

**Extract keywords**:
- Technical terms: "webhook", "authentication", "Redis"
- Domain concepts: "password reset", "notification", "report"
- System mentions: "user-service", "email gateway"

**Identify question categories**:
- What capabilities exist? (System Catalog search)
- What's been built before? (Jira ticket search)
- What constraints apply? (Constitution.md from repos)

### Step 2: System Catalog Search

**When**: Always, for any repo/service/API mention

**How**:
1. Search by keyword: "webhook", "email", "auth"
2. Filter by type: services, libraries, infrastructure
3. Read descriptions and capabilities
4. Note dependencies and integrations

**Example**:
```yaml
# Search: "authentication"
# Results:
- name: auth-service
  description: Handles user authentication, JWT tokens
  capabilities: [login, logout, token-refresh, password-reset]
  tech_stack: Python, web framework, PostgreSQL
  owner: platform-team

- name: session-manager
  description: Manages user sessions, SSO integration
  capabilities: [session-tracking, sso, multi-factor-auth]
  tech_stack: Node.js, Redis
  owner: identity-team
```

**Use cases**:
- Validate mentioned services exist
- Find related services you should mention
- Understand which service owns which capability

### Step 3: Jira Ticket Search (JQL)

**When**: Looking for similar past work, patterns, learnings

**Search Patterns**:

**By keyword**:
```jql
project = PROJ AND summary ~ "webhook"
project = PROJ AND description ~ "password reset"
```

**By status (completed work)**:
```jql
project = PROJ AND status = Done AND created >= -90d
project = PROJ AND status IN (Done, Closed) AND resolved >= -180d
```

**By Epic (related Stories)**:
```jql
project = PROJ AND "Epic Link" = TICKET-ID
parent = TICKET-ID
```

**By labels**:
```jql
project = PROJ AND labels IN (authentication, security)
```

**Complex queries**:
```jql
project = PROJ AND (summary ~ "webhook" OR description ~ "event processing") AND status = Done
```

**What to extract from found tickets**:
- Implementation patterns (how was it done?)
- Success metrics (what worked?)
- Gotchas (what didn't work?)
- Related repos/services (what integrated with what?)
- Reusable components (libraries, utilities)

**Example**:
```
Search: "password reset"
Found: TICKET-ID "Two-Factor Authentication"

Key Learnings:
- Used email-service for sending verification codes
- Auth-service handles password hashing (bcrypt)
- Audit logging required (compliance requirement)
- Average implementation time: 2 weeks

Pattern to Reuse:
- Email verification flow from auth-service
- Audit logging pattern
```

### Step 4: Constitution.md Discovery

**When**: Planning implementation (node_5, node_6)

**What to look for**:
- Technology mandates (must use X, cannot use Y)
- Security requirements (all endpoints need auth)
- Testing standards (80% coverage minimum)
- Code organization patterns (module structure)

**Where to find**:
- Repository root: `/constitution.md`
- Docs folder: `/docs/constitution.md`
- GitHub folder: `/.github/constitution.md`

**Parsing strategy**:
```markdown
# Constitution.md for auth-service

## Technology Mandates
- **Database**: PostgreSQL only (no MySQL, no MongoDB)
- **Python**: 3.11 or higher
- **Password Hashing**: bcrypt with cost factor 12

## Forbidden Patterns
- No plaintext passwords in logs
- No SQL queries via string concatenation
- No hardcoded credentials

## Security Requirements
- All endpoints require JWT authentication
- Rate limiting: 10 req/min per user
- Audit logging for all password operations
```

**Extract relevant rules**:
- If spec mentions database → extract database rules
- If spec mentions authentication → extract auth rules
- If spec mentions API endpoints → extract API rules

### Step 5: Related Documentation

**Internal docs**:
- Confluence pages (if accessible)
- README.md in relevant repos
- Architecture Decision Records (ADRs)

**External docs**:
- API documentation (OpenAPI/Swagger)
- Library documentation (for dependencies)
- Framework best practices

**What to extract**:
- How to use existing services
- Integration patterns
- Common pitfalls
- Best practices

### Step 6: Pattern Recognition

**Identify successful patterns**:
- What approach was used for similar features?
- Which services/libraries were chosen?
- How was testing structured?
- What deployment strategy worked?

**Identify anti-patterns**:
- What failed in past tickets?
- What was deprecated or replaced?
- What caused bugs or delays?

**Document for reuse**:
```markdown
# Patterns: Webhook Implementation

## Successful Pattern (from TICKET-ID)
- web framework for endpoints
- HMAC signature validation (shared-utils/auth.py)
- Redis for deduplication (5-minute TTL)
- task queue for async processing

## Tried and Failed (from TICKET-ID)
- Flask webhooks → Too slow, switched to web framework
- In-memory deduplication → Lost on restart, switched to Redis
```

### Step 7: Validation

**Before using any reference**:

1. **Repo exists?**
   - Search System Catalog
   - If not found → Don't mention it

2. **Service exists?**
   - Search System Catalog
   - Verify capability matches need
   - If uncertain → Ask user

3. **API exists?**
   - Check service documentation
   - Verify endpoint/method
   - If uncertain → Mark as "needs verification"

4. **Pattern still valid?**
   - Check if recent (< 6 months)
   - Verify not deprecated
   - If old → Search for newer approach

## Research Outputs

### For PRD Generation (node_1)

**Research deliverable**:
```markdown
# Research Summary: Password Reset Feature

## Related Work
- TICKET-ID: Two-Factor Authentication (Done, 2026-02)
  - Used email-service for verification
  - Audit logging pattern reusable

## Relevant Services (System Catalog)
- auth-service: Handles password operations
- email-service: Sends verification emails
- audit-logger: Compliance logging

## Constitution.md Constraints
- auth-service: bcrypt for hashing, audit all password ops
- email-service: Rate limit 100/min per user

## Patterns to Reuse
- Email verification flow
- Audit logging pattern
- Error handling for failed emails

## References Validated
✓ auth-service exists in System Catalog
✓ email-service exists in System Catalog
✓ audit-logger exists in System Catalog
```

### For Spec Generation (node_4)

**Research deliverable**:
```markdown
# Research Summary: Webhook Endpoint Story

## Similar Specs
- TICKET-ID: GitHub Webhook Handler
  - Had 5 acceptance criteria (good template)
  - Edge cases: duplicate events, malformed payloads

## Related Stories in Epic
- TICKET-ID: Redis Deduplication
  - Depends on this story (webhook must extract event IDs)

## Technical Patterns
- HMAC validation in shared-utils/auth.py
- web framework async endpoint pattern from auth-service

## Validation
✓ shared-utils repo exists
✓ auth.py module exists (has validate_hmac function)
```

### For Plan Generation (node_6)

**Research deliverable**:
```markdown
# Research Summary: Webhook Implementation Plan

## Affected Repos (System Catalog)
- your project: Main repo for orchestration logic
- shared-utils: Contains auth helpers

## Constitution.md Rules
- your project:
  * Must use PostgreSQL for persistence
  * Python 3.11+ required
  * web framework 0.110+ for APIs
- shared-utils:
  * Read-only (no modifications without approval)

## Existing Code Patterns
- api/webhooks.py: GitHub webhook example (HMAC validation)
- core/redis.py: Redis connection pool setup
- middleware/auth.py: Reusable HMAC validator

## Integration Points
- Redis (existing): DB 0 for task queue, DB 2 for dedup
- PostgreSQL (existing): orchestrator database
- Jira MCP (new integration): via langchain-mcp-adapters

## Validation
✓ All repos exist in System Catalog
✓ Constitution.md files fetched
✓ Referenced code files exist in repos
```

## Hallucination Prevention Checklist

Before generating any artifact, verify:

- [ ] **All repos mentioned** → Exist in System Catalog
- [ ] **All services mentioned** → Exist in System Catalog
- [ ] **All APIs mentioned** → Documented or verified with user
- [ ] **All libraries mentioned** → Listed in repo dependencies or standard libraries
- [ ] **All patterns mentioned** → From recent tickets or docs, not invented
- [ ] **All metrics mentioned** → Based on existing SLAs or industry standards
- [ ] **All tickets referenced** → Actually exist in Jira

**If uncertain about ANY reference → Ask user or omit**

## Research Strategies by Domain

### Authentication/Authorization

**Search for**:
- System Catalog: "auth", "authentication", "authorization", "identity"
- Jira: `summary ~ "auth OR login OR password"`
- Constitution.md: Security requirements, password policies

**Common services**:
- auth-service, identity-service, session-manager
- SSO providers (Okta, Auth0)
- JWT libraries

### Data Processing/ETL

**Search for**:
- System Catalog: "data", "pipeline", "etl", "processing"
- Jira: `summary ~ "data processing OR pipeline OR batch"`
- Constitution.md: Data governance, retention policies

**Common services**:
- data-pipeline, batch-processor, stream-processor
- Airflow, Kafka, Spark

### Notifications

**Search for**:
- System Catalog: "email", "notification", "alert", "sms"
- Jira: `summary ~ "notification OR email OR alert"`
- Constitution.md: Rate limiting, templates

**Common services**:
- email-service, notification-service, sms-gateway
- SendGrid, Twilio, SNS

### API/Webhook Integrations

**Search for**:
- System Catalog: "webhook", "api", "integration", "gateway"
- Jira: `summary ~ "webhook OR api integration"`
- Constitution.md: Authentication, rate limiting, retry logic

**Common services**:
- api-gateway, webhook-handler, integration-service
- Kong, Nginx, Envoy

## When to Ask vs When to Search

### Ask the User When:

- **Ambiguous requirements**: "Should this support OAuth or just JWT?"
- **Business decisions**: "What's the priority: speed or security?"
- **Missing context**: "Which team owns the user-service?"
- **New capabilities**: "Should we build this or use external service?"

### Search First When:

- **Technical patterns**: "How do we handle webhooks?"
- **Existing services**: "What email service do we use?"
- **Code conventions**: "What testing framework is standard?"
- **Past decisions**: "Why did we choose Redis over Memcached?"

### Neither When:

- **Industry standards**: "How does OAuth 2.0 work?" → Use general knowledge
- **Framework docs**: "How to use web framework dependencies?" → Official docs
- **Common patterns**: "How to structure REST APIs?" → General best practices

## Common Research Mistakes

1. **Not Searching at All**
   - ❌ "I'll just design this from scratch"
   - ✅ Search for similar work first

2. **Trusting First Result**
   - ❌ One ticket found → Assume that's the pattern
   - ✅ Review 3-5 tickets, find common patterns

3. **Ignoring Recency**
   - ❌ Ticket from 2020 → "This is how we do it"
   - ✅ Prioritize recent work (last 6 months)

4. **Over-Relying on Search**
   - ❌ Searching for 2 hours for a 5-minute user question
   - ✅ Search 10-15 minutes, then ask if unclear

5. **Not Validating References**
   - ❌ Mention "password-manager-service" without checking
   - ✅ Validate every service/repo in System Catalog

6. **Hallucinating "Standard" Services**
   - ❌ "Use the standard notification-service" (doesn't exist)
   - ✅ Search System Catalog, use actual service names

### In  (PRD)
```python
def (state):
    ticket = get_ticket(state["ticket_id"])
    # Research phase
    research = {
        "system_catalog": search_catalog(extract_keywords(ticket.description)),
        "related_tickets": search_jira(extract_keywords(ticket.description)),
        "patterns": identify_patterns(related_tickets),
        "validation": validate_references(research)
    }
    # Generate PRD with research context
    prd = generate_prd(ticket.description, research_context=research)
    # Ensure no hallucinations
    validate_prd_references(prd, research["system_catalog"])
    return state
```
### In 
```python
def (state):
    spec = state["spec"]
    # Research affected repos
    keywords = extract_technical_keywords(spec)
    repos = search_catalog(keywords, filter="repositories")
    # Fetch constitution.md from each repo
    constitutions = {}
    for repo in repos:
        const = fetch_file(repo, "constitution.md")
        if const:
            constitutions[repo.name] = parse_constitution(const)
    # Save research to state
    state["repos"] = repos
    state["constitutions"] = constitutions
    return state
```
## References

- Jira JQL Reference: https://support.atlassian.com/jira-service-management-cloud/docs/use-advanced-search-with-jira-query-language-jql/
- System Catalog Best Practices: (internal)
- Research-Driven Development: https://martinfowler.com/articles/research-driven-development.html
