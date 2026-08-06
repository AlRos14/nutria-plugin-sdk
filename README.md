# nutria-plugin SDK

SDK for building, validating, signing, and packaging Nutria plugins.

Release `0.2.0` introduces the typed capability graph and manifest schema
`2.0`. ChatBotNutralia owns reviewable drafts, revisions, and approval; a
plugin only reads channel state and delivers the exact approved snapshot.

This release also supports **declarative admin extensions**, allowing plugins
to expose safe, host-rendered operator views inside ChatBotNutralia.
It also defines **declarative admin flows** for safe, host-rendered operator
workflows such as QR/device-code login without shipping frontend code.

## Install

```bash
uv add nutria-plugin
```

## Quickstart

### 1. Scaffold a new plugin

```bash
nutria-plugin new my-workspace-plugin --name "My Workspace Plugin"
```

This creates:

```
my-workspace-plugin/
  plugin.json          # manifest — edit this
  README.md
  connections/         # one JSON file per connection
  skills/              # SKILL.md files
  context_docs/        # Markdown docs injected into persona prompts
  specs/               # OpenAPI/WSDL specs
  hooks/hooks.json     # declarative hooks
  settings.schema.json # config schema shown in admin UI
```

### 2. Edit plugin.json

```json
{
  "schema_version": "2.0",
  "id": "my-workspace-plugin",
  "name": "My Workspace Plugin",
  "version": "0.1.0",
  "description": "Connects Nutria to My Workspace tool",
  "author": "Your Name",
  "runtime_types": ["declarative_api"],
  "required_secrets": ["API_KEY"],
  "optional_secrets": ["API_REGION"],
  "remote_endpoints": ["https://api.myworkspace.com"],
  "capabilities": [
    {
      "id": "workspace.search",
      "title": "Search workspace",
      "description": "Read matching workspace resources.",
      "effect": "read",
      "tool": "search_workspace",
      "connection_id": "workspace"
    }
  ]
}
```

For customer messages, add a `reviewable_actions` contract and an
`external_write` capability as documented in
[reviewable-actions.md](docs/reviewable-actions.md). Do not create a plugin
draft table or native saved-draft tool.

### 3. Validate

```bash
nutria-plugin validate .
# OK
```

### 4. Pack

```bash
nutria-plugin pack . --output my-workspace-plugin-0.1.0.zip
# Packed: my-workspace-plugin-0.1.0.zip
```

### 5. Sign (optional)

Generate a key pair once:

```bash
nutria-plugin keygen --out my-signing-key
# Private key: my-signing-key.pem
# Public key:  my-signing-key.pub.pem
```

Sign before packing:

```bash
nutria-plugin sign plugin.json --key my-signing-key.pem
nutria-plugin pack . --output my-workspace-plugin-0.1.0.zip
```

Or sign during pack:

```bash
nutria-plugin pack . --key my-signing-key.pem --output my-workspace-plugin-0.1.0.zip
```

Configure the Nutria instance to trust your public key:

```bash
export NUTRIA_PLUGIN_TRUSTED_KEYS='["-----BEGIN PUBLIC KEY-----\n..."]'
```


## Store-Scoped Settings Fields

ChatBotNutralia can render one settings input per loaded store for plugin
fields that declare the host-specific metadata below in `settings.schema.json`:

```json
{
  "store_dir": {
    "type": "object",
    "default": {},
    "additionalProperties": { "type": "string" },
    "x-nutria-store-scoped": true,
    "x-nutria-store-default-key": "default"
  }
}
```

This is intended for plugins whose runtime values differ per store but are still
managed from one shared admin UI. The host stores values as an object like:

```json
{
  "store_dir": {
    "nutrivip": "/app/cache/whatsapp/nutrivip/store",
    "fire": "/app/cache/whatsapp/fire/store",
    "default": "/app/cache/whatsapp/{store}/store"
  }
}
```

Plugins should treat this as a ChatBotNutralia host extension, not generic JSON
Schema behavior.

## Python API

```python
from nutria_plugin import (
    PluginManifest,
    load_plugin_bundle,
    extract_plugin_bundle,
    validate_zip,
    scaffold_plugin,
    pack_plugin,
    validate_plugin_dir,
    generate_keypair,
    sign_manifest,
    verify_manifest,
    SignatureStatus,
)

# Parse a manifest
manifest = PluginManifest.from_file(Path("plugin.json"))

# Load from ZIP bytes
manifest = load_plugin_bundle(zip_bytes)

# Extract to disk
manifest = extract_plugin_bundle(zip_bytes, target_dir)

# Sign and verify
private_pem, public_pem = generate_keypair()
sig = sign_manifest(manifest.model_dump(), private_pem)
status = verify_manifest(manifest.model_dump())
assert status == SignatureStatus.VERIFIED
```

## Plugin ZIP format

| Path | Description |
|------|-------------|
| `plugin.json` | Manifest (required) |
| `README.md` | Human-readable description |
| `connections/*.json` | Connection definitions |
| `skills/<name>/SKILL.md` | Skill instructions |
| `context_docs/*.md` | Docs injected into persona prompts |
| `specs/openapi.json` | OpenAPI spec (for `openapi_bridge` runtime) |
| `specs/service.wsdl` | WSDL spec (for `soap_bridge` runtime) |
| `hooks/hooks.json` | Declarative hooks |
| `settings.schema.json` | JSON Schema for configuration |
| `assets/icon.png` | Plugin icon |

## Admin frontend extensions

Plugins can declare host-rendered admin UI extensions through
`plugin.json -> admin_extensions`.

These extensions are:

- declared in plugin metadata
- rendered by the Nutria host
- safer than shipping arbitrary frontend code

See [docs/admin-extensions.md](docs/admin-extensions.md) for the full contract.

## Admin flows

Plugins can declare host-rendered operator workflows through
`plugin.json -> admin_flows`. Use this for non-secret interactive setup such as
QR pairing, OAuth/device-code login, or phone-code verification.

See [docs/admin-flows.md](docs/admin-flows.md) for the flow contract.

### Security rules

- No executable files (`.py`, `.js`, `.sh`, etc.) allowed in the ZIP.
- No hidden files or directories.
- No absolute paths or path traversal in ZIP entries.
- Maximum bundle size: 20 MB.
- Secrets are **never** stored in the ZIP — they are configured after install.
- Database-backed plugins must bind user/LLM values as SQL parameters. Standard
  `sqlite3` is acceptable for small local state stores when queries are
  centralized and no user input is interpolated into SQL strings.

## Runtime types

| Value | Description |
|-------|-------------|
| `remote_mcp` | Plugin connects to a separately deployed MCP server |
| `declarative_api` | Plugin uses declarative connection JSON files (no server needed) |
| `openapi_bridge` | Nutria auto-generates tools from an OpenAPI/Swagger spec |
| `soap_bridge` | Nutria auto-generates tools from a WSDL/SOAP spec |

## License

MIT
