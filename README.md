# nutria-plugin SDK

SDK for building, validating, signing, and packaging Nutria plugins.

Release `0.4.0` accepts only manifest schema `4.0`. Capabilities use their real
business effect (`read`, `write`, or `external_write`); preparation is expressed
by producing `prepared_action`, not by a workflow-phase effect. Every parsed
requirement resolves `task_context` to `required`, `optional`, or `forbidden`,
with `optional` as the schema default. There is no legacy manifest compatibility.

ChatBotNutralia owns task context, reviewable drafts, revisions, approval,
idempotency, and completion receipts. Plugins own authoritative provider reads
and exact delivery of an approved snapshot.

## Install

```bash
uv add nutria-plugin==0.4.0
```

## Scaffold and validate

```bash
nutria-plugin new my-workspace-plugin --name "My Workspace Plugin"
nutria-plugin validate my-workspace-plugin
nutria-plugin pack my-workspace-plugin --output my-workspace-plugin-0.1.0.zip
```

The generated directory contains `plugin.json`, component directories for
connections, skills, context documents, specs and hooks, plus an optional
settings schema and assets.

## Minimal schema 4.0 manifest

```json
{
  "schema_version": "4.0",
  "id": "my-workspace-plugin",
  "name": "My Workspace Plugin",
  "version": "0.1.0",
  "description": "Connects Nutria to an authoritative workspace.",
  "author": "Your Name",
  "runtime_types": ["declarative_api"],
  "required_secrets": ["API_KEY"],
  "remote_endpoints": ["https://api.myworkspace.com"],
  "capabilities": [{
    "id": "workspace.search",
    "title": "Search workspace",
    "description": "Read matching workspace resources.",
    "effect": "read",
    "tool": "search_workspace",
    "connection_id": "workspace",
    "requirements": {
      "authority": "read",
      "audience": ["team_internal"],
      "task_context": "optional"
    },
    "exposure": "model",
    "produces": [{
      "result_path": ".items",
      "resource_type": "workspace.item",
      "output_name": "items",
      "many": true
    }]
  }],
  "world_providers": [{
    "id": "workspace",
    "title": "Workspace",
    "description": "Authoritative workspace resources.",
    "connection_id": "workspace",
    "resource_types": [{
      "id": "workspace.item",
      "title": "Workspace item",
      "description": "One stable workspace item.",
      "identity_fields": ["id"],
      "search_capability": "workspace.search"
    }]
  }]
}
```

Every capability must declare `requirements` and `exposure`. `task_context`
defaults to `optional`; hosts resolve and may promote it to `required` when the
capability consumes or produces task-owned resources such as `task`, `artifact`,
or `prepared_action`. Host/admin-only capabilities also require a safe
`non_callable_reason`. Every connection referenced by a capability must be
represented by a matching world provider.

For customer messages, use a host-owned `reviewable_actions` contract. Do not
create plugin draft tables or native saved-draft tools. See
[`docs/reviewable-actions.md`](docs/reviewable-actions.md).

## Python API

```python
from pathlib import Path
from nutria_plugin import PluginManifest, pack_plugin, validate_plugin_dir

manifest = PluginManifest.from_file(Path("plugin.json"))
errors = validate_plugin_dir(Path("."))
archive = pack_plugin(Path("."), Path("dist/plugin.zip"))
```

### Validate MCP results against declared outputs

Manifest validation checks the descriptor itself. Protocol-level plugin tests
must also validate the payload Nutria receives after MCP transport:

```python
from nutria_plugin import validate_capability_result

payload = validate_capability_result(
    capability,
    structured_content=call_result.structuredContent,
    text_content=call_result.content[0].text,
)
```

This normalizes FastMCP's scalar JSON envelope and raises
`MCPResultContractError` when a declared path such as `.items` does not
materialize. It does not execute the tool and should be used in a bounded,
fixture-backed or read-only MCP integration test.

The package exports the strict manifest, capability, provider, reviewable-action,
admin extension/flow, bundle, packaging, and signing models/functions documented
in [`docs/python-api.md`](docs/python-api.md).

## Bundle and security rules

- `plugin.json` is required at the ZIP root.
- Paths are relative; traversal, symlinks, hidden paths, and disallowed file
  extensions are rejected.
- Maximum compressed bundle size is 20 MB and decompressed size is bounded.
- Secrets are configured after installation and never stored in the bundle.
- Remote endpoints are checked for unsafe local/private targets.
- Database-backed plugins bind user/model values as SQL parameters.

Supported runtime types are `remote_mcp`, `declarative_api`, `openapi_bridge`,
and `soap_bridge`.

## License

MIT
