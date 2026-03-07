"""Tests for scaffold, pack, and validate_plugin_dir."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nutria_plugin.packaging import (
    PackagingError,
    pack_plugin,
    scaffold_plugin,
    validate_plugin_dir,
)


def test_scaffold_creates_expected_files(tmp_path):
    target = tmp_path / "my-plugin"
    scaffold_plugin(target, "my-plugin", "My Plugin")
    assert (target / "plugin.json").exists()
    assert (target / "README.md").exists()
    assert (target / "hooks" / "hooks.json").exists()
    assert (target / "settings.schema.json").exists()


def test_scaffold_manifest_valid(tmp_path):
    from nutria_plugin.manifest import PluginManifest

    target = tmp_path / "p"
    scaffold_plugin(target, "demo-plugin")
    m = PluginManifest.from_file(target / "plugin.json")
    assert m.id == "demo-plugin"


def test_scaffold_no_overwrite_by_default(tmp_path):
    target = tmp_path / "p"
    scaffold_plugin(target, "p")
    with pytest.raises(PackagingError, match="already exists"):
        scaffold_plugin(target, "p")


def test_scaffold_overwrite_allowed(tmp_path):
    target = tmp_path / "p"
    scaffold_plugin(target, "p")
    scaffold_plugin(target, "p", overwrite=True)
    assert (target / "plugin.json").exists()


def test_pack_plugin_produces_zip(tmp_path):
    src = tmp_path / "myplugin"
    scaffold_plugin(src, "my-plugin", "My Plugin")
    out = tmp_path / "output.zip"
    result = pack_plugin(src, out)
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0


def test_pack_plugin_default_output_name(tmp_path):
    src = tmp_path / "myplugin"
    scaffold_plugin(src, "my-plugin")
    out = pack_plugin(src)
    assert out.name.startswith("my-plugin-")
    assert out.suffix == ".zip"
    out.unlink(missing_ok=True)


def test_pack_plugin_missing_manifest(tmp_path):
    src = tmp_path / "empty"
    src.mkdir()
    with pytest.raises(PackagingError, match="plugin.json"):
        pack_plugin(src)


def test_pack_plugin_rejects_blocked_type(tmp_path):
    src = tmp_path / "myplugin"
    scaffold_plugin(src, "my-plugin")
    (src / "evil.py").write_text("pass")
    with pytest.raises(PackagingError, match=".py"):
        pack_plugin(src, tmp_path / "out.zip")


def test_pack_plugin_with_signing(tmp_path):
    from nutria_plugin.signing import generate_keypair

    src = tmp_path / "myplugin"
    scaffold_plugin(src, "sign-plugin")
    priv, _ = generate_keypair()
    priv_path = tmp_path / "key.pem"
    priv_path.write_text(priv)

    out = tmp_path / "signed.zip"
    pack_plugin(src, out, sign=True, private_key_pem=priv)
    assert out.exists()

    manifest_dict = json.loads((src / "plugin.json").read_text())
    assert "signature" in manifest_dict


def test_validate_plugin_dir_valid(tmp_path):
    src = tmp_path / "myplugin"
    scaffold_plugin(src, "my-plugin")
    errors = validate_plugin_dir(src)
    assert errors == []


def test_validate_plugin_dir_missing_manifest(tmp_path):
    src = tmp_path / "empty"
    src.mkdir()
    errors = validate_plugin_dir(src)
    assert any("plugin.json" in e for e in errors)


def test_validate_plugin_dir_blocked_type(tmp_path):
    src = tmp_path / "myplugin"
    scaffold_plugin(src, "my-plugin")
    (src / "bad.py").write_text("pass")
    errors = validate_plugin_dir(src)
    assert any(".py" in e for e in errors)
