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
