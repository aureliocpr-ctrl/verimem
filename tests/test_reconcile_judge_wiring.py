"""set_reconcile_judge wires the semantic NLI judge into the store-path reconcile, so the
validated 4× conflict-recall is reachable in production (not just via direct calls).
Default (no judge wired) stays the lexical heuristic. Hermetic — reconcile_new_fact is
stubbed to capture the judge it receives; no LLM, no entity graph."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from verimem.semantic import Fact, SemanticMemory


def _mem():
    tmp = Path(tempfile.mkdtemp(prefix="recjudge_"))
    return SemanticMemory(db_path=tmp / "semantic" / "semantic.db")


def _capture(sm):
    seen = {}

    def _stub(fact, *, auto_supersede=False, judge=None, require_evidence=False,
              protect_evidenced=False):
        seen["judge"] = judge
        return {"superseded": [], "contested": []}

    sm.reconcile_new_fact = _stub  # type: ignore[method-assign]
    return seen


def test_store_path_passes_wired_judge(monkeypatch):
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "1")
    sm = _mem()
    seen = _capture(sm)
    sentinel = object()
    sm.set_reconcile_judge(sentinel)
    sm.store(Fact(proposition="The cache TTL is 300 seconds.", topic="t"), embed="sync")
    assert seen.get("judge") is sentinel  # judge flowed setter -> store -> reconcile


def test_store_path_judge_none_by_default(monkeypatch):
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "1")
    sm = _mem()
    seen = _capture(sm)
    sm.store(Fact(proposition="The region is eu-west-1.", topic="t"), embed="sync")
    assert seen.get("judge") is None  # unset -> lexical default, unchanged


def test_setter_is_idempotent_and_overridable():
    sm = _mem()
    a, b = object(), object()
    sm.set_reconcile_judge(a)
    assert sm._reconcile_judge is a
    sm.set_reconcile_judge(b)
    assert sm._reconcile_judge is b
    sm.set_reconcile_judge(None)
    assert sm._reconcile_judge is None


@pytest.mark.parametrize("on", ["0", ""])
def test_reconcile_off_skips_entirely(monkeypatch, on):
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", on)
    sm = _mem()
    seen = _capture(sm)
    sm.set_reconcile_judge(object())
    sm.store(Fact(proposition="The port is 8080.", topic="t"), embed="sync")
    assert "judge" not in seen  # reconcile not invoked when the feature is off
