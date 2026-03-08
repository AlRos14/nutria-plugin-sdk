# SKILL.md — Format Reference

A skill tells the persona *when* to use a plugin and *how*. Each skill lives
in its own subdirectory under `skills/`:

```
skills/
  my-skill/
    SKILL.md
```

A plugin can contain multiple skills. Each skill should address one coherent
use case.

## File structure

A SKILL.md file has two parts:

```
---
YAML frontmatter
---

Markdown body
```

The frontmatter is parsed by the Nutria runtime and controls activation and
tool access. The markdown body is injected into the persona's system prompt
when the skill is active.

## Frontmatter reference

```yaml
---
name: my-skill                         # required — unique within the plugin
display_name: My Skill                 # required — shown in admin UI
version: 0.1.0                         # required — semver
description: >                         # required — short summary
  What this skill enables the persona to do.
tools_required:                        # required — at least one tool
  - conn_my-plugin--my-api__get_item
  - conn_my-plugin--my-api__search_items
authority_levels:                      # required — one entry per tool
  conn_my-plugin--my-api__get_item: read
  conn_my-plugin--my-api__search_items: read
triggers:                              # optional — natural language phrases
  - "check inventory"
  - "is it in stock"
  - "inventory lookup"
---
```

### `name`

Unique skill identifier within the plugin. Lowercase, hyphens allowed.
Used internally — not shown to end users.

### `display_name`

Human-readable name shown in the Nutria admin UI and approval logs.

### `version`

Semver version of the skill definition itself. Update this when you change
the skill behavior significantly.

### `description`

One or two sentences describing the skill's purpose. Shown in the admin UI.

### `tools_required`

List of tool names the skill may use. Uses the canonical tool name format:

```
conn_<plugin-id>--<connection-id>__<tool-name>
```

The persona will only have access to tools listed here when this skill is active.

### `authority_levels`

Maps each tool to its authority level. This is the declaration — the
connection file specifies the actual constraint, but the skill declares how
it intends to use each tool.

| Level | Behaviour |
|-------|-----------|
| `read` | No approval required |
| `write_internal` | No external approval required |
| `write_external` | Queued for human approval before execution |

### `triggers`

Optional list of natural language phrases that activate this skill. The
persona matches incoming messages against these phrases to decide which
skill is relevant. Phrases are matched loosely — you do not need exact wording.

Tips:
- Include both English and the primary language of your users
- Include domain synonyms (`"waybill"` and `"tracking number"`)
- Keep phrases concise — 2–5 words per phrase

## Body content

The body is injected into the persona's system prompt when the skill is
active. Write it as instructions to the persona, not as documentation for
developers.

### Recommended sections

**Purpose paragraph** — one sentence explaining what the skill does.

**Decision table** — when to use each tool:

```markdown
| User intent          | Tool            | Needs approval |
|----------------------|-----------------|----------------|
| Look up a product    | get_product     | No             |
| Place an order       | create_order    | Yes            |
```

**Parameter guide** — explain non-obvious fields, valid values, formats.

**Error handling** — what to do when a tool returns an error.

**Notes** — edge cases, caveats, format conventions.

### Style rules

- Write in second person ("Use X to do Y", not "The skill uses X")
- Be specific about parameter values — include valid enum values and formats
- Keep the body under ~400 lines — longer prompts degrade LLM attention
- Use tables for reference data (status codes, enum values, date formats)

## Complete example

```markdown
---
name: order-management
display_name: Order Management
version: 0.1.0
description: >
  Create, cancel, and look up customer orders through the Warehouse API.
tools_required:
  - conn_warehouse--api__get_order
  - conn_warehouse--api__create_order
  - conn_warehouse--api__cancel_order
authority_levels:
  conn_warehouse--api__get_order: read
  conn_warehouse--api__create_order: write_external
  conn_warehouse--api__cancel_order: write_external
triggers:
  - "order status"
  - "create order"
  - "cancel order"
  - "order lookup"
  - "where is my order"
---

# Order Management Skill

## Purpose

Look up customer orders, create new orders, and cancel existing ones using
the Warehouse REST API.

## Looking up an order

Use `conn_warehouse--api__get_order` with the order ID. If the customer
gives you an email instead of an ID, ask them to confirm the order ID from
their confirmation email.

## Creating an order

Use `conn_warehouse--api__create_order`. **Requires approval.**

Required fields:
- `customer_id`: customer UUID
- `sku`: product SKU code
- `quantity`: integer, must be > 0
- `delivery_address`: full street address

Confirm all details with the customer before submitting.

## Cancelling an order

Use `conn_warehouse--api__cancel_order`. **Requires approval.**

Only orders with `status: "pending"` or `status: "processing"` can be
cancelled. If the status is `"shipped"`, inform the customer that cancellation
is no longer possible.

## Decision table

| User intent           | Tool          | Needs approval |
|-----------------------|---------------|----------------|
| Check order status    | get_order     | No             |
| Create new order      | create_order  | Yes            |
| Cancel an order       | cancel_order  | Yes            |
```
