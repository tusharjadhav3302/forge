# Jira Integration & Markup Conversion Skill

## Purpose

Convert between Markdown and Jira markup, structure Jira descriptions for readability, and use Jira API client tools effectively. Ensures all AI-generated content renders correctly in Jira and follows best practices for issue creation and updates.

## When to Use

Use this skill when:
- Creating Jira issues (Features, Epics, Stories, Tasks) via MCP
- Updating Jira issue descriptions with generated content
- Converting Markdown artifacts (PRD, spec, plan) to Jira markup
- Structuring Jira content for maximum readability
- Working with Jira custom fields and issue linking

## Core Principles

### 1. Jira Markup is Not Markdown

Jira uses its own markup syntax that differs from Markdown. Direct copy-paste of Markdown produces broken formatting.

### 2. Readability First

Jira issues are read by humans. Use headers, bullet points, panels, and visual hierarchy for scannable content.

### 3. Use the Right Field for the Right Content

- **Description**: Summary, acceptance criteria, key requirements
- **Comments**: Feedback, questions, status updates, discussions
- **Attachments**: Full specs, plans, diagrams, large documents

### 4. Parent Linking is Critical

Always link child issues to parents:
- Stories → Epic (via `parent` field)
- Epics → Feature (via `parent` field)
- Subtasks → Story (via `parent` field)

## Markdown to Jira Markup Conversion

### Headers

| Markdown | Jira Markup |
|----------|-------------|
| `# H1` | `h1. H1` |
| `## H2` | `h2. H2` |
| `### H3` | `h3. H3` |
| `#### H4` | `h4. H4` |
| `##### H5` | `h5. H5` |
| `###### H6` | `h6. H6` |

**Example**:
```markdown
## Overview
### Background
```

Converts to:
```
h2. Overview
h3. Background
```

### Text Formatting

| Style | Markdown | Jira Markup |
|-------|----------|-------------|
| Bold | `**text**` | `*text*` |
| Italic | `*text*` or `_text_` | `_text_` |
| Bold Italic | `***text***` | `_*text*_` |
| Monospace | `` `code` `` | `{{code}}` |
| Strikethrough | `~~text~~` | `-text-` |
| Underline | N/A | `+text+` |
| Superscript | N/A | `^text^` |
| Subscript | N/A | `~text~` |

**Example**:
```markdown
**Important**: Use `Redis` for caching, not ~~MySQL~~ PostgreSQL.
```

Converts to:
```
*Important*: Use {{Redis}} for caching, not -MySQL- PostgreSQL.
```

### Lists

**Unordered Lists**:
```markdown
- Item 1
- Item 2
  - Nested item
```

Converts to:
```
* Item 1
* Item 2
** Nested item
```

**Ordered Lists**:
```markdown
1. First
2. Second
   1. Nested
```

Converts to:
```
# First
# Second
## Nested
```

### Links

| Markdown | Jira Markup |
|----------|-------------|
| `[text](url)` | `[text\|url]` |
| `[text](url "title")` | `[text\|url]` (no title support) |
| `<url>` | `[url]` |

**Example**:
```markdown
See [documentation](https://example.com) for details.
```

Converts to:
```
See [documentation|https://example.com] for details.
```

### Code Blocks

**Inline Code**: `` `code` `` → `{{code}}`

**Code Blocks**:
```markdown
```python
def hello():
    print("world")
```
```

Converts to:
```
{code:python}
def hello():
    print("world")
{code}
```

**No Language Specified**:
```markdown
```
plain text
```
```

Converts to:
```
{code}
plain text
{code}
```

### Blockquotes

```markdown
> This is a quote
> Multiple lines
```

Converts to:
```
{quote}
This is a quote
Multiple lines
{quote}
```

### Tables

| Markdown | Jira Markup |
|----------|-------------|
| `| Header 1 | Header 2 |` | `\|\| Header 1 \|\| Header 2 \|\|` |
| `| Cell 1 | Cell 2 |` | `\| Cell 1 \| Cell 2 \|` |

**Example**:
```markdown
| Name | Type |
|------|------|
| Redis | Cache |
| PostgreSQL | Database |
```

Converts to:
```
|| Name || Type ||
| Redis | Cache |
| PostgreSQL | Database |
```

### Horizontal Rules

```markdown
---
```

Converts to:
```
----
```

## Jira-Specific Markup (Not in Markdown)

### Panels

```
{panel:title=Important Note}
This content appears in a highlighted panel.
{panel}
```

**Use for**: Callouts, warnings, important information

### Info/Warning/Note Boxes

```
{info}
This is informational content.
{info}

{warning}
This is a warning.
{warning}

{note}
This is a note.
{note}
```

### Collapsible Sections

```
{expand:title=Click to see details}
Hidden content that expands when clicked.
{expand}
```

**Use for**: Long content, optional details, implementation notes

### Colors

```
{color:red}This is red text{color}
{color:blue}This is blue text{color}
```

## Structuring Jira Descriptions

### Template for User Stories

```
As a [role]
I want [capability]
So that [business value]

h2. Acceptance Criteria

h3. Scenario: [Descriptive name]

*Given* [context]
*When* [action]
*Then* [observable outcome]

h3. Scenario: [Another scenario]

*Given* [different context]
*When* [action]
*Then* [different outcome]

h2. Edge Cases

* [Edge case 1]
* [Edge case 2]

h2. Definition of Done

* All acceptance criteria pass
* Edge cases handled
* Tests written and passing
* Code reviewed and merged

h2. Technical Notes

[Any technical details, patterns to follow, constraints]
```

### Template for Epics

```
h1. [Epic Name]

h2. Scope

h3. What's Included
* [Capability 1]
* [Capability 2]

h3. What's Excluded (Out of Scope)
* [Related but separate capability]
* [Future enhancement]

h2. Business Value

[Why this Epic matters - 2-3 sentences]

h2. Technical Approach (High-Level)

[Brief overview of implementation approach]

h2. Dependencies

* *Depends on*: [Other Epics that must complete first]
* *Blocks*: [Other Epics that wait on this]

h2. Success Criteria

* [Measurable outcome 1]
* [Measurable outcome 2]
```

### Template for Plans (Attachments Preferred)

For large plans (>5KB), use attachments instead of descriptions:

1. Generate plan.md in Markdown
2. Attach as file to Jira issue
3. In description, add summary:

```
h2. Implementation Plan

See attached {{plan.md}} for full implementation plan.

h3. Quick Summary

* *Affected Repos*: your orchestrator, shared-utils
* *Key Changes*: FastAPI webhook endpoints, Redis state persistence
* *Estimated Effort*: 3-4 weeks
* *Risks*: Redis single point of failure (mitigation: persistence enabled)

[Full details in attachment]
```

## Using Jira API client Tools

### Creating Issues

**Epic Example**:
```python
jira_mcp.create_issue(
    project_key="PROJ",
    summary="Webhook Gateway & Event Router",
    issue_type="Epic",
    description="""
h2. Scope

h3. What's Included
* FastAPI webhook endpoints
* HMAC signature validation
* Redis event deduplication
* Celery task publishing

h3. What's Excluded
* Webhook retry logic (handled by Celery)
* Multiple webhook sources (Jira only for Phase 1)

h2. Business Value

Reliably receive and route Jira events to orchestrator workflows, enabling AI-driven SDLC automation.
""",
    additional_fields={
        "parent": "TICKET-ID"  # Link to Feature
    }
)
```

**Story Example**:
```python
jira_mcp.create_issue(
    project_key="PROJ",
    summary="FastAPI Webhook Endpoints",
    issue_type="Story",
    description="""
As a system integrator
I want webhook endpoints that receive Jira events
So that external systems can trigger orchestrator workflows

h2. Acceptance Criteria

h3. Scenario: Jira status transition webhook

*Given* Jira webhook configured for PROJ project
*When* ticket status changes (e.g., "Pending PRD Approval" → "Drafting PRD")
*Then* POST /webhooks/jira receives event, validates HMAC, returns 200 OK within 100ms

h3. Scenario: Invalid payload

*Given* an invalid payload or signature
*When* webhook is called
*Then* return 400 Bad Request with validation errors

h2. Technical Notes

FastAPI + Pydantic validation, async handlers, HMAC signature validation for security
""",
    additional_fields={
        "parent": "TICKET-ID"  # Link to Epic
    }
)
```

### Updating Issues

```python
# Update description
jira_mcp.update_issue(
    issue_key="TICKET-ID",
    fields={
        "description": updated_description_in_jira_markup
    }
)

# Transition status
jira_mcp.transition_issue(
    issue_key="TICKET-ID",
    transition="In Progress"
)
```

### Adding Comments

```python
jira_mcp.add_comment(
    issue_key="TICKET-ID",
    comment="""
Thanks for the feedback! To address your concerns, could you specify:

* Which security aspects need more detail?
* Are there specific standards to follow (OWASP, SOC 2)?

I'll revise once I understand the focus areas.
"""
)
```

### Parent Linking Patterns

**Feature → Epic → Story** hierarchy:

```python
# Create Feature (no parent)
feature = jira_mcp.create_issue(
    project_key="PROJ",
    summary="AI-Generated PRDs",
    issue_type="Feature",
    description="..."
)
# Returns: {"key": "TICKET-ID"}

# Create Epic under Feature
epic = jira_mcp.create_issue(
    project_key="PROJ",
    summary="Webhook Gateway",
    issue_type="Epic",
    description="...",
    additional_fields={"parent": "TICKET-ID"}  # Link to Feature
)
# Returns: {"key": "TICKET-ID"}

# Create Story under Epic
story = jira_mcp.create_issue(
    project_key="PROJ",
    summary="FastAPI Webhook Endpoints",
    issue_type="Story",
    description="...",
    additional_fields={"parent": "TICKET-ID"}  # Link to Epic
)
# Returns: {"key": "TICKET-ID"}
```

## Handling Large Descriptions

### Jira Description Limits

- **Soft limit**: ~32KB (32,768 characters)
- **Hard limit**: Varies by Jira Cloud vs Server
- **Best practice**: Keep descriptions < 10KB

### Strategies for Large Content

**Option 1: Attachments**
```python
# Generate plan.md file
plan_content = generate_plan(...)
write_file("plan.md", plan_content)

# Create issue with summary description
jira_mcp.create_issue(
    project_key="PROJ",
    summary="Implementation Plan",
    issue_type="Story",
    description="See attached plan.md for full details.\n\nh2. Summary\n..."
)

# Attach file
jira_mcp.upload_attachment(
    issue_key="TICKET-ID",
    file_path="plan.md"
)
```

**Option 2: Collapsible Sections**
```
h2. Implementation Plan

{expand:title=Click to see full plan}
[Large content here]
{expand}
```

**Option 3: External Links**
```
h2. Implementation Plan

Full plan available: [Google Doc|https://docs.google.com/...]

h2. Summary
[Key points only]
```

## Conversion Utilities

### Python Conversion Function

```python
import re

def markdown_to_jira(markdown: str) -> str:
    """Convert Markdown to Jira markup."""
    text = markdown

    # Headers
    text = re.sub(r'^######\s+(.+)$', r'h6. \1', text, flags=re.MULTILINE)
    text = re.sub(r'^#####\s+(.+)$', r'h5. \1', text, flags=re.MULTILINE)
    text = re.sub(r'^####\s+(.+)$', r'h4. \1', text, flags=re.MULTILINE)
    text = re.sub(r'^###\s+(.+)$', r'h3. \1', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.+)$', r'h2. \1', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s+(.+)$', r'h1. \1', text, flags=re.MULTILINE)

    # Code blocks with language
    text = re.sub(r'```(\w+)\n(.*?)\n```', r'{code:\1}\n\2\n{code}', text, flags=re.DOTALL)
    # Code blocks without language
    text = re.sub(r'```\n(.*?)\n```', r'{code}\n\1\n{code}', text, flags=re.DOTALL)

    # Inline code
    text = re.sub(r'`([^`]+)`', r'{{\1}}', text)

    # Bold (** or __)
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    text = re.sub(r'__(.+?)__', r'*\1*', text)

    # Italic (* or _) - careful not to conflict with bold or lists
    text = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'_\1_', text)

    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'[\1|\2]', text)

    # Unordered lists
    text = re.sub(r'^- ', '* ', text, flags=re.MULTILINE)
    text = re.sub(r'^  - ', '** ', text, flags=re.MULTILINE)
    text = re.sub(r'^    - ', '*** ', text, flags=re.MULTILINE)

    # Ordered lists
    text = re.sub(r'^\d+\. ', '# ', text, flags=re.MULTILINE)

    # Blockquotes
    text = re.sub(r'^> (.+)$', r'{quote}\n\1\n{quote}', text, flags=re.MULTILINE)

    # Horizontal rules
    text = re.sub(r'^---+$', '----', text, flags=re.MULTILINE)

    return text
```

**Note**: This is a basic converter. Complex Markdown (nested structures, tables) may need manual adjustment.

## Common Pitfalls to Avoid

1. **Using Markdown Directly in Jira**
   - ❌ Copy-paste Markdown → Broken formatting
   - ✅ Convert to Jira markup first

2. **Forgetting Parent Links**
   - ❌ Creating Stories without Epic parent
   - ✅ Always set `additional_fields={"parent": "EPIC-KEY"}`

3. **Exceeding Description Limits**
   - ❌ 50KB description → Jira error
   - ✅ Use attachments for large content

4. **Poor Visual Hierarchy**
   - ❌ Wall of text, no headers, no bullets
   - ✅ Use h2/h3, bullet points, panels

5. **Mixing Bot and Human Comments**
   - ❌ AI responding to its own comments
   - ✅ Filter comments by author

6. **Wrong Field for Content**
   - ❌ Full plan in description
   - ✅ Summary in description, plan as attachment

## Quality Checklist

Before creating/updating Jira issues:

- [ ] **Markup converted**: Markdown → Jira markup
- [ ] **Headers used**: h2 for major sections, h3 for subsections
- [ ] **Bullet points**: Lists formatted correctly (* for unordered, # for ordered)
- [ ] **Code blocks**: Language specified where applicable
- [ ] **Parent linked**: Epic/Story has parent field set
- [ ] **Description length**: < 10KB (use attachments if larger)
- [ ] **Visual hierarchy**: Scannable, not wall of text
- [ ] **No formatting errors**: Preview in Jira to verify rendering

## References

- Jira Text Formatting Notation: https://jira.atlassian.com/secure/WikiRendererHelpAction.jspa
- Jira Cloud REST API: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- MCP Atlassian Server: https://github.com/modelcontextprotocol/servers/tree/main/src/atlassian
