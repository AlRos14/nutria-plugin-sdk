"""Tests for ECDSA-P256 signing and verification."""

from __future__ import annotations

import json
import os

import pytest

from nutria_plugin.signing import (
    SignatureStatus,
    _canonical_payload,
    generate_keypair,
    sign_manifest,
    verify_manifest,
)


def _minimal_dict(**overrides) -> dict:
    base = {
        "schema_version": "1.0",
        "id": "test-plugin",
        "name": "Test",
        "version": "1.0.0",
        "description": "d",
        "author": "a",
        "runtime_types": ["declarative_api"],
    }
    base.update(overrides)
    return base


def test_generate_keypair_returns_pem_strings():
    priv, pub = generate_keypair()
    assert "BEGIN PRIVATE KEY" in priv
    assert "BEGIN PUBLIC KEY" in pub


def test_keypairs_are_unique():
    priv1, pub1 = generate_keypair()
    priv2, pub2 = generate_keypair()
    assert priv1 != priv2
    assert pub1 != pub2


def test_canonical_payload_excludes_signature():
    data = _minimal_dict(signature="abc")
    payload = _canonical_payload(data)
    parsed = json.loads(payload)
    assert "signature" not in parsed


def test_canonical_payload_is_deterministic():
    data = _minimal_dict()
    assert _canonical_payload(data) == _canonical_payload(data)


def test_canonical_payload_sorted_keys():
    data1 = {"b": 2, "a": 1}
    data2 = {"a": 1, "b": 2}
    assert _canonical_payload(data1) == _canonical_payload(data2)


def test_sign_and_verify_success(monkeypatch):
    priv, pub = generate_keypair()
    data = _minimal_dict()
    sig = sign_manifest(data, priv)
    data["signature"] = sig

    monkeypatch.setenv("NUTRIA_PLUGIN_TRUSTED_KEYS", json.dumps([pub]))
    assert verify_manifest(data) == SignatureStatus.VERIFIED


def test_verify_missing_when_no_signature(monkeypatch):
    monkeypatch.setenv("NUTRIA_PLUGIN_TRUSTED_KEYS", json.dumps(["dummy"]))
    assert verify_manifest(_minimal_dict()) == SignatureStatus.MISSING


def test_verify_missing_when_no_trusted_keys(monkeypatch):
    monkeypatch.delenv("NUTRIA_PLUGIN_TRUSTED_KEYS", raising=False)
    priv, _ = generate_keypair()
    data = _minimal_dict()
    data["signature"] = sign_manifest(data, priv)
    assert verify_manifest(data) == SignatureStatus.MISSING


def test_verify_invalid_for_tampered_manifest(monkeypatch):
    priv, pub = generate_keypair()
    data = _minimal_dict()
    sig = sign_manifest(data, priv)
    data["signature"] = sig
    data["name"] = "Tampered!"  # modify after signing

    monkeypatch.setenv("NUTRIA_PLUGIN_TRUSTED_KEYS", json.dumps([pub]))
    assert verify_manifest(data) == SignatureStatus.INVALID


def test_verify_invalid_for_wrong_key(monkeypatch):
    priv1, _ = generate_keypair()
    _, pub2 = generate_keypair()
    data = _minimal_dict()
    data["signature"] = sign_manifest(data, priv1)

    monkeypatch.setenv("NUTRIA_PLUGIN_TRUSTED_KEYS", json.dumps([pub2]))
    assert verify_manifest(data) == SignatureStatus.INVALID


def test_verify_invalid_for_bad_hex_signature(monkeypatch):
    _, pub = generate_keypair()
    data = _minimal_dict(signature="not-valid-hex!")
    monkeypatch.setenv("NUTRIA_PLUGIN_TRUSTED_KEYS", json.dumps([pub]))
    assert verify_manifest(data) == SignatureStatus.INVALID


def test_malformed_trusted_keys_raises(monkeypatch):
    monkeypatch.setenv("NUTRIA_PLUGIN_TRUSTED_KEYS", "this is not json")
    data = _minimal_dict(signature="aabb")
    with pytest.raises(ValueError, match="NUTRIA_PLUGIN_TRUSTED_KEYS"):
        verify_manifest(data)


def test_sign_requires_ec_key():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = rsa_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    with pytest.raises(TypeError):
        sign_manifest(_minimal_dict(), pem)
