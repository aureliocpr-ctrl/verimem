"""TDD — provenance signing on the write-path (SMSR arXiv 2606.12703 via the
cortex research bridge, action #2): SMSR's Theorem 1 — no deterministic
provenance-FREE filter certifies safety against an adaptive multi-session
adversary. The truth-gate (what deserves admission) needs the complementary
provenance-gate (who is speaking, unforgeably). The signature lives INSIDE the
verified_by ref (``source-doc:X:t1#sig=<hmac>``) — zero schema change,
self-contained, canonical_source untouched.
"""
from __future__ import annotations

import pytest

from engram.provenance_signing import (
    audit_store,
    sign_ref,
    verify_fact_refs,
    verify_ref,
)
from engram.source_trust import canonical_source

KEY = "test-key-do-not-ship"


def test_sign_and_verify_roundtrip():
    ref = sign_ref("source-doc:alice:t1", "Rex is a labrador.", key=KEY)
    assert ref.startswith("source-doc:alice:t1#sig=")
    assert verify_ref(ref, "Rex is a labrador.", key=KEY) is True
    # any tampering breaks it: proposition, ref body, or signature
    assert verify_ref(ref, "Rex is a poodle.", key=KEY) is False
    tampered = ref.replace("alice", "mallory")
    assert verify_ref(tampered, "Rex is a labrador.", key=KEY) is False
    assert verify_ref(ref, "Rex is a labrador.", key="other-key") is False


def test_unsigned_ref_verifies_false_but_parses_fine():
    assert verify_ref("source-doc:alice:t1", "x", key=KEY) is False
    # the signed ref still canonicalises to the same source (regex untouched)
    ref = sign_ref("source-doc:alice:t1", "x", key=KEY)
    assert canonical_source([ref]) == "alice"


def test_verify_fact_refs_all_must_hold():
    class _F:  # minimal fact stub
        proposition = "Rex is a labrador."
        verified_by = [sign_ref("source-doc:alice:t1", "Rex is a labrador.", key=KEY),
                       "actor:composer:r1"]        # actor refs are exempt (P85 self-sig is separate)
    assert verify_fact_refs(_F, key=KEY) == {"signed": 1, "unsigned": 0,
                                             "invalid": 0, "exempt": 1,
                                             "ok": True}
    class _G:
        proposition = "Rex is a labrador."
        verified_by = ["source-doc:bob:t9"]
    out = verify_fact_refs(_G, key=KEY)
    assert out["unsigned"] == 1 and out["ok"] is False


def test_audit_store_counts_and_names_offenders(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    from engram.client import Memory
    m = Memory(tmp_path / "s.db")
    good = m.add("Rex is a labrador.", topic="pets",
                 verified_by=[sign_ref("source-doc:alice:t1",
                                       "Rex is a labrador.", key=KEY)])
    bad = m.add("Rex is a poodle.", topic="pets",
                verified_by=["source-doc:mallory:t2"])
    rep = audit_store(m.semantic, key=KEY)
    assert rep["facts_checked"] >= 2
    assert rep["fully_signed"] >= 1
    assert bad["id"] in rep["offender_ids"]
    assert good["id"] not in rep["offender_ids"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
