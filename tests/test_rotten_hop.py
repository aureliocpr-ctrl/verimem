"""Rotten-hop invalidation in the reasoning dossier (task #20d) — TDD.

Transfer law L3: a derivation resting on a SUPERSEDED fact is stale — the
chain of custody must not present a replaced value as current. The fix
invalidates the DERIVATION (abstain, pointing at the rotten hop), never the
sources feeding it. A superseded fact is still in the store (get() returns
it with superseded_by set), so without this check the dossier silently cites
the old value.
"""
from __future__ import annotations

from engram.graph_reasoning import _dossier_for_path


class _FakeStore:
    def __init__(self, names):
        self._names = names

    def entity_name(self, eid):
        return self._names.get(eid, eid)


def _name(store, eid):
    return store._names.get(eid, eid)


class _FakeSemantic:
    def __init__(self, facts):
        self._facts = facts

    def get(self, fid):
        return self._facts.get(fid)


class _Fact:
    def __init__(self, fid, prop, superseded_by=None):
        self.id = fid
        self.proposition = prop
        self.superseded_by = superseded_by


def _path(fid):
    return {"target": "e2", "min_weight": 0.9, "path_weight": 0.9,
            "grounded": True,
            "hops": [{"src_entity": "e1", "dst_entity": "e2",
                      "predicate": "manages", "weight": 0.9,
                      "source_fact_id": fid}]}


def test_live_hop_produces_a_derivation(monkeypatch):
    import engram.graph_reasoning as gr
    monkeypatch.setattr(gr, "_entity_name", _name)
    store = _FakeStore({"e1": "Alice", "e2": "Project X"})
    sem = _FakeSemantic({"f1": _Fact("f1", "Alice manages Project X.")})
    out = _dossier_for_path(store, sem, "e1", _path("f1"))
    assert out["abstained"] is False and out["derivation"]


def test_superseded_hop_invalidates_the_derivation(monkeypatch):
    import engram.graph_reasoning as gr
    monkeypatch.setattr(gr, "_entity_name", _name)
    store = _FakeStore({"e1": "Alice", "e2": "Project X"})
    sem = _FakeSemantic({
        "f1": _Fact("f1", "Alice manages Project X.", superseded_by="f2")})
    out = _dossier_for_path(store, sem, "e1", _path("f1"))
    assert out["abstained"] is True and out["grounded"] is False
    assert out["answer"] is None
    assert "supersed" in out["reason"].lower()
    assert "f2" in out["reason"], "must point at the superseding fact"
