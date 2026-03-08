# Changelog

All notable changes to `nutria-plugin` are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
