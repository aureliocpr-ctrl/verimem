"""P1 wiring — reconcile-on-write, opt-in behind ENGRAM_RECONCILE_ON_WRITE.

Makes the prototype REACHABLE from the real write path (the production caller the
critic kept flagging as missing), fail-safe (contest, never auto-supersede), and
default-OFF so it changes nothing until explicitly enabled and measured.
"""
from __future__ import annotations

import time

from verimem.entity_kg import Entity
from verimem.semantic import Fact, SemanticMemory

_DAY = 86400.0


def test_reconcile_new_fact_contests_related(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    old = Fact(id="old", proposition="config X is 30s", topic="t",
               status="verified", confidence=0.9, created_at=now - 30 * _DAY)
    new = Fact(id="new", proposition="config X is 5s", topic="t",
               status="verified", confidence=0.9, created_at=now)
    sm.store(old)
    sm.store(new)
    es = sm._recall_entity_store()
    eid = es.store(Entity(canonical_name="config_x", type="config"))
    es.link_fact("old", eid)
    es.link_fact("new", eid)
    res = sm.reconcile_new_fact(new)
    assert "old" in res["contested"]
    assert sm.get("old").superseded_by is None, "fail-safe default: no supersede"


def test_store_does_not_reconcile_by_default(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("ENGRAM_RECONCILE_ON_WRITE", raising=False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    called: list = []
    monkeypatch.setattr(sm, "reconcile_new_fact",
                        lambda f, **k: called.append(getattr(f, "id", "")))
    sm.store(Fact(id="x", proposition="Acme Corp uses Postgres", topic="t"))
    assert called == [], "default OFF: no reconcile on write"


def test_store_triggers_reconcile_when_gated_on(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "1")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    called: list = []
    monkeypatch.setattr(
        sm, "reconcile_new_fact",
        lambda f, **k: (called.append(getattr(f, "id", "")),
                        {"superseded": [], "contested": []})[1])
    sm.store(Fact(id="acme", proposition="Acme Corp uses Postgres", topic="t"))
    assert "acme" in called, "gate ON: reconcile runs on the write path"
