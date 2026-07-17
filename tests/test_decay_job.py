"""Cycle #110.C — Confidence decay job.

Aurelio audit 2026-05-16: "fact con outcome positivo non aumentano peso,
fact stagionati non perdono peso. Sistema inerte."

Decay model: exponential, half-life-style.

    new = max(floor, old * exp(-age / tau))

where ``age`` is ``now - fact.created_at`` (seconds) and ``tau`` is the
time-constant (default 30 days). The floor prevents a fact from going
to zero — it stays in the corpus as a traceable historical entry but
loses dominance in recall ranking.

Why this matters
----------------
The current corpus has fact written months ago with ``confidence=0.9``
that still win cosine-tied recall over freshly-verified facts. Decay
breaks that tie: time-since-write is a free signal we were ignoring.

V1 scope
--------
- Pure decision function ``compute_decayed_confidence``: no IO, fully
  testable in isolation.
- Orchestrator ``run_decay_pass(SemanticMemory)`` that walks the
  corpus, applies the formula, and persists updates via a direct
  SQL UPDATE (no embedding recomputation).
- ``dry_run`` mode for preview.
- Summary dict returned for observability.

V2 (out of scope)
-----------------
- ``last_reinforced_at`` column updated on retrieval.
- Per-topic tau (some topics decay faster).
- Salience boost from positive episode outcomes.
"""
from __future__ import annotations

import math
import time
from pathlib import Path

import pytest

from verimem.semantic import Fact, SemanticMemory

SEC_PER_DAY = 86400.0


# ---------------------------------------------------------------------------
# 1. compute_decayed_confidence — pure function, no IO
# ---------------------------------------------------------------------------


class TestComputeDecayedConfidence:

    def test_zero_age_returns_original(self) -> None:
        from verimem.decay_job import compute_decayed_confidence
        out = compute_decayed_confidence(
            original=0.9, age_seconds=0.0,
        )
        assert out == pytest.approx(0.9, rel=1e-6)

    def test_one_half_life_halves_confidence(self) -> None:
        """age = tau * ln(2) -> halved (exactly the half-life)."""
        from verimem.decay_job import compute_decayed_confidence
        tau = 30 * SEC_PER_DAY
        half_life = tau * math.log(2)
        out = compute_decayed_confidence(
            original=0.8, age_seconds=half_life,
            tau_seconds=tau, floor=0.0,
        )
        assert out == pytest.approx(0.4, rel=1e-6)

    def test_one_tau_reduces_to_one_over_e(self) -> None:
        """age = tau -> original / e (≈ 0.368 * original)."""
        from verimem.decay_job import compute_decayed_confidence
        tau = 30 * SEC_PER_DAY
        out = compute_decayed_confidence(
            original=1.0, age_seconds=tau,
            tau_seconds=tau, floor=0.0,
        )
        assert out == pytest.approx(math.e ** -1, rel=1e-6)

    def test_very_old_fact_clamped_to_floor(self) -> None:
        from verimem.decay_job import compute_decayed_confidence
        # age >> tau -> exp(-large) ≈ 0 -> clamp to floor
        out = compute_decayed_confidence(
            original=0.9, age_seconds=10 * 365 * SEC_PER_DAY,
            tau_seconds=30 * SEC_PER_DAY, floor=0.05,
        )
        assert out == pytest.approx(0.05, abs=1e-9)

    def test_negative_age_is_treated_as_zero(self) -> None:
        """Defensive: clock-skew or a fact with future created_at must
        not BOOST confidence (which would be the literal formula since
        exp(-negative) > 1). Cap at original."""
        from verimem.decay_job import compute_decayed_confidence
        out = compute_decayed_confidence(
            original=0.8, age_seconds=-3600.0,
        )
        assert out == pytest.approx(0.8, rel=1e-6)


# ---------------------------------------------------------------------------
# 2. run_decay_pass — orchestrator, walks SemanticMemory
# ---------------------------------------------------------------------------


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sm.db")


def _store_dated(sm: SemanticMemory, *, fid: str, age_days: float,
                  confidence: float = 0.9) -> None:
    """Store a fact whose created_at is exactly ``age_days`` in the past."""
    now = time.time()
    f = Fact(
        id=fid, proposition=f"fact {fid}", topic="t/decay",
        confidence=confidence,
        created_at=now - age_days * SEC_PER_DAY,
    )
    sm.store(f)


class TestRunDecayPass:

    def test_no_facts_returns_zero_summary(self, sm: SemanticMemory) -> None:
        from verimem.decay_job import run_decay_pass
        out = run_decay_pass(sm)
        assert out["facts_seen"] == 0
        assert out["facts_updated"] == 0

    def test_dry_run_does_not_persist(self, sm: SemanticMemory) -> None:
        from verimem.decay_job import run_decay_pass
        _store_dated(sm, fid="a", age_days=90, confidence=0.9)
        out = run_decay_pass(sm, dry_run=True)
        assert out["facts_seen"] == 1
        # In dry-run, facts_updated counts the rows that WOULD change
        assert out["facts_updated"] >= 1
        # But the actual confidence in DB is unchanged
        assert sm.get("a").confidence == pytest.approx(0.9)

    def test_real_run_persists_updates(self, sm: SemanticMemory) -> None:
        from verimem.decay_job import run_decay_pass
        _store_dated(sm, fid="a", age_days=60, confidence=0.9)
        before = sm.get("a").confidence
        out = run_decay_pass(sm, tau_seconds=30 * SEC_PER_DAY)
        after = sm.get("a").confidence
        assert after < before
        assert out["facts_updated"] >= 1

    def test_floor_clamps_very_old_facts(self, sm: SemanticMemory) -> None:
        from verimem.decay_job import run_decay_pass
        _store_dated(sm, fid="ancient", age_days=10_000, confidence=0.9)
        run_decay_pass(sm, tau_seconds=30 * SEC_PER_DAY, floor=0.1)
        got = sm.get("ancient")
        assert got.confidence == pytest.approx(0.1, abs=1e-6)

    def test_fresh_fact_barely_changes(self, sm: SemanticMemory) -> None:
        from verimem.decay_job import run_decay_pass
        _store_dated(sm, fid="fresh", age_days=0.001, confidence=0.9)
        run_decay_pass(sm, tau_seconds=30 * SEC_PER_DAY)
        # Fresh fact: tiny decay
        assert sm.get("fresh").confidence == pytest.approx(0.9, abs=0.001)

    def test_pass_is_idempotent_for_floor_facts(
        self, sm: SemanticMemory,
    ) -> None:
        """Once a fact is already at the floor, a second pass mustn't
        push it lower or claim it changed."""
        from verimem.decay_job import run_decay_pass
        _store_dated(sm, fid="ancient", age_days=10_000, confidence=0.9)
        run_decay_pass(sm, tau_seconds=30 * SEC_PER_DAY, floor=0.1)
        first = sm.get("ancient").confidence
        second_summary = run_decay_pass(
            sm, tau_seconds=30 * SEC_PER_DAY, floor=0.1,
        )
        second = sm.get("ancient").confidence
        assert second == pytest.approx(first, abs=1e-6)
        assert second_summary["facts_updated"] == 0

    def test_summary_reports_averages(self, sm: SemanticMemory) -> None:
        from verimem.decay_job import run_decay_pass
        _store_dated(sm, fid="a", age_days=60, confidence=0.9)
        _store_dated(sm, fid="b", age_days=15, confidence=0.7)
        out = run_decay_pass(sm, tau_seconds=30 * SEC_PER_DAY)
        assert "avg_confidence_before" in out
        assert "avg_confidence_after" in out
        assert out["avg_confidence_after"] <= out["avg_confidence_before"]
