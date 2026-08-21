"""
Plugin scaffold, validation, and packaging helpers.

nutria-plugin new    — scaffold a new plugin directory
nutria-plugin pack   — validate and zip a plugin directory
nutria-plugin validate — validate without packing
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Optional

from .bundle import ALLOWED_EXTENSIONS, validate_zip
from .manifest import PluginManifest


class PackagingError(Exception):
    """Raised when plugin packaging fails validation."""


SCAFFOLD_TEMPLATE = {
    "plugin.json": lambda plugin_id, name: json.dumps(
        {
            "schema_version": "4.0",
            "id": plugin_id,
            "name": name,
            "version": "0.1.0",
            "description": f"{name} plugin for Nutria",
            "author": "Your Name",
            "runtime_types": ["declarative_api"],
            "default_scope": "store",
            "required_secrets": [],
            "remote_endpoints": [],
            "capabilities": [
                {
                    "id": f"{plugin_id}.health.read",
                    "title": "Read plugin health",
                    "description": "Read the current plugin connection health.",
                    "effect": "read",
                    "tool": "get_health",
                    "connection_id": plugin_id,
                    "requirements": {
                        "authority": "read",
                        "audience": ["private_internal", "team_internal"],
                        "task_context": "optional",
                    },
                    "exposure": "model",
                    "produces": [
                        {
                            "result_path": ".health",
                            "resource_type": f"{plugin_id}.resource",
                            "output_name": "health",
                        }
                    ],
                }
            ],
            "world_providers": [
                {
                    "id": plugin_id,
                    "title": name,
                    "description": f"Authoritative {name} resources.",
                    "connection_id": plugin_id,
                    "health_capability": f"{plugin_id}.health.read",
                    "resource_types": [
                        {
                            "id": f"{plugin_id}.resource",
                            "title": f"{name} resource",
                            "description": f"One stable resource exposed by {name}.",
                            "identity_fields": ["id"],
                        }
                    ],
                }
            ],
            "tags": [],
        },
        indent=2,
    )
    + "\n",
    "README.md": lambda plugin_id, name: f"# {name}\n\nNutria plugin for {name}.\n",
    "hooks/hooks.json": lambda *_: json.dumps({"hooks": []}, indent=2) + "\n",
    "settings.schema.json": lambda *_: json.dumps(
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {},
            "required": [],
        },
        indent=2,
    )
    + "\n",
}

# Directories to create with no required placeholder files.
SCAFFOLD_DIRS = ["connections", "skills", "context_docs", "specs", "assets"]

# Top-level directories that are for developer use only and excluded from the ZIP.
_EXCLUDED_TOP_DIRS = {"docs", "tests", "test", ".github", "examples", "example"}
_EXCLUDED_ROOT_FILES = {
    "pyproject.toml", "setup.py", "setup.cfg", "Makefile",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "uv.lock", "poetry.lock", "requirements.txt", "requirements-dev.txt",
    ".python-version", "tox.ini",
}


def scaffold_plugin(
    target_dir: Path,
    plugin_id: str,
    name: Optional[str] = None,
    *,
    overwrite: bool = False,
) -> None:
    """Create a new plugin directory with starter files.

    Raises:
        PackagingError: if target_dir already exists and overwrite is False.
    """
    if target_dir.exists() and not overwrite:
        raise PackagingError(
            f"directory {target_dir} already exists; use overwrite=True to replace"
        )
    name = name or plugin_id
    target_dir.mkdir(parents=True, exist_ok=True)
    for rel, content_fn in SCAFFOLD_TEMPLATE.items():
        dest = target_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content_fn(plugin_id, name), encoding="utf-8")
    for d in SCAFFOLD_DIRS:
        (target_dir / d).mkdir(exist_ok=True)


def _collect_plugin_files(plugin_dir: Path) -> list[Path]:
    """Recursively collect files to include in the plugin ZIP."""
    files: list[Path] = []
    for path in sorted(plugin_dir.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(plugin_dir)
        # skip hidden files/dirs
        if any(part.startswith(".") for part in rel.parts):
            continue
        # skip Python bytecode cache directories at any depth
        if "__pycache__" in rel.parts:
            continue
        # skip requirements.txt inside mcp_server/ — deps must be managed by
        # the server operator; bundling them creates a misleading expectation
        # that they will be auto-installed (security concern for marketplace plugins)
        if rel.parts[0] == "mcp_server" and rel.name.lower() == "requirements.txt":
            continue
        # skip developer-only top-level directories (docs/, tests/, examples/, etc.)
        if rel.parts[0] in _EXCLUDED_TOP_DIRS:
            continue
        # skip developer-only root files (pyproject.toml, Dockerfile, etc.)
        if len(rel.parts) == 1 and rel.name.lower() in _EXCLUDED_ROOT_FILES:
            continue
        # Source checkouts commonly retain the last built bundle next to
        # plugin.json. It is an output artifact, never a nested bundle member.
        if len(rel.parts) == 1 and rel.suffix.lower() == ".zip":
            continue
        # reject symlinks — they could point outside the plugin directory
        if path.is_symlink():
            raise PackagingError(
                f"symlinks are not allowed in plugin bundles: {rel}"
            )
        suffix = path.suffix.lower()
        if suffix and suffix not in ALLOWED_EXTENSIONS:
            # Allow .py files inside mcp_server/ for remote_mcp plugins
            in_mcp_server = len(rel.parts) >= 2 and rel.parts[0] == "mcp_server"
            if not (suffix == ".py" and in_mcp_server):
                raise PackagingError(
                    f"file type {suffix!r} not allowed in plugin bundle: {rel}"
                )
        files.append(path)
    return files


def _validate_declared_admin_assets(plugin_dir: Path, manifest: PluginManifest) -> list[str]:
    """Validate schema assets referenced by admin extensions and flows."""
    errors: list[str] = []
    declared = [
        (
            f"admin_extensions[{idx}]",
            extension.schema_path,
            extension.kind.value,
        )
        for idx, extension in enumerate(manifest.admin_extensions)
    ]
    declared.extend(
        (
            f"admin_flows[{idx}]",
            flow.schema_path,
            flow.kind.value,
        )
        for idx, flow in enumerate(manifest.admin_flows)
    )
    root = plugin_dir.resolve()
    for label, schema_path, expected_type in declared:
        path = plugin_dir / schema_path
        try:
            path.resolve().relative_to(root)
        except ValueError:
            errors.append(f"{label}.schema_path points outside plugin directory: {schema_path}")
            continue
        if not path.exists():
            errors.append(f"{label}.schema_path not found: {schema_path}")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"{label}.schema_path is not valid JSON: {schema_path}: {exc}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"{label}.schema_path must contain a JSON object: {schema_path}")
            continue
        schema_type = payload.get("type")
        if schema_type != expected_type:
            errors.append(
                f"{label}.schema_path type must be {expected_type!r}, got {schema_type!r}"
            )
    return errors


def pack_plugin(
    plugin_dir: Path,
    output_path: Optional[Path] = None,
    *,
    sign: bool = False,
    private_key_pem: Optional[str] = None,
) -> Path:
    """Validate a plugin directory and produce a ZIP bundle.

    Args:
        plugin_dir: Path to the plugin directory containing plugin.json.
        output_path: Where to write the ZIP. Defaults to {plugin_id}-{version}.zip in the CWD.
        sign: If True, sign the manifest before packing (requires private_key_pem).
        private_key_pem: PEM-encoded EC private key for signing.

    Returns:
        Path to the created ZIP file.

    Raises:
        PackagingError: if validation fails.
    """
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.exists():
        raise PackagingError(f"plugin.json not found in {plugin_dir}")

    try:
        manifest = PluginManifest.from_file(manifest_path)
    except Exception as exc:
        raise PackagingError(f"invalid plugin.json: {exc}") from exc

    asset_errors = _validate_declared_admin_assets(plugin_dir, manifest)
    if asset_errors:
        raise PackagingError("; ".join(asset_errors))

    if sign:
        if not private_key_pem:
            raise PackagingError("private_key_pem is required when sign=True")
        from .signing import sign_manifest

        raw_dict = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw_dict["signature"] = sign_manifest(raw_dict, private_key_pem)
        manifest_path.write_text(json.dumps(raw_dict, indent=2) + "\n", encoding="utf-8")
        manifest = PluginManifest.from_file(manifest_path)

    files = _collect_plugin_files(plugin_dir)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            arcname = file_path.relative_to(plugin_dir).as_posix()
            zf.write(file_path, arcname=arcname)

    data = buf.getvalue()
    errors = validate_zip(data)
    if errors:
        raise PackagingError("bundle failed validation after packing: " + "; ".join(errors))

    if output_path is None:
        output_path = Path(f"{manifest.id}-{manifest.version}.zip")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return output_path


def validate_plugin_dir(plugin_dir: Path) -> list[str]:
    """Validate a plugin directory without packing it.

    Returns a list of errors (empty = valid).
    """
    errors: list[str] = []
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.exists():
        errors.append("plugin.json not found")
        return errors

    try:
        manifest = PluginManifest.from_file(manifest_path)
    except Exception as exc:
        errors.append(f"invalid plugin.json: {exc}")
        manifest = None

    if manifest is not None:
        errors.extend(_validate_declared_admin_assets(plugin_dir, manifest))

    for path in plugin_dir.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(plugin_dir)
        # Hidden files/dirs (e.g. .gitignore, .git/) are skipped by pack_plugin too;
        # flag them only if they would cause a problem, not just because they exist.
        if any(part.startswith(".") for part in rel.parts):
            continue
        # skip Python bytecode cache directories at any depth
        if "__pycache__" in rel.parts:
            continue
        # skip requirements.txt inside mcp_server/ — deps must be managed by
        # the server operator; bundling them creates a misleading expectation
        # that they will be auto-installed (security concern for marketplace plugins)
        if rel.parts[0] == "mcp_server" and rel.name.lower() == "requirements.txt":
            continue
        if rel.parts[0] in _EXCLUDED_TOP_DIRS:
            continue
        if len(rel.parts) == 1 and rel.name.lower() in _EXCLUDED_ROOT_FILES:
            continue
        if len(rel.parts) == 1 and rel.suffix.lower() == ".zip":
            continue
        if path.is_symlink():
            errors.append(f"symlinks not allowed: {rel}")
            continue
        suffix = path.suffix.lower()
        if suffix and suffix not in ALLOWED_EXTENSIONS:
            in_mcp_server = len(rel.parts) >= 2 and rel.parts[0] == "mcp_server"
            if not (suffix == ".py" and in_mcp_server):
                errors.append(f"file type {suffix!r} not allowed: {rel}")

    return errors
