"""
nutria-plugin CLI

Commands:
  keygen    Generate an ECDSA P-256 key pair for manifest signing
  sign      Sign a plugin manifest in-place
  new       Scaffold a new plugin directory
  pack      Validate and pack a plugin directory into a ZIP bundle
  validate  Validate a plugin directory without packing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _cmd_keygen(args: argparse.Namespace) -> int:
    from .signing import generate_keypair

    out_stem = Path(args.out)
    # Reject path traversal in the output stem
    try:
        resolved = out_stem.resolve()
        cwd = Path.cwd().resolve()
        resolved.relative_to(cwd)
    except ValueError:
        print(f"error: --out path must be within the current directory", file=sys.stderr)
        return 1

    private_pem, public_pem = generate_keypair()
    priv_file = out_stem.with_suffix(".pem")
    pub_file = out_stem.with_suffix(".pub.pem")
    priv_file.write_text(private_pem, encoding="utf-8")
    pub_file.write_text(public_pem, encoding="utf-8")
    print(f"Private key: {priv_file}")
    print(f"Public key:  {pub_file}")
    print()
    print("Add the public key to NUTRIA_PLUGIN_TRUSTED_KEYS:")
    print(json.dumps([public_pem]))
    return 0


def _cmd_sign(args: argparse.Namespace) -> int:
    from .signing import sign_manifest

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"error: {manifest_path} not found", file=sys.stderr)
        return 1

    key_path = Path(args.key)
    if not key_path.exists():
        print(f"error: {key_path} not found", file=sys.stderr)
        return 1

    private_pem = key_path.read_text(encoding="utf-8")
    raw_dict = json.loads(manifest_path.read_text(encoding="utf-8"))
    sig_hex = sign_manifest(raw_dict, private_pem)
    raw_dict["signature"] = sig_hex
    manifest_path.write_text(json.dumps(raw_dict, indent=2) + "\n", encoding="utf-8")
    print(f"Signed: {manifest_path}")
    return 0


def _cmd_new(args: argparse.Namespace) -> int:
    from .packaging import PackagingError, scaffold_plugin

    target = Path(args.dir or args.id)
    try:
        scaffold_plugin(target, plugin_id=args.id, name=args.name)
        print(f"Created plugin scaffold in: {target}")
        return 0
    except PackagingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _cmd_pack(args: argparse.Namespace) -> int:
    from .packaging import PackagingError, pack_plugin

    plugin_dir = Path(args.dir)
    output = Path(args.output) if args.output else None

    private_pem: str | None = None
    if args.key:
        key_path = Path(args.key)
        if not key_path.exists():
            print(f"error: {key_path} not found", file=sys.stderr)
            return 1
        private_pem = key_path.read_text(encoding="utf-8")

    try:
        out_path = pack_plugin(plugin_dir, output, sign=bool(args.key), private_key_pem=private_pem)
        print(f"Packed: {out_path}")
        return 0
    except PackagingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _cmd_validate(args: argparse.Namespace) -> int:
    from .packaging import validate_plugin_dir

    plugin_dir = Path(args.dir)
    errors = validate_plugin_dir(plugin_dir)
    if errors:
        print("Validation errors:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nutria-plugin",
        description="Nutria plugin SDK CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_keygen = sub.add_parser("keygen", help="Generate an ECDSA P-256 key pair")
    p_keygen.add_argument("--out", default="nutria-plugin", help="Output file stem (no extension)")

    p_sign = sub.add_parser("sign", help="Sign a plugin manifest in-place")
    p_sign.add_argument("manifest", nargs="?", default="plugin.json", help="Path to plugin.json")
    p_sign.add_argument("--key", required=True, help="Path to private key PEM file")

    p_new = sub.add_parser("new", help="Scaffold a new plugin directory")
    p_new.add_argument("id", help="Plugin ID (e.g. my-plugin)")
    p_new.add_argument("--name", help="Human-readable plugin name")
    p_new.add_argument("--dir", help="Target directory (defaults to plugin ID)")

    p_pack = sub.add_parser("pack", help="Validate and pack a plugin ZIP")
    p_pack.add_argument("dir", nargs="?", default=".", help="Plugin directory to pack")
    p_pack.add_argument("--output", "-o", help="Output ZIP path")
    p_pack.add_argument("--key", help="Sign with this private key PEM file")

    p_validate = sub.add_parser("validate", help="Validate a plugin directory")
    p_validate.add_argument("dir", nargs="?", default=".", help="Plugin directory to validate")

    args = parser.parse_args(argv)
    handlers = {
        "keygen": _cmd_keygen,
        "sign": _cmd_sign,
        "new": _cmd_new,
        "pack": _cmd_pack,
        "validate": _cmd_validate,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
