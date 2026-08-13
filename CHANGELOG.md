# Changelog

## 0.3.1

- Create missing parent directories for explicit plugin package output paths.

## 0.3.0

- Replace adapter-specific prepared actions with one portable exact-preview protocol.
- Require typed value/resource inputs with explicit origin and sensitivity.
- Require JSON result paths for model-visible read outputs and reject schema 2.2.

## 0.2.3

- Make manifest schema 2.2 the only accepted plugin contract.
- Require every manifest to declare typed capabilities and world providers.
- Require explicit capability authority, audience, task-context, and exposure.
- Replace model-callability and compatibility metadata with strict exposure and
  safe non-callability reasons.
- Require task context for task-owned resources and matching providers for all
  connection-backed capabilities.
- Tighten reviewable external writes, immutable envelope mappings,
  idempotency, and completion receipt validation.

## 0.2.2

- Add backward-compatible schema-2.1 capability exposure and safe non-callability metadata.
- Add prepared-action, idempotency, and completion receipt contracts.
- Require model-selectable external writes to declare all execution safety contracts.

## 0.2.1

- Add manifest schema `2.1` with typed world providers, custom resource types,
  stable identity fields, safe projections, and provider capability references.
- Keep schema `2.0` compatible and export the new provider descriptor models.
- Scaffold new plugins with schema `2.1` while preserving the 0.3.0 roadmap.

## 0.2.0

- Make manifest schema `2.0` the single production schema.
- Add typed capability/resource descriptors and host-only external writes.
- Replace native reviewable-action tool names with capability references.
- Validate capability references, typed bindings, and pure preparation adapters.
- Export all capability and resource models from `nutria_plugin`.

All notable changes to `nutria-plugin` are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Documentation

- **Database-backed plugin rules** — `docs/security.md` now documents the
  standard for plugins with local state: keep small SQLite stores
  dependency-light, use bound parameters for all user/LLM-controlled values,
  avoid interpolated SQL, centralize database access, and reserve SQLAlchemy for
  plugins that need ORM/migration capabilities.
- **Store-scoped settings fields** — `README.md` and `docs/manifest.md` now
  document the host-specific `x-nutria-store-scoped` settings schema contract
  for plugins that need one admin field per loaded store plus a `default`
  fallback.

---

## [0.0.1.5b0] — 2026-04-15

### Added

- **Declarative admin extensions** — `PluginManifest` now accepts
  `admin_extensions`, a host-rendered frontend extension contract that lets
  plugins declare safe operator-facing views for the Nutria admin UI.
- **New manifest models** — added `PluginAdminExtension`,
  `PluginAdminExtensionPlacement`, and `PluginAdminExtensionKind` to the shared
  SDK schema so plugin authors can package frontend extensions without shipping
  arbitrary browser code.

### Documentation

- **`docs/admin-extensions.md`**: new guide describing the host-rendered admin
  extension model, supported placements/kinds, schema-file layout, and the
  recommended packaging pattern for plugin-provided operator views.
- **`docs/manifest.md`**: documented the `admin_extensions` field and its safe
  `schema_path` contract.
- **`docs/index.md`**: updated the documentation version and added the new admin
  extensions guide to the index.

### Notes

- This release is the SDK-side foundation for plugin-driven frontend extension.
  The first concrete consumer is the `nutria-email` plugin's Email Audit panel.
- Requested release label: `0.0.1.5b`; published Python package version is
  normalized to `0.0.1.5b0` under PEP 440.

---

## [0.0.1.3a1] — 2026-03-13

### Changed

- **`packaging.py`**: `mcp_server/requirements.txt` is now silently excluded
  from plugin ZIPs at pack time (both `_collect_plugin_files` and
  `validate_plugin_dir`). Bundling a requirements file inside `mcp_server/`
  would create a misleading expectation that it is auto-installed, which is a
  critical supply-chain risk for marketplace plugins. Plugin MCP server
  dependencies must be installed by the server operator in the host environment.

### Documentation

- **`docs/security.md`**: Added "Dependency management" section explaining the
  rationale for excluding `requirements.txt`, the standard runtime model, and
  the roadmap for per-plugin venv support (marketplace Option D). Corrected the
  "Allowed extensions" section — `.py` is allowed in `mcp_server/` for
  `remote_mcp` plugins (exception not previously documented).

---

## [0.0.1-alpha] — 2025-03-08

Initial alpha release. API and file format are not yet stable.

### Added

**Manifest model (`manifest.py`)**
- `PluginManifest` — Pydantic v2 model for `plugin.json` with strict validation
- Fields: `id`, `name`, `version`, `description`, `author`, `runtime_types`,
  `default_scope`, `compatibility`, `paths`, `required_secrets`,
  `remote_endpoints`, `capabilities`, `tags`, `homepage`, `license`, `signature`
- `PluginRuntimeType` enum: `remote_mcp`, `declarative_api`, `openapi_bridge`, `soap_bridge`
- `PluginScope` enum: `platform`, `store`, `persona`
- `PluginCompatibility` model with semver-validated `min_nutria_version` / `max_nutria_version`
- `PluginPaths` model for overriding default component paths
- `PluginManifest.from_file()`, `from_json_bytes()`, `to_file()` helpers

**Bundle operations (`bundle.py`)**
- `load_plugin_bundle(data: bytes) -> PluginManifest` — parse and validate a plugin ZIP
- `extract_plugin_bundle(data: bytes, target_dir: Path) -> PluginManifest` — safe extraction
- `validate_zip(data: bytes) -> list[str]` — non-extracting ZIP validation
- `PluginBundleError` exception
- Decompression bomb guard: 100 MB uncompressed size limit
- Extension allowlist: `.json .md .yaml .yml .txt .png .jpg .jpeg .svg .ico .pdf .wsdl .xsd .xml .csv`
- Path traversal prevention via `PurePosixPath` normalization
- Maximum ZIP size: 20 MB

**Packaging (`packaging.py`)**
- `scaffold_plugin(plugin_id, name, target_dir)` — create standard plugin directory
- `pack_plugin(plugin_dir, output_path, sign, private_key_pem) -> Path` — validate and pack
- `validate_plugin_dir(plugin_dir) -> list[str]` — directory validation (hidden files skipped)
- `PackagingError` exception
- Symlink rejection at pack time
- Hidden file skipping (consistent between `validate_plugin_dir` and `pack_plugin`)

**Signing (`signing.py`)**
- `generate_keypair() -> tuple[str, str]` — ECDSA P-256 key pair generation
- `sign_manifest(manifest: dict, private_key_pem: str) -> str` — sign and return hex DER signature
- `verify_manifest(manifest: dict) -> SignatureStatus` — verify against `NUTRIA_PLUGIN_TRUSTED_KEYS`
- `SignatureStatus` enum: `VERIFIED`, `UNSIGNED`, `INVALID`, `UNTRUSTED`, `MISSING`
- Canonical payload serialization (sorted keys, no `signature` field, no whitespace)
- `NUTRIA_PLUGIN_TRUSTED_KEYS` env var for trusted public key list

**CLI (`cli.py`)**
- `nutria-plugin new <id>` — scaffold plugin directory
- `nutria-plugin validate [dir]` — validate plugin directory
- `nutria-plugin pack [dir]` — validate and pack to ZIP
- `nutria-plugin sign [manifest] --key <pem>` — sign manifest in-place
- `nutria-plugin keygen [--out <stem>]` — generate ECDSA P-256 key pair
- `--key` flag on `pack` for inline sign-and-pack
- `--output`/`-o` flag on `pack` for custom output path

**Documentation**
- `docs/index.md` — overview and navigation
- `docs/quickstart.md` — first plugin in 5 minutes
- `docs/manifest.md` — complete `plugin.json` field reference
- `docs/connection-types.md` — all 4 runtime types with annotated examples
- `docs/skill-format.md` — `SKILL.md` frontmatter schema and authoring guide
- `docs/security.md` — signing, trust policies, ZIP safety, secrets
- `docs/cli.md` — all CLI commands and flags
- `docs/python-api.md` — Python API reference

**Security hardening**
- SSRF protection: `remote_endpoints` blocks loopback, private, link-local, reserved IPs
- Decompression bomb: 100 MB limit on `ZipInfo.file_size` before extraction
- Symlink blocking: `PackagingError` raised on any symlink in plugin source
- Extension allowlist (not blocklist)
- CLI `keygen --out` path traversal prevention (output path must be within CWD)
- `_safe_zip_path`: checks `".." in path.parts` on normalized `PurePosixPath`

### Notes

- This is an alpha release. Manifest schema, connection file format, and
  Python API may change before `0.1.0`.
- `declarative_api` connection file format is not yet formally versioned.
- WSDL/OpenAPI bridge tool name conventions are established but the bridge
  runtime is implemented in the ChatBotNutralia host, not this package.
