"""SDK end-to-end: same-source EVOLUTION supersession (task #48 enforce).

With the contradiction moat ENFORCING and ENGRAM_SUPERSEDE_SAME_SOURCE opted in, a newer
write from the SAME source that clashes with a stored value ADMITS the new fact and
RETIRES the old one (superseded_by) — the evolving-facts differentiator. A cross-source
clash, or the flag off, must NOT supersede (quarantine the new instead) — the griefing
guard + safe default.

Only the two heavy models are faked (embedder → constant vector so the cosine pre-filter
passes; NLI classifier → a contradiction verdict). The gate classification, the
supersede routing and the handler's admit-then-retire are the real code.
"""
from __future__ import annotations

import numpy as np

from verimem import Memory, embedding, local_relation
from verimem.local_relation import LocalRelationJudge


def _force_contradiction(monkeypatch):
    monkeypatch.setattr(embedding, "encode", lambda text: np.array([1.0, 0.0, 0.0]))
    local_relation.set_local_relation_judge(LocalRelationJudge(
        classifier=lambda pairs: [
            {"contradiction": 0.9, "entailment": 0.0, "neutral": 0.1} for _ in pairs]))


def test_same_source_evolution_admits_new_and_retires_old(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    _force_contradiction(monkeypatch)
    try:
        mem = Memory(path=tmp_path / "sem" / "sem.db")
        r1 = mem.add("Alice lives in Rome", topic="person/alice",
                     verified_by=["source-doc:acme:1"], validate="full")
        r2 = mem.add("Alice lives in Paris", topic="person/alice",
                     verified_by=["source-doc:acme:1"], validate="full")
    finally:
        local_relation.set_local_relation_judge(None)
    assert r2["status"] != "quarantined"                       # new admitted
    assert mem.semantic.get(r1["id"]).superseded_by == r2["id"]  # old retired


def test_numeric_same_source_evolution_supersedes(tmp_path, monkeypatch):
    """E2E 2026-07-19: a same-source NUMERIC evolution is caught by the LEXICAL L3 (not
    the NLI), which was routing it to quarantine-the-new. It must supersede like any
    other evolution. No NLI needed — numeric contradiction is deterministic."""
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)   # lexical path only
    mem = Memory(path=tmp_path / "sem" / "sem.db")
    r1 = mem.add("The subscription costs 100 euros per month.", topic="pricing/plan",
                 verified_by=["source-doc:billing:1"], validate="full")
    r2 = mem.add("The subscription costs 150 euros per month.", topic="pricing/plan",
                 verified_by=["source-doc:billing:1"], validate="full")
    assert r2["status"] != "quarantined"                         # new admitted
    assert mem.semantic.get(r1["id"]).superseded_by == r2["id"]  # old retired


def test_numeric_cross_source_still_quarantines(tmp_path, monkeypatch):
    """A cross-source numeric clash is a real conflict — quarantine the new, retire
    nothing (the griefing guard holds on the lexical path too)."""
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)
    mem = Memory(path=tmp_path / "sem" / "sem.db")
    r1 = mem.add("The subscription costs 100 euros per month.", topic="pricing/plan",
                 verified_by=["source-doc:billing:1"], validate="full")
    r2 = mem.add("The subscription costs 150 euros per month.", topic="pricing/plan",
                 verified_by=["source-doc:rogue:9"], validate="full")   # DIFFERENT source
    assert mem.semantic.get(r1["id"]).superseded_by is None       # first NOT retired
    assert r2["status"] == "quarantined"                          # conflict → quarantined


def test_cross_source_clash_does_not_supersede(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    _force_contradiction(monkeypatch)
    try:
        mem = Memory(path=tmp_path / "sem" / "sem.db")
        r1 = mem.add("Alice lives in Rome", topic="person/alice",
                     verified_by=["source-doc:acme:1"], validate="full")
        mem.add("Alice lives in Paris", topic="person/alice",
                verified_by=["source-doc:globex:9"], validate="full")  # DIFFERENT source
    finally:
        local_relation.set_local_relation_judge(None)
    assert mem.semantic.get(r1["id"]).superseded_by is None     # NOT retired (griefing guard)


def test_backfill_does_not_retire_current_value(tmp_path, monkeypatch):
    """FIX (opus critic P2): a same-source re-assertion of an OLD value (asserted_at in
    the past) must NOT retire the current value — valid-time threaded through the gate,
    not the candidate's always-now write-time."""
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    _force_contradiction(monkeypatch)
    try:
        mem = Memory(path=tmp_path / "sem" / "sem.db")
        r_current = mem.add("Alice lives in Paris", topic="person/alice",
                            verified_by=["source-doc:acme:1"],
                            asserted_at=2_000_000_000.0, validate="full")
        mem.add("Alice lives in Rome", topic="person/alice",   # backfill of an OLD value
                verified_by=["source-doc:acme:1"],
                asserted_at=1_000_000_000.0, validate="full")
    finally:
        local_relation.set_local_relation_judge(None)
    assert mem.semantic.get(r_current["id"]).superseded_by is None   # current NOT retired


def test_flag_explicitly_disabled_does_not_supersede(tmp_path, monkeypatch):
    """The escape hatch: ENGRAM_SUPERSEDE_SAME_SOURCE=0 disables the (default-on)
    supersession — an evolution falls back to quarantine-the-new."""
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "0")  # explicitly disabled
    _force_contradiction(monkeypatch)
    try:
        mem = Memory(path=tmp_path / "sem" / "sem.db")
        r1 = mem.add("Alice lives in Rome", topic="person/alice",
                     verified_by=["source-doc:acme:1"], validate="full")
        mem.add("Alice lives in Paris", topic="person/alice",
                verified_by=["source-doc:acme:1"], validate="full")
    finally:
        local_relation.set_local_relation_judge(None)
    assert mem.semantic.get(r1["id"]).superseded_by is None     # safe default: not retired


# --- lexical expansion 0.7.0: version / date / negation reach the DEFAULT moat ---
# Mandate 2026-07-19 ("non castrare, espandi"): the zero-config claim
# "numeric/version/date/negation" must be TRUE with NO NLI tier loaded.

def _lexical_only(monkeypatch):
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)
    monkeypatch.delenv("ENGRAM_SUPERSEDE_SAME_SOURCE", raising=False)  # default ON


def _evolves(mem, old_text, new_text):
    src = ["source-doc:acme:9"]
    r1 = mem.add(old_text, topic="evo/x", verified_by=src, validate="full")
    r2 = mem.add(new_text, topic="evo/x", verified_by=src, validate="full")
    assert r2["status"] != "quarantined", f"new write quarantined: {r2}"
    assert r1["id"] in (r2.get("superseded") or []), f"old not superseded: {r2}"
    assert mem.semantic.get(r1["id"]).superseded_by == r2["id"]


def test_version_same_source_evolution_supersedes_lexically(tmp_path, monkeypatch):
    _lexical_only(monkeypatch)
    _evolves(Memory(path=tmp_path / "v.db"),
             "Orion ships on version 2.3.1.",
             "Orion ships on version 4.0.0.")


def test_month_date_same_source_evolution_supersedes_lexically(tmp_path, monkeypatch):
    _lexical_only(monkeypatch)
    _evolves(Memory(path=tmp_path / "m.db"),
             "Project Aurora launches in March 2025.",
             "Project Aurora launches in September 2025.")


def test_iso_date_same_source_evolution_supersedes_lexically(tmp_path, monkeypatch):
    _lexical_only(monkeypatch)
    _evolves(Memory(path=tmp_path / "d.db"),
             "The compliance audit is on 2025-03-06.",
             "The compliance audit is on 2025-09-20.")


def test_negation_same_source_evolution_supersedes_lexically(tmp_path, monkeypatch):
    _lexical_only(monkeypatch)
    _evolves(Memory(path=tmp_path / "n.db"),
             "The vendor contract is signed.",
             "The vendor contract is not signed.")
