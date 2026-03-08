# Security — Signing, Trust, and ZIP Safety

## Plugin signing

Signing lets Nutria administrators verify that a plugin ZIP was produced by a
trusted publisher and has not been tampered with after publication.

Signing is optional but strongly recommended for plugins distributed to
third-party Nutria instances.

### How it works

1. The publisher generates an ECDSA P-256 key pair.
2. Before packing, the manifest fields are serialized to a canonical JSON
   representation (alphabetically sorted keys, no whitespace) and the
   `signature` field is excluded.
3. The SHA-256 digest of that payload is signed with the private key using
   deterministic ECDSA (RFC 6979).
4. The DER-encoded signature is hex-encoded and stored in `plugin.json`
   as the `signature` field.
5. At install time, Nutria verifies the signature against the list of trusted
   public keys configured by the administrator.

### Generating a key pair

```bash
nutria-plugin keygen --out my-publisher-key
# Private key: my-publisher-key.pem     ← store securely, never commit
# Public key:  my-publisher-key.pub.pem ← distribute to Nutria instances
```

The private key is a PEM-encoded ECDSA P-256 key. Keep it secret.
The public key is the corresponding PEM-encoded public key to be
registered with each Nutria instance that will accept your plugins.

### Signing a manifest

Sign in-place (modifies `plugin.json`):

```bash
nutria-plugin sign plugin.json --key my-publisher-key.pem
```

Sign during pack (signs and packs in one step):

```bash
nutria-plugin pack . --key my-publisher-key.pem --output my-plugin-0.1.0.zip
```

### Registering trusted keys on a Nutria instance

Set the `NUTRIA_PLUGIN_TRUSTED_KEYS` environment variable to a JSON array
of PEM public key strings (newlines as `\n`):

```bash
export NUTRIA_PLUGIN_TRUSTED_KEYS='[
  "-----BEGIN PUBLIC KEY-----\nMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...\n-----END PUBLIC KEY-----"
]'
```

### Signature verification behaviour

| Situation | Result |
|-----------|--------|
| Valid signature, key in trusted list | `SignatureStatus.VERIFIED` |
| Manifest modified after signing | `SignatureStatus.INVALID` |
| Signature present but key not trusted | `SignatureStatus.UNTRUSTED` |
| No signature in manifest | `SignatureStatus.UNSIGNED` |
| No trusted keys configured | `SignatureStatus.MISSING` |

Nutria instances can be configured to:
- **Allow unsigned plugins** (default in development)
- **Require signed plugins** — reject `UNSIGNED` and `MISSING`
- **Require trusted signatures** — only accept `VERIFIED`

---

## ZIP security rules

The SDK enforces these rules both at pack time and at install time.

### Allowed file extensions (allowlist)

Only the following extensions are permitted inside a plugin ZIP:

```
.json  .md  .yaml  .yml  .txt  .png  .jpg  .jpeg  .svg  .ico
.pdf  .wsdl  .xsd  .xml  .csv
```

Any other extension (`.py`, `.js`, `.sh`, `.exe`, `.rb`, `.php`, etc.) is
rejected. This prevents code injection through plugin installation.

### Path safety

- No absolute paths (e.g. `/etc/passwd`)
- No path traversal components (`..` in any segment)
- No empty path segments

These are checked on the normalized `PurePosixPath` representation.

### No hidden files or symlinks

- Files and directories starting with `.` (hidden) are not packed and not
  accepted in ZIPs.
- Symlinks in the plugin source directory cause a `PackagingError` at pack time.

### Size limits

| Limit | Value |
|-------|-------|
| Maximum ZIP file size | 20 MB |
| Maximum uncompressed size (decompression bomb guard) | 100 MB |

The uncompressed size check prevents decompression bomb attacks by checking
`ZipInfo.file_size` before extraction.

---

## Secrets handling

**Secrets are never stored in the plugin ZIP.** The `required_secrets` field
in `plugin.json` contains only secret *names* — the actual values are
configured after installation by the Nutria administrator.

**Do not:**
- Put API keys, tokens, or passwords in `plugin.json`
- Put credentials in connection JSON files
- Put credentials in SKILL.md or context docs
- Commit `.env` files to your plugin repository

**Do:**
- List secret names in `required_secrets`
- Reference secret names in connection auth config (e.g. `"secret": "MY_KEY"`)
- Document required secrets in `README.md` with descriptions

---

## SSRF protection

`remote_endpoints` in `plugin.json` is validated at install time against an
IP address blocklist:

- Loopback: `127.0.0.0/8`, `::1`
- Private: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- Link-local: `169.254.0.0/16`, `fe80::/10`
- Reserved ranges
- `localhost`, `localhost.localdomain`

IP literal URLs that resolve to these ranges are blocked even if they use
a domain name. Hostname-based URLs are validated at install time but also
re-checked at runtime by the Nutria execution engine.

---

## Supply chain considerations

- Always publish your public key alongside your plugin releases.
- Use different signing keys for different publishers or environments.
- Rotate keys periodically; remove revoked keys from `NUTRIA_PLUGIN_TRUSTED_KEYS`.
- Pin the `nutria-plugin` SDK version in your plugin build tooling.
- Review connection files and WSDLs from third-party plugins before installing.
