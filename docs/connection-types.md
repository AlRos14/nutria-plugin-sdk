# Connection Types

A connection file lives in `connections/<id>.json` and describes one external
integration. Nutria uses the connection file to generate the tools that the
persona can call.

## Tool naming convention

Every tool generated from a connection has a canonical name:

```
conn_<plugin-id>--<connection-id>__<tool-name>
```

Examples:
- `conn_inventory-lookup--warehouse__get_stock`
- `conn_mrw-shipping--sagec__TransmEnvio`
- `conn_trello-workspace--trello__get_card`

This name is used in `SKILL.md` `tools_required` and `authority_levels` fields,
and in the Nutria approval log.

## Authority levels

Every tool must declare an authority level that controls approval requirements.

| Level | Description |
|-------|-------------|
| `read` | Read-only query — no approval required |
| `write_internal` | Writes to Nutria-internal state only — no external approval required |
| `write_external` | Writes to an external system — requires human approval |

---

## Runtime type: `declarative_api`

Hand-written REST tool definitions. No spec file required. Nutria executes
the HTTP calls directly using the connection definition.

### Minimum file

```json
{
  "id": "my-api",
  "name": "My API",
  "description": "Short description of this connection.",
  "runtime": "declarative_api",
  "base_url": "https://api.myservice.com",
  "auth": { "type": "none" },
  "tools": []
}
```

### Auth options

**No auth:**
```json
{ "auth": { "type": "none" } }
```

**Static header (e.g. API key):**
```json
{
  "auth": {
    "type": "header",
    "header": "X-API-Key",
    "secret": "MY_API_KEY"
  }
}
```

**Bearer token:**
```json
{
  "auth": {
    "type": "bearer",
    "secret": "MY_TOKEN"
  }
}
```

**Basic auth:**
```json
{
  "auth": {
    "type": "basic",
    "username_secret": "MY_USERNAME",
    "password_secret": "MY_PASSWORD"
  }
}
```

**OAuth2 client credentials:**
```json
{
  "auth": {
    "type": "oauth2_client_credentials",
    "token_url": "https://auth.myservice.com/token",
    "client_id_secret": "MY_CLIENT_ID",
    "client_secret_secret": "MY_CLIENT_SECRET",
    "scope": "read:data write:data"
  }
}
```

### Tool definition

```json
{
  "name": "get_user",
  "description": "Get a user by ID.",
  "method": "GET",
  "path": "/v1/users/{user_id}",
  "authority_level": "read",
  "parameters": {
    "path": {
      "user_id": {
        "type": "string",
        "description": "The user UUID"
      }
    },
    "query": {
      "include_deleted": {
        "type": "boolean",
        "description": "Include soft-deleted users",
        "required": false
      }
    }
  }
}
```

**POST with body:**
```json
{
  "name": "create_card",
  "description": "Create a new card on a Trello list.",
  "method": "POST",
  "path": "/1/cards",
  "authority_level": "write_external",
  "parameters": {
    "query": {
      "idList":  { "type": "string",  "description": "Target list ID" },
      "name":    { "type": "string",  "description": "Card title" },
      "desc":    { "type": "string",  "description": "Card description", "required": false },
      "due":     { "type": "string",  "description": "Due date (ISO 8601)", "required": false }
    }
  }
}
```

**PUT with enum constraint:**
```json
{
  "name": "close_card",
  "description": "Archive a Trello card.",
  "method": "PUT",
  "path": "/1/cards/{card_id}",
  "authority_level": "write_external",
  "parameters": {
    "path": {
      "card_id": { "type": "string", "description": "Card ID" }
    },
    "query": {
      "closed": {
        "type": "string",
        "enum": ["true"],
        "description": "Must be 'true' to archive the card"
      }
    }
  }
}
```

---

## Runtime type: `openapi_bridge`

Nutria reads an OpenAPI 3.x or Swagger 2.x spec and auto-generates all tools.
The spec file lives in `specs/` (default: `specs/openapi.json` or `specs/openapi.yaml`).

```json
{
  "id": "my-openapi-service",
  "name": "My OpenAPI Service",
  "description": "Auto-generated tools from the service OpenAPI spec.",
  "runtime": "openapi_bridge",
  "spec": "specs/openapi.json",
  "endpoint": "https://api.myservice.com",
  "auth": {
    "type": "bearer",
    "secret": "MY_TOKEN"
  }
}
```

- The `spec` field is a relative path inside the plugin ZIP.
- All operations in the spec become available as tools.
- Tool names are derived from `operationId` values in the spec.
- If `operationId` is missing, the bridge will generate names from method+path.
- You can filter or exclude operations using `include_operations` /
  `exclude_operations` arrays (list of operationIds).

```json
{
  "include_operations": ["getCard", "createCard", "updateCard"]
}
```

---

## Runtime type: `soap_bridge`

Nutria reads a WSDL file and generates tools for each WSDL operation.
The WSDL file lives in `specs/`.

```json
{
  "id": "sagec",
  "name": "MRW SAGEC",
  "description": "MRW SAGEC SOAP 1.2 service.",
  "runtime": "soap_bridge",
  "soap_version": "1.2",
  "spec": "specs/sagec.wsdl",
  "endpoint": "https://sagec.mrw.es/MRWEnvio.asmx",
  "auth": {
    "type": "soap_header",
    "header_element": "AuthInfo",
    "header_namespace": "http://www.mrw.es/",
    "fields": {
      "Username": { "secret": "MY_USERNAME" },
      "Password": { "secret": "MY_PASSWORD" }
    }
  },
  "tools": [
    {
      "operation": "GetOrder",
      "authority_level": "read",
      "description": "Retrieve order details."
    },
    {
      "operation": "CreateOrder",
      "authority_level": "write_external",
      "description": "Create a new order."
    }
  ]
}
```

**`soap_version`**: `"1.1"` or `"1.2"`. Defaults to `"1.1"`.

**Auth types for SOAP:**

*Header auth (credentials in SOAP envelope header):*
```json
{
  "type": "soap_header",
  "header_element": "AuthHeader",
  "header_namespace": "http://myservice.com/",
  "fields": {
    "Username": { "secret": "MY_USERNAME" },
    "Password": { "secret": "MY_PASSWORD" }
  }
}
```

*Body auth (credentials injected as operation parameters):*
```json
{
  "type": "soap_body",
  "fields": {
    "login": { "secret": "MY_USERNAME" },
    "pass":  { "secret": "MY_PASSWORD" }
  }
}
```

*Optional fields:*
```json
{
  "Username":   { "secret": "MY_USERNAME" },
  "Department": { "secret": "MY_DEPT", "optional": true }
}
```

**Tool names for SOAP bridge:**

```
conn_<plugin-id>--<wsdl-stem>__<OperationName>
```

where `wsdl-stem` is the WSDL filename without the `.wsdl` extension.

Examples with `specs/sagec.wsdl`:
- `conn_mrw-shipping--sagec__TransmEnvio`
- `conn_mrw-shipping--sagec__GetEtiquetaEnvio`

---

## Runtime type: `remote_mcp`

Connects to an already-deployed MCP server. Nutria proxies tool calls to it.

```json
{
  "id": "my-mcp-server",
  "name": "My MCP Server",
  "description": "Proxy to our internal MCP tool server.",
  "runtime": "remote_mcp",
  "endpoint": "https://mcp.myservice.com",
  "auth": {
    "type": "bearer",
    "secret": "MCP_AUTH_TOKEN"
  }
}
```

- The endpoint must be accessible from the Nutria instance.
- Tool names are taken directly from the MCP server's `tools/list` response.
- The MCP server is responsible for defining tool schemas and executing calls.
