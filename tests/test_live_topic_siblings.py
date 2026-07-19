"""SemanticMemory.live_topic_siblings + the gate's _live_topic_siblings helper — the
bounded, LIVE-only same-topic query the opt-in write-path NLI moat uses instead of
all() (Phase 1.1).

Excluding superseded / quarantined facts is CORRECTNESS, not just cost: flagging a
new write as contradicting a value that was ALREADY superseded or quarantined is a
false positive. Scanning all() on every write is O(store); the indexed query is
bounded to the same topic.
"""
from __future__ import annotations

import types

from verimem import anti_confab_gate
from verimem.semantic import Fact, SemanticMemory


def _mk(sm: SemanticMemory, fid: str, prop: str, *,
        topic: str = "t", status: str = "model_claim") -> None:
    sm.store(Fact(id=fid, proposition=prop, topic=topic, status=status))


def test_method_excludes_superseded_quarantined_and_other_topic(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    _mk(sm, "live1", "the server is up")
    _mk(sm, "dead1", "the server is down")
    sm.supersede("dead1", "live1")                      # dead1 now superseded_by live1
    _mk(sm, "quar1", "the server exploded", status="quarantined")
    _mk(sm, "other", "unrelated", topic="t2")
    ids = {f.id for f in sm.live_topic_siblings("t")}
    assert ids == {"live1"}


def test_method_respects_limit(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    for i in range(5):
        _mk(sm, f"f{i}", f"proposition number {i}")
    assert len(sm.live_topic_siblings("t", limit=3)) == 3


def test_method_empty_topic_is_empty(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    _mk(sm, "f0", "x")
    assert sm.live_topic_siblings("") == []


def test_gate_helper_filters_superseded_via_all_fallback():
    """The gate helper works on a duck-typed store that only exposes all() (no indexed
    method): it still excludes superseded + quarantined + other-topic facts in memory."""
    live = types.SimpleNamespace(id="live", proposition="p", topic="t",
                                 status="model_claim", superseded_by=None)
    dead = types.SimpleNamespace(id="dead", proposition="p2", topic="t",
                                 status="model_claim", superseded_by="live")
    quar = types.SimpleNamespace(id="quar", proposition="p3", topic="t",
                                 status="quarantined", superseded_by=None)
    off = types.SimpleNamespace(id="off", proposition="p4", topic="other",
                                status="model_claim", superseded_by=None)
    store = types.SimpleNamespace(all=lambda: [live, dead, quar, off])
    got = anti_confab_gate._live_topic_siblings(store, "t")
    assert [f.id for f in got] == ["live"]


def test_gate_helper_prefers_indexed_method_when_present():
    """When the store exposes live_topic_siblings, the helper uses it (not all())."""
    sentinel = [types.SimpleNamespace(id="idx", proposition="p", topic="t")]
    calls = {"all": 0}
    store = types.SimpleNamespace(
        live_topic_siblings=lambda topic, limit=200: sentinel,
        all=lambda: calls.__setitem__("all", calls["all"] + 1) or [],
    )
    got = anti_confab_gate._live_topic_siblings(store, "t")
    assert got == sentinel and calls["all"] == 0
