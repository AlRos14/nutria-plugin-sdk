"""
ECDSA-P256 plugin manifest signing and verification.

Trusted public keys are configured via the NUTRIA_PLUGIN_TRUSTED_KEYS
environment variable — a JSON array of PEM-encoded EC public keys:

    NUTRIA_PLUGIN_TRUSTED_KEYS='["-----BEGIN PUBLIC KEY-----\\n..."]'

CLI:
    nutria-plugin keygen               # generate a key pair
    nutria-plugin sign plugin.json     # sign a manifest in-place
"""

from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


class SignatureStatus(str, Enum):
    """Result of a manifest signature verification attempt."""

    VERIFIED = "verified"   # Signature present and valid against a trusted key
    MISSING = "missing"     # No signature field, or NUTRIA_PLUGIN_TRUSTED_KEYS not set
    INVALID = "invalid"     # Signature present but verification failed


def generate_keypair() -> tuple[str, str]:
    """Generate an ECDSA P-256 key pair.

    Returns:
        Tuple of (private_key_pem, public_key_pem) as strings.
    """
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


def _canonical_payload(manifest_dict: dict) -> bytes:
    """Return a deterministic JSON representation of the manifest for signing.

    The 'signature' field is excluded so the payload is stable whether the
    manifest is pre- or post-signing.
    """
    data = {k: v for k, v in manifest_dict.items() if k != "signature"}
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def sign_manifest(manifest_dict: dict, private_key_pem: str) -> str:
    """Sign a plugin manifest dict and return the hex-encoded DER signature.

    The returned value should be stored in manifest_dict['signature'].
    """
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"), password=None
    )
    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise TypeError("Private key must be an EC key")
    return private_key.sign(_canonical_payload(manifest_dict), ec.ECDSA(hashes.SHA256())).hex()


def _load_trusted_public_keys() -> list[ec.EllipticCurvePublicKey]:
    """Load trusted EC public keys from NUTRIA_PLUGIN_TRUSTED_KEYS.

    Returns an empty list when the env var is not set.
    Raises ValueError when the env var is set but malformed — so a typo in
    production fails loudly instead of silently accepting all plugins.
    """
    raw = os.environ.get("NUTRIA_PLUGIN_TRUSTED_KEYS", "")
    if not raw:
        return []
    try:
        pem_list: list[str] = json.loads(raw)
        if not isinstance(pem_list, list):
            raise ValueError("NUTRIA_PLUGIN_TRUSTED_KEYS must be a JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"NUTRIA_PLUGIN_TRUSTED_KEYS is set but invalid: {exc}") from exc

    keys: list[ec.EllipticCurvePublicKey] = []
    for pem in pem_list:
        try:
            key = serialization.load_pem_public_key(pem.encode("utf-8"))
            if isinstance(key, ec.EllipticCurvePublicKey):
                keys.append(key)
        except Exception:
            pass  # skip individual bad keys; caller gets fewer trusted keys
    return keys


def verify_manifest(manifest_dict: dict) -> SignatureStatus:
    """Verify the ECDSA signature embedded in a plugin manifest dict.

    Returns:
        SignatureStatus.VERIFIED  – valid against at least one trusted key
        SignatureStatus.MISSING   – no signature field, or keys not configured
        SignatureStatus.INVALID   – signature present but verification failed

    Raises:
        ValueError: if NUTRIA_PLUGIN_TRUSTED_KEYS is set but malformed.
    """
    sig_hex: Optional[str] = manifest_dict.get("signature")
    if not sig_hex:
        return SignatureStatus.MISSING

    try:
        sig_der = bytes.fromhex(sig_hex)
    except ValueError:
        return SignatureStatus.INVALID

    payload = _canonical_payload(manifest_dict)
    trusted_keys = _load_trusted_public_keys()  # may raise ValueError

    if not trusted_keys:
        return SignatureStatus.MISSING

    for key in trusted_keys:
        try:
            key.verify(sig_der, payload, ec.ECDSA(hashes.SHA256()))
            return SignatureStatus.VERIFIED
        except InvalidSignature:
            continue
        except Exception:
            continue

    return SignatureStatus.INVALID
