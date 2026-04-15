# Declarative Admin Extensions

Nutria plugins can now extend the ChatBotNutralia admin frontend through a
**host-rendered declarative contract**.

This model is intentionally different from shipping arbitrary frontend code:

- the plugin declares **what** should be rendered
- the Nutria host decides **how** to render it
- the admin UI stays consistent with the host's permissions, styling, and data handling

## Why this model exists

The goal is to let plugins expose operator-facing screens such as:

- audit tables
- investigation views
- operational dashboards
- plugin-specific admin records

without adding the security and compatibility burden of loading plugin-owned
JavaScript inside the admin SPA.

## Manifest field

Plugins declare admin extensions in `plugin.json` through `admin_extensions`.

```json
{
  "id": "nutria-email",
  "name": "Nutria Email",
  "version": "0.3.0",
  "runtime_types": ["remote_mcp"],
  "admin_extensions": [
    {
      "id": "email-audit",
      "title": "Email Audit",
      "description": "Inspect outbound emails sent by the plugin.",
      "placement": "plugins.detail",
      "kind": "table",
      "schema_path": "assets/admin/email-audit.json"
    }
  ]
}
```

## Supported values

### `placement`

Current supported placement:

- `plugins.detail` — render the extension inside the existing Plugins admin page

### `kind`

Current supported kind:

- `table` — a host-rendered table with filters and per-record detail views

## Schema file

The schema referenced by `schema_path` must be a JSON file inside the plugin
bundle. For a table extension, the host currently expects a shape like:

```json
{
  "type": "table",
  "resource": "sent_emails",
  "columns": [
    { "key": "sent_at", "label": "Sent", "format": "datetime" },
    { "key": "subject", "label": "Subject" },
    { "key": "status", "label": "Status", "format": "badge" }
  ],
  "detail_fields": [
    { "key": "body_plain", "label": "Plain body", "format": "pre" },
    { "key": "metadata", "label": "Metadata", "format": "json" }
  ],
  "filters": [
    { "key": "q", "label": "Search", "type": "search" },
    { "key": "status", "label": "Status", "type": "select", "options": ["sent", "failed"] }
  ],
  "default_page_size": 25,
  "empty_message": "No records found."
}
```

## Packaging guidance

Recommended layout:

```text
my-plugin/
  plugin.json
  assets/
    admin/
      my-extension.json
```

Key rules:

- `schema_path` must be **relative**
- `schema_path` must point to a **JSON** file
- the host owns the rendering logic
- the plugin should expose data through approved backend/runtime paths, not by
  embedding executable web assets

## First production use case

The first plugin using this contract is `nutria-email`, which declares an
`email-audit` extension rendered inside the Plugins section of ChatBotNutralia.

That extension lets operators inspect outbound email records without direct
filesystem or SQLite access.
