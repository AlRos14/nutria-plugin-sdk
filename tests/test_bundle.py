"""Tests for bundle validation and extraction."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from nutria_plugin.bundle import (
    MANIFEST_FILENAME,
    MAX_BUNDLE_SIZE_BYTES,
    PluginBundleError,
    extract_plugin_bundle,
    load_plugin_bundle,
    validate_zip,
)


def _make_zip(files: dict[str, str]) -> bytes:
    """Build an in-memory zip from a filename->content dict."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


VALID_MANIFEST = json.dumps(
    {
        "schema_version": "1.0",
        "id": "test-plugin",
        "name": "Test",
        "version": "1.0.0",
        "description": "d",
        "author": "a",
        "runtime_types": ["declarative_api"],
    }
)


def test_validate_zip_valid():
    data = _make_zip({MANIFEST_FILENAME: VALID_MANIFEST, "README.md": "# hi"})
    assert validate_zip(data) == []


def test_validate_zip_missing_manifest():
    data = _make_zip({"README.md": "hello"})
    errors = validate_zip(data)
    assert any("plugin.json" in e for e in errors)


def test_validate_zip_blocked_python_file():
    data = _make_zip({MANIFEST_FILENAME: VALID_MANIFEST, "connector/server.py": "pass"})
    errors = validate_zip(data)
    assert any(".py" in e for e in errors)


def test_validate_zip_path_traversal():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.txt", "bad content")
        zf.writestr(MANIFEST_FILENAME, VALID_MANIFEST)
    data = buf.getvalue()
    errors = validate_zip(data)
    assert any("traversal" in e.lower() or ".." in e for e in errors)


def test_validate_zip_hidden_file():
    data = _make_zip({MANIFEST_FILENAME: VALID_MANIFEST, ".secret": "nope"})
    errors = validate_zip(data)
    assert any("hidden" in e for e in errors)


def test_validate_zip_oversized(monkeypatch):
    import nutria_plugin.bundle as bundle_mod

    monkeypatch.setattr(bundle_mod, "MAX_BUNDLE_SIZE_BYTES", 10)
    data = _make_zip({MANIFEST_FILENAME: VALID_MANIFEST, "big.md": "x" * 20})
    errors = validate_zip(data)
    assert any("size" in e for e in errors)


def test_validate_zip_not_a_zip():
    errors = validate_zip(b"not a zip at all")
    assert any("zip" in e.lower() for e in errors)


def test_load_plugin_bundle_success():
    data = _make_zip({MANIFEST_FILENAME: VALID_MANIFEST})
    manifest = load_plugin_bundle(data)
    assert manifest.id == "test-plugin"


def test_load_plugin_bundle_invalid_manifest():
    data = _make_zip({MANIFEST_FILENAME: '{"id": "bad"}', "README.md": ""})
    with pytest.raises(PluginBundleError, match="plugin.json"):
        load_plugin_bundle(data)


def test_load_plugin_bundle_rejects_blocked_type():
    data = _make_zip({MANIFEST_FILENAME: VALID_MANIFEST, "evil.py": "pass"})
    with pytest.raises(PluginBundleError):
        load_plugin_bundle(data)


def test_extract_plugin_bundle_creates_files(tmp_path):
    data = _make_zip(
        {
            MANIFEST_FILENAME: VALID_MANIFEST,
            "context_docs/guide.md": "# guide",
            "connections/trello.json": "{}",
        }
    )
    manifest = extract_plugin_bundle(data, tmp_path)
    assert manifest.id == "test-plugin"
    assert (tmp_path / "context_docs" / "guide.md").exists()
    assert (tmp_path / "connections" / "trello.json").exists()


def test_extract_plugin_bundle_path_traversal_rejected(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(MANIFEST_FILENAME, VALID_MANIFEST)
        zf.writestr("../escape.txt", "got out")
    data = buf.getvalue()
    with pytest.raises(PluginBundleError):
        extract_plugin_bundle(data, tmp_path)
