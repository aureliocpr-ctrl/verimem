"""Similarity fallback for reconcile candidates (task #21) — TDD.

Measured hole (mini-world v3, 2026-07-10): reconciliation finds candidates
by SHARED ENTITY only; on key-value facts the extractor does not link
("The access code of project_1 is ..."), so supersession NEVER fires even on
two directly conflicting facts. The fallback takes the top-k semantic
neighbours when the entity path yields nothing — same conflict filters,
behind ENGRAM_RECONCILE_SIM_FALLBACK=1, default OFF (entity path unchanged).
"""
from __future__ import annotations

import time

from verimem.client import Memory

DAY = 86400.0


def _two_conflicting_facts(mem: Memory):
    """The exact minimal case that does NOT supersede today. asserted_at is
    spaced 2 days so min_age_gap_days=1.0 cannot be the blocker."""
    now = time.time()
    r1 = mem.add("The access code of project_1 is aaa111.", topic="w",
                 verified_by=["source-doc:h1:t0"], asserted_at=now - 2 * DAY)
    r2 = mem.add("The access code of project_1 is bbb222.", topic="w",
                 verified_by=["source-doc:h2:t1"], asserted_at=now)
    return r1, r2


def test_sim_fallback_supersedes_the_minimal_case(tmp_path, monkeypatch):
    """Unit-level: the test-suite embedding STUB hashes whole strings, so its
    recall never returns near-neighbours — the similarity path is exercised
    by patching recall to return the older conflicting fact. The REAL
    end-to-end proof runs on the real embedder in the mini-world judge
    (source_trust_miniworld --reconcile)."""
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")  # call reconcile directly
    monkeypatch.setenv("ENGRAM_RECONCILE_SIM_FALLBACK", "1")
    mem = Memory(tmp_path / "m.db")
    r1, r2 = _two_conflicting_facts(mem)
    old_f = mem.semantic.get(r1["id"])
    new_f = mem.semantic.get(r2["id"])
    monkeypatch.setattr(mem.semantic, "recall",
                        lambda q, k=6, **kw: [(old_f, 0.9)])
    res = mem.semantic.reconcile_new_fact(new_f, auto_supersede=True)
    assert r1["id"] in res["superseded"], res
    assert getattr(mem.semantic.get(r1["id"]), "superseded_by", None) == r2["id"]


def test_sim_fallback_does_not_touch_unrelated_facts(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "1")
    monkeypatch.setenv("ENGRAM_RECONCILE_AUTO_SUPERSEDE", "1")
    monkeypatch.setenv("ENGRAM_RECONCILE_SIM_FALLBACK", "1")
    mem = Memory(tmp_path / "m.db")
    now = time.time()
    r1 = mem.add("The database port of service_alpha is 5432.", topic="w",
                 verified_by=["source-doc:h1:t0"], asserted_at=now - 2 * DAY)
    mem.add("The access code of project_9 is zzz999.", topic="w",
            verified_by=["source-doc:h2:t1"], asserted_at=now)
    assert not getattr(mem.semantic.get(r1["id"]), "superseded_by", None), (
        "different subject/attribute must never be superseded by similarity")
