# plugin.json — Manifest Reference

The manifest is the single source of truth for plugin identity, runtime
requirements, and security policy. It must be at the root of the plugin
directory as `plugin.json`.

## Complete example

```json
{
  "schema_version": "1.0",
  "id": "my-plugin",
  "name": "My Plugin",
  "version": "0.1.0",
  "description": "Short description of what this plugin does (max 1024 chars).",
  "author": "Acme Corp <dev@acme.com>",
  "runtime_types": ["declarative_api"],
  "default_scope": "store",
  "compatibility": {
    "min_nutria_version": "0.10.0",
    "max_nutria_version": null
  },
  "paths": {
    "connections_dir": "connections",
    "skills_dir": "skills",
    "context_docs_dir": "context_docs",
    "settings_schema": "settings.schema.json",
    "hooks_file": "hooks/hooks.json",
    "specs_dir": "specs",
    "assets_dir": "assets"
  },
  "required_secrets": ["MY_API_KEY", "MY_API_SECRET"],
  "remote_endpoints": ["https://api.myservice.com"],
  "capabilities": ["read", "write"],
  "tags": ["crm", "sales"],
  "homepage": "https://github.com/myorg/my-plugin",
  "license": "MIT",
  "signature": null
}
```

## Field reference

### `schema_version` *(string, required)*

Must be `"1.0"`. Future versions will increment this value.

---

### `id` *(string, required)*

Unique plugin identifier. Used in tool names, secrets namespacing, and install paths.

- Pattern: `^[a-z][a-z0-9\-]*$`
- Max length: 64 characters
- Must be globally unique across all plugins installed in a Nutria instance

Examples: `"trello-workspace"`, `"mrw-shipping"`, `"hubspot-crm"`

---

### `name` *(string, required)*

Human-readable display name shown in the admin UI.

- Min length: 1, Max length: 128

---

### `version` *(string, required)*

Plugin version using semantic versioning.

- Must match semver: `MAJOR.MINOR.PATCH[-prerelease][+build]`
- Examples: `"0.1.0"`, `"1.0.0"`, `"2.0.0-beta.1"`, `"0.0.1-alpha"`

---

### `description` *(string, required)*

Short description of the plugin's purpose.

- Min length: 1, Max length: 1024

---

### `author` *(string, required)*

Publisher name and optional email.

- Max length: 128
- Example: `"Acme Corp <dev@acme.com>"`

---

### `runtime_types` *(array of strings, required)*

One or more runtime modes this plugin uses. At least one value required.

| Value | Description |
|-------|-------------|
| `"declarative_api"` | Declarative REST/HTTP connection files — no server needed |
| `"openapi_bridge"` | Auto-generates tools from an OpenAPI/Swagger spec |
| `"soap_bridge"` | Auto-generates tools from a WSDL/SOAP spec |
| `"remote_mcp"` | Connects to a separately deployed MCP server |

Most plugins use a single runtime type. Plugins that bridge both REST and SOAP
may list two.

---

### `default_scope` *(string, optional)*

Where the plugin is installed by default.

| Value | Description |
|-------|-------------|
| `"platform"` | Available to all stores and all personas |
| `"store"` | Available to all personas in a specific store (default) |
| `"persona"` | Installed for a single persona only |

Default: `"store"`

---

### `compatibility` *(object, optional)*

Version gates evaluated during install.

```json
{
  "min_nutria_version": "0.10.0",
  "max_nutria_version": null
}
```

Both fields use semver and are optional. A `null` value means no constraint.

---

### `paths` *(object, optional)*

Override the default paths for plugin components inside the ZIP. Useful only
if you need a non-standard layout. All paths must be relative and contain
no empty, `.`, or `..` segments.

Defaults:

| Field | Default |
|-------|---------|
| `connections_dir` | `"connections"` |
| `skills_dir` | `"skills"` |
| `context_docs_dir` | `"context_docs"` |
| `settings_schema` | `"settings.schema.json"` |
| `hooks_file` | `"hooks/hooks.json"` |
| `specs_dir` | `"specs"` |
| `assets_dir` | `"assets"` |

---

### `required_secrets` *(array of strings, optional)*

Names of secrets the plugin needs. The Nutria instance will prompt the
admin to configure these after install.

**Rules:**
- Values are names only — never put actual secret values here
- Names are deduplicated and whitespace-stripped automatically
- Secrets are accessed at runtime via the Nutria secrets provider
- Optional secrets should be documented in `settings.schema.json` or `README.md`

Example:
```json
"required_secrets": ["STRIPE_API_KEY", "STRIPE_WEBHOOK_SECRET"]
```

---

### `remote_endpoints` *(array of strings, optional)*

Absolute `http://` or `https://` URLs that the plugin will connect to.
These are validated at install time for SSRF safety.

**Blocked automatically:**
- `localhost` and `localhost.localdomain`
- Loopback addresses (`127.0.0.0/8`, `::1`)
- Private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
- Link-local addresses (`169.254.0.0/16`, `fe80::/10`)
- Reserved IP ranges

Example:
```json
"remote_endpoints": [
  "https://api.stripe.com",
  "https://hooks.stripe.com"
]
```

---

### `capabilities` *(array of strings, optional)*

Free-form capability tags used for discovery and policy enforcement.
Common values: `"read"`, `"write"`, `"notify"`, `"payments"`.

---

### `tags` *(array of strings, optional)*

Discovery tags shown in the plugin marketplace.

Examples: `["crm", "sales"]`, `["shipping", "logistics", "soap"]`

---

### `homepage` *(string, optional)*

URL to the plugin's repository or documentation page.

---

### `license` *(string, optional)*

SPDX license identifier. Examples: `"MIT"`, `"Apache-2.0"`, `"LGPL-3.0"`.

---

### `signature` *(string, optional)*

Hex-encoded ECDSA-P256 DER signature. Set by `nutria-plugin sign` or
`nutria-plugin pack --key`. Do not edit this field manually.

See [security.md](security.md) for details on the signing workflow.

## Validation

```bash
nutria-plugin validate .
```

The SDK validates all constraints above and reports all errors at once.
Validation is also run automatically before packing.

## Forbidden patterns

The following will cause validation errors:
- `id` starting with a digit or containing uppercase letters
- `version` not matching semver
- `required_secrets` containing objects instead of strings
- `remote_endpoints` targeting private/internal addresses
- Any `paths` value that is absolute or contains `..`
- Fields not listed above (extra fields are forbidden — `"extra": "forbid"`)
