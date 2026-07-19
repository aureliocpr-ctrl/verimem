"""Tamper-evidence hash-chain primitives (task #24, foundation).

Each log entry is hashed together with the previous entry's hash
(``entry_hash = sha256(prev_hash || canonical(entry))``), so any edit, deletion,
insertion or reordering of a past entry changes every hash from that point on and is
detectable by recomputation. This is the tamper-DETECTION half of an audit trail.

What this module deliberately is NOT: it does not make an audit log tamper-PROOF. An
attacker who can write the DB can also recompute the whole chain. Real tamper-evidence
needs the verified HEAD published to somewhere the DB-writer cannot rewrite (an
external append-only sink, a signature under an external key, a transparency/timestamp
service) — a deployment/scope decision layered on top of these primitives, never a
chain that lives only inside the same DB (that is theatre). Keeping that boundary
explicit is the honest contract.

Pure and dependency-free (hashlib + json): unit-testable with plain dicts, and reusable
by any store that wants a verifiable append-only log.
"""
from __future__ import annotations

import hashlib
import json

__all__ = ["GENESIS_HASH", "canonical_bytes", "entry_hash", "build_chain",
           "verify_chain"]

#: The chain's fixed starting link (before any entry). 64 hex zeros = "no predecessor".
GENESIS_HASH = "0" * 64


def canonical_bytes(entry: dict) -> bytes:
    """Deterministic serialization of an entry: JSON with sorted keys, no incidental
    whitespace, ASCII-escaped — so key order and formatting can never change the hash
    (two dicts with the same content hash identically)."""
    return json.dumps(entry, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, default=str).encode("utf-8")


def entry_hash(entry: dict, prev_hash: str) -> str:
    """``sha256(prev_hash || 0x00 || canonical(entry))`` as hex. The domain-separator
    byte keeps the prev-hash and the payload from running together."""
    h = hashlib.sha256()
    h.update(str(prev_hash).encode("utf-8"))
    h.update(b"\x00")
    h.update(canonical_bytes(entry))
    return h.hexdigest()


def build_chain(entries: list[dict], *, genesis: str = GENESIS_HASH) -> list[str]:
    """Running entry-hash after each entry: ``out[i]`` chains ``entries[0..i]``, so
    ``out[-1]`` is the head that certifies the whole log. Append-only by construction —
    appending an entry never changes an earlier hash."""
    out: list[str] = []
    prev = genesis
    for e in entries:
        prev = entry_hash(e, prev)
        out.append(prev)
    return out


def verify_chain(entries: list[dict], hashes: list[str], *,
                 genesis: str = GENESIS_HASH) -> int | None:
    """Recompute the chain and return the index of the FIRST entry whose stored hash
    does not match — i.e. the point of tamper (edited content, a broken prev-link from
    a deletion/insertion, or reordering). ``None`` when the chain is fully intact.

    A length mismatch (truncation or an inserted row) is reported at the first index
    that cannot be reconciled, so a caller never reads it as "intact"."""
    if len(entries) != len(hashes):
        return min(len(entries), len(hashes))
    prev = genesis
    for i, (e, h) in enumerate(zip(entries, hashes, strict=True)):
        prev = entry_hash(e, prev)
        if prev != h:
            return i
    return None

# ---------------------------------------------------------------------------
# Anchor-B (task #24): the chain head signed with an EXTERNAL ed25519 key.
#
# Anchor-A exports the head for the operator to archive; an attacker who owns
# the DB can recompute the whole chain but CANNOT forge a head signed by a key
# that never lives in the DB-writing process. The private key is a PEM file
# the OPERATOR manages (VERIMEM_AUDIT_SIGNING_KEY) -- verimem never stores it.
# ed25519 via the optional ``cryptography`` package (extra ``verimem[audit]``);
# a configured key with the package missing raises loudly -- an operator who
# ASKED for signing must never silently not get it.
#
# Honest scope: B detects forgery of the head GIVEN the key stays external.
# It does not add C's public timestamping (air-gap-friendly by design).
# ---------------------------------------------------------------------------

def _require_crypto():
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
    except ImportError as exc:  # pragma: no cover -- environment-dependent
        raise RuntimeError(
            "audit head signing requires the 'cryptography' package - "
            "install verimem[audit]") from exc
    return serialization, Ed25519PrivateKey, Ed25519PublicKey


def generate_audit_keypair(directory) -> tuple:
    """Generate an ed25519 keypair for audit-head signing; returns
    ``(private_pem_path, public_pem_path)``. Run this OUTSIDE the process
    that writes the audit DB and keep the private key out of its reach --
    that separation is the whole point of anchor-B."""
    from pathlib import Path
    serialization, Ed25519PrivateKey, _pub = _require_crypto()
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    priv = d / "verimem-audit-signing.pem"
    pub = d / "verimem-audit-signing.pub.pem"
    priv.write_bytes(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    pub.write_bytes(key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    return priv, pub


def sign_head(head_hash: str, private_key_path) -> str:
    """Sign a chain head with the operator's ed25519 private key; returns the
    base64 signature to archive NEXT TO the head."""
    import base64
    serialization, _priv, _pub = _require_crypto()
    key = serialization.load_pem_private_key(
        open(private_key_path, "rb").read(), password=None)
    sig = key.sign(str(head_hash).encode("utf-8"))
    return base64.b64encode(sig).decode("ascii")


def verify_head_signature(head_hash: str, signature_b64: str,
                          public_key_path) -> bool:
    """True iff ``signature_b64`` is a valid signature of ``head_hash`` under
    the public key -- ANY failure (garbage b64, wrong key, wrong head) is
    ``False``, never an exception: verification is a yes/no question."""
    import base64
    try:
        serialization, _priv, _pub = _require_crypto()
        key = serialization.load_pem_public_key(
            open(public_key_path, "rb").read())
        key.verify(base64.b64decode(signature_b64),
                   str(head_hash).encode("utf-8"))
        return True
    except Exception:  # noqa: BLE001 -- verification is boolean by contract
        return False

