# nutria-plugin SDK

SDK for building, validating, signing, and packaging Nutria plugins.

This release also supports **declarative admin extensions**, allowing plugins
to expose safe, host-rendered operator views inside ChatBotNutralia.

## Install

```bash
pip install nutria-plugin
# or with uv
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
  "schema_version": "1.0",
  "id": "my-workspace-plugin",
  "name": "My Workspace Plugin",
  "version": "0.1.0",
  "description": "Connects Nutria to My Workspace tool",
  "author": "Your Name",
  "runtime_types": ["declarative_api"],
  "required_secrets": ["API_KEY"],
  "remote_endpoints": ["https://api.myworkspace.com"]
}
```

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

### Security rules

- No executable files (`.py`, `.js`, `.sh`, etc.) allowed in the ZIP.
- No hidden files or directories.
- No absolute paths or path traversal in ZIP entries.
- Maximum bundle size: 20 MB.
- Secrets are **never** stored in the ZIP — they are configured after install.

## Runtime types

| Value | Description |
|-------|-------------|
| `remote_mcp` | Plugin connects to a separately deployed MCP server |
| `declarative_api` | Plugin uses declarative connection JSON files (no server needed) |
| `openapi_bridge` | Nutria auto-generates tools from an OpenAPI/Swagger spec |
| `soap_bridge` | Nutria auto-generates tools from a WSDL/SOAP spec |

## License

MIT
