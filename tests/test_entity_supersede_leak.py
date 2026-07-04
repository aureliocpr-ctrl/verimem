"""Superseded/orphaned facts must NOT leak through entity/anchor recall
(correctness-hunt #3, HIGH-2).

entity_facts links are created under a live-fact filter but never removed
when a fact is later superseded/orphaned, and SemanticMemory.get() is an
unfiltered SELECT. So render_anchor_block (injected into every fresh
instance's SessionStart self-model) resolved a retracted fact's id via
get() and printed its STALE proposition as current memory.

Fix: SemanticMemory.get(live_only=True) + filter_live_ids(ids); the
anchor/PPR consumers use them so a dead fact never surfaces.

RED marker: pre-fix get() returns a superseded fact and the anchor block
renders its proposition.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from engram.self_model import render_anchor_block
from engram.semantic import Fact, SemanticMemory


def _mk(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "s.db")


def _supersede(sm: SemanticMemory, old_id: str, new_id: str) -> None:
    with sm._connect() as conn:
        conn.execute("UPDATE facts SET superseded_by = ? WHERE id = ?",
                     (new_id, old_id))


# ── get(live_only) / filter_live_ids ────────────────────────────────────────

def test_get_live_only_excludes_superseded(tmp_path: Path) -> None:
    sm = _mk(tmp_path)
    sm.store(Fact(id="old01", proposition="X is true", topic="t"), embed="defer")
    sm.store(Fact(id="new01", proposition="X is false", topic="t"), embed="defer")
    _supersede(sm, "old01", "new01")
    assert sm.get("old01") is not None, "plain get must still resolve any id"
    assert sm.get("old01", live_only=True) is None, (
        "live_only get must hide a superseded fact"
    )
    assert sm.get("new01", live_only=True) is not None


def test_get_live_only_excludes_quarantined(tmp_path: Path) -> None:
    sm = _mk(tmp_path)
    sm.store(Fact(id="q01", proposition="poison", topic="t",
                  status="quarantined"), embed="defer")
    assert sm.get("q01") is not None
    assert sm.get("q01", live_only=True) is None


def test_filter_live_ids_keeps_order(tmp_path: Path) -> None:
    sm = _mk(tmp_path)
    sm.store(Fact(id="a", proposition="alive a", topic="t"), embed="defer")
    sm.store(Fact(id="b", proposition="superseded b", topic="t"), embed="defer")
    sm.store(Fact(id="c", proposition="alive c", topic="t"), embed="defer")
    sm.store(Fact(id="x", proposition="successor", topic="t"), embed="defer")
    _supersede(sm, "b", "x")
    live = sm.filter_live_ids(["a", "b", "c", "missing"])
    assert live == ["a", "c"], f"only live ids, order preserved, got {live}"


# ── render_anchor_block end-to-end (the injected self-model path) ────────────

class _FakeStore:
    """Minimal EntityStore stand-in: one anchor linked to two facts."""
    def __init__(self, eid: str, fact_ids: list[str]) -> None:
        self._eid = eid
        self._fact_ids = fact_ids

    def list_anchors(self) -> list[dict[str, Any]]:
        return [{
            "entity_id": self._eid, "name": "WidgetX",
            "weight": 0.9, "half_life_days": 30.0, "age_days": 1.0,
        }]

    def facts_for_entity(self, entity_id: str) -> list[str]:
        return list(self._fact_ids)


def test_render_anchor_block_hides_superseded(tmp_path: Path) -> None:
    sm = _mk(tmp_path)
    sm.store(Fact(id="live01", proposition="WidgetX ships in v2", topic="t"),
             embed="defer")
    sm.store(Fact(id="dead01", proposition="WidgetX was cancelled FOREVER",
                  topic="t"), embed="defer")
    sm.store(Fact(id="succ01", proposition="WidgetX ships in v2 confirmed",
                  topic="t"), embed="defer")
    _supersede(sm, "dead01", "succ01")

    store = _FakeStore("e-widget", ["dead01", "live01"])
    out = render_anchor_block(store, sem=sm, top_k_facts=3)
    md = out["markdown"]
    assert "WidgetX ships in v2" in md, "the live fact must render"
    assert "cancelled FOREVER" not in md, (
        "a SUPERSEDED fact must NOT be injected into the self-model block"
    )
