# CLI Reference

The `nutria-plugin` CLI is the primary tool for plugin development.

## Installation

```bash
uv add nutria-plugin
# or
pip install nutria-plugin
```

---

## `nutria-plugin new` — Scaffold a plugin

Create a new plugin directory with the standard structure.

```bash
nutria-plugin new <id> [--name <display-name>] [--dir <target-dir>]
```

| Argument | Description |
|----------|-------------|
| `id` | Plugin ID (lowercase, hyphens allowed, e.g. `my-plugin`) |
| `--name` | Display name. Defaults to title-cased `id` |
| `--dir` | Target directory. Defaults to `<id>/` in the current directory |

**Examples:**

```bash
# Scaffold in ./my-crm-plugin/
nutria-plugin new my-crm-plugin

# Custom name and directory
nutria-plugin new my-crm-plugin --name "My CRM Plugin" --dir ~/plugins/my-crm
```

**Created structure:**

```
<dir>/
  plugin.json          # pre-filled manifest
  README.md
  connections/         # empty — add your connection JSON files
  skills/              # empty — add your SKILL.md subdirectories
  context_docs/        # empty — add your Markdown reference docs
  specs/               # empty — add OpenAPI/WSDL files
  hooks/hooks.json     # empty hooks array
  settings.schema.json # empty JSON Schema
  assets/              # empty
```

---

## `nutria-plugin validate` — Validate a plugin

Validate a plugin directory (does not pack).

```bash
nutria-plugin validate [<dir>]
```

| Argument | Description |
|----------|-------------|
| `dir` | Plugin directory to validate. Defaults to `.` |

**Exit codes:** `0` = valid, `1` = one or more errors found.

**Output:**

```bash
$ nutria-plugin validate my-plugin/
OK

$ nutria-plugin validate broken-plugin/
Validation errors:
  - invalid plugin.json: version must use semantic versioning
  - invalid plugin.json: remote_endpoints[0] targets a private/internal address
```

Validation checks:
- All `plugin.json` fields (see [manifest.md](manifest.md))
- Required files present (`plugin.json`, at least one connection or skill)
- No hidden files in the directory
- No symlinks

---

## `nutria-plugin pack` — Validate and pack a ZIP

Validate the plugin and produce a distributable ZIP archive.

```bash
nutria-plugin pack [<dir>] [--output <path>] [--key <pem-file>]
```

| Argument | Description |
|----------|-------------|
| `dir` | Plugin directory to pack. Defaults to `.` |
| `--output`, `-o` | Output ZIP path. Defaults to `<id>-<version>.zip` in the current directory |
| `--key` | Path to a PEM private key file. If provided, the manifest is signed before packing |

**Examples:**

```bash
# Pack to default name (my-plugin-0.1.0.zip)
nutria-plugin pack my-plugin/

# Custom output path
nutria-plugin pack my-plugin/ --output dist/my-plugin-0.1.0.zip

# Sign and pack
nutria-plugin pack my-plugin/ --key my-signing-key.pem --output dist/my-plugin-0.1.0.zip
```

**What pack does:**
1. Runs full validation — aborts on any error
2. Collects all files, skipping hidden files and checking extensions
3. Rejects symlinks
4. Writes a ZIP with stored (non-compressed) entries and safe paths
5. Optionally signs the manifest before writing

---

## `nutria-plugin sign` — Sign a manifest in-place

Sign an existing `plugin.json` file. Modifies the file by adding or updating
the `signature` field.

```bash
nutria-plugin sign [<manifest>] --key <pem-file>
```

| Argument | Description |
|----------|-------------|
| `manifest` | Path to `plugin.json`. Defaults to `plugin.json` in the current directory |
| `--key` | Path to the PEM private key file (required) |

**Example:**

```bash
nutria-plugin sign plugin.json --key my-signing-key.pem
```

Signing does not pack — run `nutria-plugin pack` after signing to produce
the distributable ZIP.

---

## `nutria-plugin keygen` — Generate a signing key pair

Generate an ECDSA P-256 key pair for plugin signing.

```bash
nutria-plugin keygen [--out <stem>]
```

| Argument | Description |
|----------|-------------|
| `--out` | Output file stem. Defaults to `nutria-plugin`. Output path must be within the current directory |

**Output files:**

| File | Contents |
|------|----------|
| `<stem>.pem` | PEM-encoded private key — keep secret, never commit |
| `<stem>.pub.pem` | PEM-encoded public key — distribute to Nutria instances |

**Example:**

```bash
nutria-plugin keygen --out acme-publisher
# Private key: acme-publisher.pem
# Public key:  acme-publisher.pub.pem
```

**Security note:** The output path is resolved and must be within the current
working directory. Path traversal in `--out` is rejected.

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Validation error, signing error, or unexpected failure |
| `2` | CLI usage error (invalid arguments) |
