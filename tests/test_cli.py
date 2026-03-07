"""Tests for the nutria-plugin CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from nutria_plugin.cli import main


def test_cli_keygen(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = main(["keygen", "--out", "mykey"])
    assert result == 0
    assert (tmp_path / "mykey.pem").exists()
    assert (tmp_path / "mykey.pub.pem").exists()


def test_cli_keygen_path_traversal_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = main(["keygen", "--out", "../../../tmp/evil"])
    assert result == 1


def test_cli_new_and_validate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = main(["new", "test-plugin", "--name", "Test Plugin", "--dir", str(tmp_path / "out")])
    assert result == 0

    result = main(["validate", str(tmp_path / "out")])
    assert result == 0


def test_cli_validate_invalid_dir(tmp_path):
    result = main(["validate", str(tmp_path)])
    assert result == 1


def test_cli_pack(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["new", "cli-plugin", "--dir", str(tmp_path / "plugin")])
    result = main(["pack", str(tmp_path / "plugin"), "-o", str(tmp_path / "out.zip")])
    assert result == 0
    assert (tmp_path / "out.zip").exists()


def test_cli_sign(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["new", "sign-plugin", "--dir", str(tmp_path / "plugin")])
    main(["keygen", "--out", str(tmp_path / "key")])
    result = main(["sign", str(tmp_path / "plugin" / "plugin.json"), "--key", str(tmp_path / "key.pem")])
    assert result == 0
    manifest_dict = json.loads((tmp_path / "plugin" / "plugin.json").read_text())
    assert "signature" in manifest_dict


def test_cli_sign_missing_manifest(tmp_path):
    result = main(["sign", str(tmp_path / "nonexistent.json"), "--key", "dummy.pem"])
    assert result == 1


def test_cli_sign_missing_key(tmp_path):
    manifest = tmp_path / "plugin.json"
    manifest.write_text("{}")
    result = main(["sign", str(manifest), "--key", str(tmp_path / "nope.pem")])
    assert result == 1
