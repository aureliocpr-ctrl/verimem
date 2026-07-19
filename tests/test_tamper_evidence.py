"""Tamper-evidence hash-chain primitives (task #24, foundation).

Pure, deterministic core: each log entry is hashed together with the previous
entry's hash, so any edit, deletion, insertion or reordering of a past entry breaks
the chain from that point on. This is the substrate the adjudication audit log gets
chained with; the EXTERNAL anchor (where the verified head is published so a DB-writer
cannot silently rewrite the whole chain) is a deployment/scope decision layered on top
— NOT in this module. A chain that lives only inside the same DB an attacker can write
is theatre; these primitives are honest about being only the tamper-DETECTION half.
"""
from __future__ import annotations

from verimem.tamper_evidence import (
    GENESIS_HASH,
    build_chain,
    entry_hash,
    verify_chain,
)


def _entries() -> list[dict]:
    return [
        {"id": "a", "disposition": "admitted", "proposition": "the sky is blue"},
        {"id": "b", "disposition": "quarantined", "proposition": "the sky is green"},
        {"id": "c", "disposition": "rejected", "proposition": "2+2=5"},
    ]


def test_entry_hash_is_deterministic_and_key_order_independent():
    a = entry_hash({"x": 1, "y": 2}, GENESIS_HASH)
    b = entry_hash({"y": 2, "x": 1}, GENESIS_HASH)  # same content, different order
    assert a == b and len(a) == 64  # sha256 hex


def test_entry_hash_depends_on_prev_hash():
    e = {"x": 1}
    assert entry_hash(e, GENESIS_HASH) != entry_hash(e, "f" * 64)


def test_build_chain_is_deterministic():
    assert build_chain(_entries()) == build_chain(_entries())
    assert len(build_chain(_entries())) == 3


def test_verify_intact_chain_returns_none():
    entries = _entries()
    hashes = build_chain(entries)
    assert verify_chain(entries, hashes) is None


def test_edit_of_a_past_entry_is_detected():
    entries = _entries()
    hashes = build_chain(entries)
    entries[1] = {**entries[1], "disposition": "admitted"}  # flip a quarantine → admit
    assert verify_chain(entries, hashes) == 1  # first break at the edited entry


def test_deleting_an_entry_breaks_the_chain():
    entries = _entries()
    hashes = build_chain(entries)
    del entries[1]                       # drop the quarantine record to hide it
    assert verify_chain(entries, hashes) is not None


def test_reordering_is_detected():
    entries = _entries()
    hashes = build_chain(entries)
    entries[0], entries[1] = entries[1], entries[0]
    assert verify_chain(entries, hashes) == 0


def test_appending_a_new_entry_keeps_the_prefix_valid():
    # extending the log is legitimate — the prior head still verifies the prefix.
    entries = _entries()
    hashes = build_chain(entries)
    entries.append({"id": "d", "disposition": "admitted", "proposition": "grass is green"})
    new_hashes = build_chain(entries)
    assert new_hashes[:3] == hashes            # prefix unchanged (append-only)
    assert verify_chain(entries, new_hashes) is None
