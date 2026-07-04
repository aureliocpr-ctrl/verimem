"""R&D 2026-06-16 — truth-reconciliation P1 (update-on-write).

The core decision: a conflict between an older fact and a newer one is either an
UPDATE (the world changed; new supersedes old → old becomes obsolete, fixing the
over-trust the calibration study found) or a DISPUTE (a genuine disagreement →
contested, both stay visible). Fail-safe: anything not clearly an update is a
dispute — a wrong supersede deletes truth from the live set, a wrong contested
only adds a visible, recoverable doubt.
"""
from __future__ import annotations

from engram.contradiction import ContradictionStore
from engram.semantic import Fact, SemanticMemory
from engram.truth_reconciliation import (
    classify_conflict,
    reconcile_fact_on_write,
)

_NOW = 1_000_000_000.0
_DAY = 86400.0


def _f(fid, *, status="verified", conf=0.9, age_days=0.0):
    return Fact(id=fid, proposition=f"value of {fid}", topic="t",
                status=status, confidence=conf, created_at=_NOW - age_days * _DAY)


# --- classify_conflict (pure) ---

def test_clear_temporal_update() -> None:
    old = _f("o", age_days=30)
    new = _f("n", age_days=0)
    assert classify_conflict(old, new, now=_NOW) == "update"


def test_near_simultaneous_is_dispute() -> None:
    old = _f("o", age_days=0.2)
    new = _f("n", age_days=0.0)
    assert classify_conflict(old, new, now=_NOW) == "dispute"


def test_newer_but_less_authoritative_is_dispute() -> None:
    # a fresh model_claim must NOT overwrite an older verified fact.
    old = _f("o", status="verified", conf=0.9, age_days=30)
    new = _f("n", status="model_claim", conf=0.5, age_days=0)
    assert classify_conflict(old, new, now=_NOW) == "dispute"


def test_promotion_to_verified_is_update() -> None:
    old = _f("o", status="model_claim", conf=0.5, age_days=30)
    new = _f("n", status="verified", conf=0.9, age_days=0)
    assert classify_conflict(old, new, now=_NOW) == "update"


# --- reconcile_fact_on_write (wires supersede / contested) ---

def test_reconcile_supersedes_clean_update(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    old = Fact(id="old", proposition="config X is 30s", topic="t",
               status="verified", confidence=0.9, created_at=_NOW - 30 * _DAY)
    new = Fact(id="new", proposition="config X is 5s", topic="t",
               status="verified", confidence=0.9, created_at=_NOW)
    sm.store(old)
    sm.store(new)
    cs = ContradictionStore(sm.db_path)
    res = reconcile_fact_on_write(sm, new, [old], now=_NOW, contradiction_store=cs)
    assert "old" in res["superseded"]
    assert sm.get("old").superseded_by == "new"


def test_reconcile_contests_ambiguous_no_blind_supersede(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    old = Fact(id="old", proposition="metric is 10", topic="t",
               status="verified", confidence=0.9, created_at=_NOW)
    new = Fact(id="new", proposition="metric is 20", topic="t",
               status="verified", confidence=0.9, created_at=_NOW)  # same instant
    sm.store(old)
    sm.store(new)
    cs = ContradictionStore(sm.db_path)
    res = reconcile_fact_on_write(sm, new, [old], now=_NOW, contradiction_store=cs)
    assert "old" in res["contested"]
    assert cs.list_unresolved_for_fact("old"), "a dispute must be recorded"
    assert sm.get("old").superseded_by is None, "fail-safe: no blind supersede"


# --- the MEASURE: P1 moves the dangerous over-trust metric ---

def test_p1_turns_over_trust_into_obsolete_flag(tmp_path) -> None:
    """The calibration study's over-trust = 'trusted' verdict on a fact that is
    actually obsolete-but-unobserved. P1 (an update arrives) must turn that into
    an 'obsolete' verdict — the only lever that moves the dangerous metric."""
    from engram.trust_signal import compute_trust_signal

    sm = SemanticMemory(db_path=tmp_path / "s.db")
    cs = ContradictionStore(sm.db_path)
    olds = []
    for i in range(20):
        f = Fact(id=f"old{i}", proposition=f"setting {i} is A", topic="t",
                 status="verified", confidence=0.9, created_at=_NOW - 60 * _DAY)
        sm.store(f)
        olds.append(f)

    # BEFORE P1: each obsolete-but-unobserved fact reads 'trusted' (over-trust).
    before = [compute_trust_signal(sm.get(f.id), sm, now=_NOW,
                                   contradiction_store=cs).verdict for f in olds]
    assert all(v == "trusted" for v in before), "precondition: dangerous over-trust"

    # P1: each update arrives and reconciliation runs.
    for i, f in enumerate(olds):
        new = Fact(id=f"new{i}", proposition=f"setting {i} is B", topic="t",
                   status="verified", confidence=0.9, created_at=_NOW)
        sm.store(new)
        reconcile_fact_on_write(sm, new, [f], now=_NOW, contradiction_store=cs)

    # AFTER P1: every reconciled fact now reads 'obsolete' -> over-trust gone.
    after = [compute_trust_signal(sm.get(f.id), sm, now=_NOW,
                                  contradiction_store=cs).verdict for f in olds]
    assert all(v == "obsolete" for v in after), "P1 must flag the updated facts"
