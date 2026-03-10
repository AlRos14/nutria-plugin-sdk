"""
Plugin bundle validation and extraction.

This module handles the ZIP lifecycle:
  - validate_zip()     — check structure/size/allowlist, no I/O side-effects
  - load_plugin_bundle() — parse and return the manifest without extracting
  - extract_plugin_bundle() — extract into a target directory
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path, PurePosixPath
from typing import Optional

from .manifest import PluginManifest, PluginRuntimeType

MANIFEST_FILENAME = "plugin.json"
MAX_BUNDLE_SIZE_BYTES = 20 * 1024 * 1024   # 20 MB compressed
MAX_UNCOMPRESSED_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB total uncompressed

# Allowlist — only these extensions are accepted inside a plugin ZIP.
# Files with no extension (e.g. README, CHANGELOG) are also allowed.
ALLOWED_EXTENSIONS = {
    ".json",
    ".md",
    ".txt",
    ".html",
    ".htm",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".xml",
    ".wsdl",   # SOAP specs
    ".yaml",
    ".yml",
}

# Kept for backwards-compatible imports; no longer used in core validation.
BLOCKED_PATTERNS = {".py", ".js", ".ts", ".sh", ".exe", ".dll", ".so", ".whl", ".tar"}


class PluginBundleError(Exception):
    """Raised when a plugin ZIP is invalid, corrupt, or unsafe."""


def _safe_zip_path(name: str) -> PurePosixPath:
    """Return a PurePosixPath for the ZIP entry or raise PluginBundleError on path traversal.

    Checks the raw string for traversal before PurePosixPath normalisation strips
    any context (e.g. PurePosixPath("./x").parts == ("x",) — the '.' is gone).
    """
    if "//" in name or name.startswith("/"):
        raise PluginBundleError(f"zip entry with absolute path is not allowed: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute():
        raise PluginBundleError(f"zip entry with absolute path is not allowed: {name!r}")
    if ".." in path.parts:
        raise PluginBundleError(f"zip entry with path traversal is not allowed: {name!r}")
    return path


def validate_zip(data: bytes) -> list[str]:
    """Validate a plugin ZIP and return a list of validation errors (empty = valid).

    This does NOT extract files to disk — it only reads the ZIP in memory.
    """
    errors: list[str] = []

    if len(data) > MAX_BUNDLE_SIZE_BYTES:
        errors.append(
            f"bundle exceeds max size {MAX_BUNDLE_SIZE_BYTES // (1024 * 1024)} MB"
        )
        return errors  # no point continuing size checks

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()

            # 1. manifest must be present at the top level
            if MANIFEST_FILENAME not in names:
                errors.append(f"{MANIFEST_FILENAME} not found in bundle root")

            # 2. zip bomb: check total uncompressed size before any extraction
            total_uncompressed = sum(info.file_size for info in zf.infolist())
            if total_uncompressed > MAX_UNCOMPRESSED_SIZE_BYTES:
                errors.append(
                    f"bundle uncompressed content exceeds max size "
                    f"{MAX_UNCOMPRESSED_SIZE_BYTES // (1024 * 1024)} MB"
                )
                return errors

            for name in names:
                try:
                    path = _safe_zip_path(name)
                except PluginBundleError as exc:
                    errors.append(str(exc))
                    continue

                suffix = path.suffix.lower()

                # 3. allowlist: only known-safe extensions (files with no extension are allowed)
                #    Exception: .py files are allowed inside mcp_server/ for remote_mcp plugins
                if suffix and suffix not in ALLOWED_EXTENSIONS:
                    in_mcp_server = len(path.parts) >= 2 and path.parts[0] == "mcp_server"
                    if not (suffix == ".py" and in_mcp_server):
                        errors.append(f"file type not allowed in plugin bundle: {name!r}")

                # 4. no hidden files
                if any(part.startswith(".") for part in path.parts):
                    errors.append(f"hidden file/directory not allowed in plugin bundle: {name!r}")

    except zipfile.BadZipFile as exc:
        errors.append(f"invalid zip file: {exc}")

    return errors


def load_plugin_bundle(data: bytes) -> PluginManifest:
    """Parse and return the PluginManifest from ZIP bytes without extracting to disk.

    Raises:
        PluginBundleError: if the ZIP is invalid or the manifest cannot be parsed.
    """
    errors = validate_zip(data)
    if errors:
        raise PluginBundleError("; ".join(errors))

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            raw = zf.read(MANIFEST_FILENAME)
    except KeyError:
        raise PluginBundleError(f"{MANIFEST_FILENAME} missing from bundle")
    except zipfile.BadZipFile as exc:
        raise PluginBundleError(f"invalid zip file: {exc}")

    try:
        manifest = PluginManifest.from_json_bytes(raw)
    except Exception as exc:
        raise PluginBundleError(f"invalid {MANIFEST_FILENAME}: {exc}") from exc

    # Verify mcp_server/ .py files are only present in remote_mcp plugins
    if PluginRuntimeType.REMOTE_MCP not in manifest.runtime_types:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                path = PurePosixPath(name)
                if len(path.parts) >= 2 and path.parts[0] == "mcp_server" and path.suffix == ".py":
                    raise PluginBundleError(
                        "mcp_server/ with .py files is only allowed for remote_mcp plugins"
                    )

    return manifest


def extract_plugin_bundle(data: bytes, target_dir: Path) -> PluginManifest:
    """Extract a plugin ZIP into target_dir and return the parsed manifest.

    target_dir must already exist. Any existing contents are left in place;
    the caller is responsible for cleanup on failure.

    Raises:
        PluginBundleError: if validation fails or extraction encounters path traversal.
    """
    manifest = load_plugin_bundle(data)  # validates first

    target_dir = target_dir.resolve()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            safe_path = _safe_zip_path(info.filename)
            dest = target_dir / safe_path
            # double-check after resolving symlinks
            try:
                dest.resolve().relative_to(target_dir)
            except ValueError:
                raise PluginBundleError(
                    f"path traversal detected during extraction: {info.filename!r}"
                )
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(info.filename))

    return manifest
