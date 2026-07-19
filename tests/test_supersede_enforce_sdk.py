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


def test_flag_off_does_not_supersede(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    monkeypatch.delenv("ENGRAM_SUPERSEDE_SAME_SOURCE", raising=False)  # default off
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
