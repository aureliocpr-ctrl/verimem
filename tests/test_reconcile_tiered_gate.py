"""Iter 3 — TIERED anti-sycophancy: protect EVIDENCED facts from a bare overwrite,
but ALLOW bare->bare knowledge updates.

Iter 2 measured that the STRICT gate (require_evidence: new must be evidenced to
supersede anything) drops reconcile update-recall 0.28->0 on HaluMem, whose
updates are all bare model_claims. The tiered policy keeps that recall (bare->bare
allowed) while still refusing to let a bare, merely-confident assertion overwrite
an EVIDENCED fact (verified status OR verified_by). Three tiers, default OFF:
  none   -> raw recency+authority (sycophantic)
  tiered -> protect evidenced facts only          [write-path default when supersede on]
  strict -> require evidence for ANY supersede     [max safety, low bare recall]
"""
from __future__ import annotations

from verimem.contradiction import ContradictionStore
from verimem.semantic import Fact, SemanticMemory
from verimem.truth_reconciliation import classify_conflict, reconcile_fact_on_write

_NOW = 1_000_000_000.0
_DAY = 86400.0


def _f(fid, *, status="model_claim", conf=0.7, age_days=0.0, verified_by=None):
    return Fact(id=fid, proposition=f"the capital of Zorvia is {fid}", topic="geo",
                status=status, confidence=conf, created_at=_NOW - age_days * _DAY,
                verified_by=verified_by)


# --- classify_conflict: the tiered policy ---

def test_tiered_blocks_bare_over_evidenced_same_rank() -> None:
    """The case the plain authority check does NOT catch: old is evidenced via
    verified_by but still model_claim (rank 2); a newer bare model_claim with
    higher confidence outranks it on authority — yet must NOT supersede evidence."""
    old = _f("old", status="model_claim", conf=0.7, age_days=5,
             verified_by=("src:doc#1",))          # evidenced, rank 2
    new = _f("new", status="model_claim", conf=0.99, age_days=0)   # bare, rank 2, louder
    assert classify_conflict(old, new, now=_NOW, protect_evidenced_facts=True) == "dispute"
    # without the tier, the confident bare assertion sycophantically wins:
    assert classify_conflict(old, new, now=_NOW) == "update"


def test_tiered_allows_bare_over_bare() -> None:
    """The HaluMem update case: both facts are unverified beliefs -> a clean
    temporal update applies (recall preserved, unlike strict)."""
    old = _f("old", status="model_claim", conf=0.7, age_days=5)
    new = _f("new", status="model_claim", conf=0.7, age_days=0)
    assert classify_conflict(old, new, now=_NOW, protect_evidenced_facts=True) == "update"


def test_tiered_allows_evidenced_over_evidenced() -> None:
    old = _f("old", status="verified", conf=0.8, age_days=5)
    new = _f("new", status="verified", conf=0.9, age_days=0)
    assert classify_conflict(old, new, now=_NOW, protect_evidenced_facts=True) == "update"


def test_strict_still_blocks_all_bare() -> None:
    """Strict is unchanged: even a bare->bare update is blocked (max safety)."""
    old = _f("old", status="model_claim", age_days=5)
    new = _f("new", status="model_claim", age_days=0)
    assert classify_conflict(old, new, now=_NOW,
                             require_evidence_to_supersede=True) == "dispute"


def test_default_and_none_allow_bare_over_bare() -> None:
    """Byte-identical default (no tier, no strict): recency+authority supersedes."""
    old = _f("old", status="model_claim", age_days=5)
    new = _f("new", status="model_claim", age_days=0)
    assert classify_conflict(old, new, now=_NOW) == "update"


# --- reconcile_fact_on_write: tiered reaches the wired path ---

def test_reconcile_tiered_protects_evidenced(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    old = _f("old", status="model_claim", conf=0.7, age_days=5,
             verified_by=("src:doc#1",))
    new = _f("new", status="model_claim", conf=0.99, age_days=0)
    sm.store(old)
    sm.store(new)
    cs = ContradictionStore(sm.db_path)
    res = reconcile_fact_on_write(sm, new, [old], now=_NOW, contradiction_store=cs,
                                  protect_evidenced=True)
    assert "old" not in res["superseded"], "evidenced fact must not be overwritten by bare"
    assert "old" in res["contested"]
    assert sm.get("old").superseded_by is None


def test_reconcile_tiered_allows_bare_update(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    old = _f("old", status="model_claim", conf=0.7, age_days=5)   # bare
    new = _f("new", status="model_claim", conf=0.7, age_days=0)   # bare
    sm.store(old)
    sm.store(new)
    cs = ContradictionStore(sm.db_path)
    res = reconcile_fact_on_write(sm, new, [old], now=_NOW, contradiction_store=cs,
                                  protect_evidenced=True)
    assert "old" in res["superseded"], "bare->bare update must still apply (recall)"
    assert sm.get("old").superseded_by == "new"
