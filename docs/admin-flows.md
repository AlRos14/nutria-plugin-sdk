# Declarative Admin Flows

Admin flows let plugins expose safe, host-rendered operator workflows without
shipping frontend code. They are intended for interactive, non-secret setup
steps such as QR pairing, OAuth/device-code login, phone-code confirmation, or
similar external authentication flows.

## Manifest field

Plugins declare flows in `plugin.json` through `admin_flows`.

```json
{
  "id": "my-plugin",
  "runtime_types": ["remote_mcp"],
  "admin_flows": [
    {
      "id": "external-login",
      "title": "External login",
      "description": "Pair an external account.",
      "placement": "plugins.detail",
      "kind": "external_auth",
      "schema_path": "assets/admin/external-login-flow.json"
    }
  ]
}
```

## Supported values

### `placement`

- `plugins.detail` — render the flow inside the Plugins admin page

### `kind`

- `external_auth` — an operator-driven authentication or pairing flow that may
  start an external login session, poll status, show a QR/code/text artifact, and
  optionally cancel the session.

## Flow schema

The file referenced by `schema_path` must be a JSON object inside the plugin
bundle and must include `"type": "external_auth"`.

Recommended shape:

```json
{
  "type": "external_auth",
  "connection_id": "my-plugin-connection",
  "input_schema": {
    "type": "object",
    "properties": {
      "pairing_method": {
        "type": "string",
        "enum": ["qr", "phone"],
        "default": "qr"
      }
    }
  },
  "actions": {
    "status": {
      "tool": "auth_status",
      "authority": "read"
    },
    "start": {
      "tool": "start_auth",
      "authority": "write_internal",
      "arguments": {
        "pairing_method": "$input.pairing_method"
      }
    },
    "poll": {
      "tool": "get_auth_session",
      "authority": "read",
      "arguments": {
        "session_id": "$state.session_id"
      }
    },
    "cancel": {
      "tool": "cancel_auth_session",
      "authority": "write_internal",
      "arguments": {
        "session_id": "$state.session_id"
      }
    }
  },
  "result_mapping": {
    "status": "session.status",
    "session_id": "session.session_id",
    "qr_payload": "session.latest_qr_payload",
    "code": "session.latest_pairing_code",
    "error": "session.last_error"
  },
  "terminal_states": ["authenticated", "cancelled", "failed", "stopped"],
  "poll_interval_ms": 2000
}
```

The host owns validation, rendering, polling, permissions, and error display.
Plugins own only the declarative contract and the runtime tools referenced by
the contract.

## Security rules

- Flow schemas are JSON data, not executable frontend assets.
- Actions must reference plugin-owned runtime tools.
- Login flows should use `read` or `write_internal` authority only.
- Static credentials belong in `required_secrets`, not in admin flow schemas.
- Operator-entered settings belong in `settings.schema.json`, not in flow
  artifacts.
