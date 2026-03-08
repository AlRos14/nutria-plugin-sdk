# Quickstart — Your first Nutria plugin

This guide builds a minimal working plugin that lets a persona search a
fictional inventory REST API. It takes about 5 minutes.

## Prerequisites

- Python 3.11+
- `uv` (or `pip`)

## 1. Install the SDK

```bash
uv add nutria-plugin
# or
pip install nutria-plugin
```

Verify:

```bash
nutria-plugin --help
```

## 2. Scaffold a plugin directory

```bash
nutria-plugin new inventory-lookup --name "Inventory Lookup"
```

This creates:

```
inventory-lookup/
  plugin.json
  README.md
  connections/
  skills/
  context_docs/
  specs/
  hooks/hooks.json
  settings.schema.json
  assets/
```

## 3. Edit plugin.json

Open `inventory-lookup/plugin.json` and fill it in:

```json
{
  "schema_version": "1.0",
  "id": "inventory-lookup",
  "name": "Inventory Lookup",
  "version": "0.1.0",
  "description": "Lets personas query real-time inventory levels from the Warehouse API.",
  "author": "Acme Corp <dev@acme.com>",
  "runtime_types": ["declarative_api"],
  "required_secrets": ["WAREHOUSE_API_KEY"],
  "remote_endpoints": ["https://api.warehouse.acme.com"]
}
```

Key rules:
- `id` must be lowercase, letters/digits/hyphens, max 64 chars
- `version` must be semver (e.g. `0.1.0`, `1.0.0-beta`)
- `required_secrets` are *names only* — no values ever go in the manifest

## 4. Add a connection

Create `inventory-lookup/connections/warehouse.json`:

```json
{
  "id": "warehouse",
  "name": "Warehouse API",
  "description": "REST API for querying product stock levels and locations.",
  "runtime": "declarative_api",
  "base_url": "https://api.warehouse.acme.com",
  "auth": {
    "type": "header",
    "header": "X-API-Key",
    "secret": "WAREHOUSE_API_KEY"
  },
  "tools": [
    {
      "name": "get_stock",
      "description": "Get current stock level and warehouse location for a product SKU.",
      "method": "GET",
      "path": "/v1/stock/{sku}",
      "authority_level": "read",
      "parameters": {
        "path": {
          "sku": {
            "type": "string",
            "description": "Product SKU code"
          }
        }
      }
    },
    {
      "name": "search_products",
      "description": "Search products by name. Returns SKU, name, and current stock.",
      "method": "GET",
      "path": "/v1/products",
      "authority_level": "read",
      "parameters": {
        "query": {
          "q": {
            "type": "string",
            "description": "Search term"
          },
          "limit": {
            "type": "integer",
            "description": "Max results (default 10)"
          }
        }
      }
    }
  ]
}
```

## 5. Add a skill

Create `inventory-lookup/skills/inventory-lookup/SKILL.md`:

```markdown
---
name: inventory-lookup
display_name: Inventory Lookup
version: 0.1.0
description: Query real-time stock levels for products.
tools_required:
  - conn_inventory-lookup--warehouse__get_stock
  - conn_inventory-lookup--warehouse__search_products
authority_levels:
  conn_inventory-lookup--warehouse__get_stock: read
  conn_inventory-lookup--warehouse__search_products: read
triggers:
  - "stock level"
  - "is it in stock"
  - "inventory"
  - "warehouse"
---

# Inventory Lookup Skill

Use `conn_inventory-lookup--warehouse__search_products` to find a product
by name when you have a partial name, then use `get_stock` with the SKU
for real-time availability.

Always include the warehouse location in the response.
```

Tool name format: `conn_<plugin-id>--<connection-id>__<tool-name>`

## 6. Validate

```bash
nutria-plugin validate inventory-lookup/
# OK
```

If there are errors, fix them before proceeding.

## 7. Pack

```bash
nutria-plugin pack inventory-lookup/ --output inventory-lookup-0.1.0.zip
# Packed: inventory-lookup-0.1.0.zip
```

## 8. Sign (optional but recommended)

Generate a key pair once per publisher:

```bash
nutria-plugin keygen --out acme-signing-key
# Private key: acme-signing-key.pem     ← keep secret
# Public key:  acme-signing-key.pub.pem ← distribute to Nutria instances
```

Sign and pack together:

```bash
nutria-plugin pack inventory-lookup/ \
  --key acme-signing-key.pem \
  --output inventory-lookup-0.1.0.zip
```

Configure the Nutria instance to trust your key:

```bash
export NUTRIA_PLUGIN_TRUSTED_KEYS='["-----BEGIN PUBLIC KEY-----\nMFkwEwYH..."]'
```

## 9. Install

```bash
nutria plugin install inventory-lookup-0.1.0.zip
```

Then configure the required secret:

```bash
nutria plugin secrets inventory-lookup
# Prompts: WAREHOUSE_API_KEY = ?
```

## Next steps

- [manifest.md](manifest.md) — all `plugin.json` fields
- [connection-types.md](connection-types.md) — REST, SOAP, OpenAPI, MCP
- [security.md](security.md) — signing and trust in depth
