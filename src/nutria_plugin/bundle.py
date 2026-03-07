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

from .manifest import PluginManifest

MANIFEST_FILENAME = "plugin.json"
MAX_BUNDLE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

ALLOWED_EXTENSIONS = {
    ".json",
    ".md",
    ".txt",
    ".html",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".ico",
    ".xml",
    ".yaml",
    ".yml",
}

BLOCKED_PATTERNS = {".py", ".js", ".ts", ".sh", ".exe", ".dll", ".so", ".whl", ".tar"}


class PluginBundleError(Exception):
    """Raised when a plugin ZIP is invalid, corrupt, or unsafe."""


def _safe_zip_path(name: str) -> PurePosixPath:
    """Return a PurePosixPath for the ZIP entry or raise PluginBundleError on path traversal."""
    path = PurePosixPath(name)
    if path.is_absolute():
        raise PluginBundleError(f"zip entry with absolute path is not allowed: {name!r}")
    for part in path.parts:
        if part in (".", ".."):
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

            for name in names:
                try:
                    path = _safe_zip_path(name)
                except PluginBundleError as exc:
                    errors.append(str(exc))
                    continue

                suffix = path.suffix.lower()

                # 2. no blocked executable/binary extensions
                if suffix in BLOCKED_PATTERNS:
                    errors.append(f"file type not allowed in plugin bundle: {name!r}")

                # 3. no hidden files
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
        return PluginManifest.from_json_bytes(raw)
    except Exception as exc:
        raise PluginBundleError(f"invalid {MANIFEST_FILENAME}: {exc}") from exc


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
