"""Critic counterexample on graded admission (514cdec3c6b4b512, FAIL vote):
an UNPROVEN write must never RETIRE an admitted value.

Empirically reproduced by the critic on the working tree: with
ENGRAM_GRADED_ADMISSION=1, a sub-threshold write (score 12) that the L3 stack
also classifies as a same-source EVOLUTION flips the gate action to persist,
which flips client.add()'s _disposition to "admitted" and UNLOCKS the
supersession branch — retiring the previously admitted (grounded) value from
curated recall. Under the env OFF both values survived. Net effect: a score-12
claim evicts a score-95 one. This file pins the cure plus the two graded
branches the first test file left uncovered (critic falsification caveat 1)
and the ledger-attribution rule (caveat 4).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.anti_confab_gate import run_validation_gate

OLD = "The subscription costs 100 euros per month."
NEW = "The subscription costs 150 euros per month."
WEAK_SOURCE = "Billing notes: various commercial topics were discussed."


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("ENGRAM_GRADED_ADMISSION", raising=False)
    yield


def _low_score(monkeypatch, score: float = 12.0):
    """Deterministic sub-threshold CE on the REAL SDK path."""
    import verimem.grounding_gate as gg
    monkeypatch.setattr(gg, "fact_grounding_score_ex",
                        lambda llm, src, prop: (score, "local"))


def test_graded_admit_must_not_retire_an_admitted_value(tmp_path: Path,
                                                        monkeypatch):
    monkeypatch.setenv("ENGRAM_GRADED_ADMISSION", "1")
    from verimem.client import Memory
    m = Memory(path=tmp_path / "m.db")
    r1 = m.add(OLD, topic="pricing/plan",
               verified_by=["source-doc:billing:1"], validate="full")
    assert r1.get("status") != "quarantined"
    _low_score(monkeypatch)
    r2 = m.add(NEW, topic="pricing/plan",
               verified_by=["source-doc:billing:1"], validate="full",
               source=WEAK_SOURCE, ground=True)
    # the graded write may be admitted low-conf — but the OLD value survives
    import sqlite3
    with sqlite3.connect(str(m.semantic.db_path)) as con:
        row = con.execute("SELECT superseded_by FROM facts WHERE id=?",
                          (r1["id"],)).fetchone()
    assert row and row[0] is None, \
        "an unproven (graded) write must NOT retire an admitted value"
    assert not r2.get("superseded"), \
        f"graded admission must not supersede, got {r2.get('superseded')}"


def test_graded_layers_are_never_credited_as_blockers():
    """Ledger attribution (critic caveat 4): a ``*-graded`` layer records an
    ADMISSION — it must never own a block reason nor a by_layer credit, even
    when another layer quarantines the same write."""
    from verimem.client import _blocking_layers, _is_advisory_layer
    assert _is_advisory_layer("L4-grounding-graded") is True
    assert _is_advisory_layer("L4-review-graded") is True
    ws = [{"layer": "L3", "reason": "contradiction"},
          {"layer": "L4-grounding-graded", "reason": "graded"}]
    assert _blocking_layers(ws) == ["L3"]


def _band(monkeypatch, *, score: float, escalation):
    """Force the CE band path deterministically: local judge, band enforced,
    tau_hi above the score, escalate_band stubbed."""
    import verimem.band_escalation as be
    import verimem.grounding_gate as gg
    monkeypatch.setattr(gg, "fact_grounding_score_ex",
                        lambda llm, src, prop: (score, "local"))
    monkeypatch.setattr(gg, "_ce_band_enforced", lambda: True)
    monkeypatch.setattr(gg, "_ce_band_tau_hi", lambda: 88.0)
    monkeypatch.setattr(be, "escalate_band", lambda src, prop: escalation)


def _gate_no_llm():
    return run_validation_gate(
        proposition="The maintenance window is on Saturday night.",
        verified_by=None, topic="ops/x", agent=None, validate="full",
        source=WEAK_SOURCE, grounding_llm=None, ground_write=True)


def test_band_review_graded_admits(monkeypatch):
    """Critic caveat 1a: the no-adjudicator band branch. Graded ON: the
    borderline write persists with L4-review-graded instead of being held."""
    monkeypatch.setenv("ENGRAM_GRADED_ADMISSION", "1")
    _band(monkeypatch, score=60.0, escalation=None)
    res = _gate_no_llm()
    assert res.action == "persist"
    assert any(w.get("layer") == "L4-review-graded" for w in res.warnings)
    assert not any(w.get("layer") == "L4-review" for w in res.warnings)


def test_band_review_off_still_holds(monkeypatch):
    _band(monkeypatch, score=60.0, escalation=None)
    res = _gate_no_llm()
    assert res.action in ("downgrade", "reject")
    assert any(w.get("layer") == "L4-review" for w in res.warnings)


def test_band_escalated_subthreshold_graded_admits(monkeypatch):
    """Critic caveat 1b: the escalated-judge branch. The llm adjudicates below
    the claude-scale cut; graded ON admits with L4-grounding-graded."""
    monkeypatch.setenv("ENGRAM_GRADED_ADMISSION", "1")
    _band(monkeypatch, score=60.0, escalation=(20.0, "claude-band"))
    res = _gate_no_llm()
    assert res.action == "persist"
    assert any(w.get("layer") == "L4-grounding-graded" for w in res.warnings)


def test_band_escalated_subthreshold_off_blocks(monkeypatch):
    _band(monkeypatch, score=60.0, escalation=(20.0, "claude-band"))
    res = _gate_no_llm()
    assert res.action in ("downgrade", "reject")
    assert any(w.get("layer") == "L4-grounding" for w in res.warnings)
