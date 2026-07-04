"""Audit 3-round #20 (correctness): a confidence-decay pass must decay by REAL
elapsed time, not by the number of times the job is run.

Root cause (deeper than the audit's "irreversible/no-undo" label): run_decay_pass
recomputes `new = old * exp(-(now - created_at)/tau)` using the CURRENT (already
decayed) confidence as `old` but the TOTAL age from created_at. So every pass
re-multiplies a fact by exp(-age_total/tau). For a 30-day-old fact each run
multiplies by exp(-1)=0.368, collapsing the corpus to the floor in
O(number-of-runs), independent of real time. The daemon's 24h cooldown
(daemon_runner.py:188 "decay is multiplicative") is a band-aid, not a fix; the
docstring's "Idempotency" claim only ever held for facts already at the floor
(test_pass_is_idempotent_for_floor_facts).

Fix: persist facts.last_decay_at and decay from `now - last_decay_at` (falling
back to created_at when never decayed). exp is multiplicative, so accumulating
per-pass deltas equals one continuous decay over the real elapsed time — and two
passes at the same instant are a no-op.
"""
from __future__ import annotations

import math
import time
from pathlib import Path

import pytest

from engram.semantic import Fact, SemanticMemory

SEC_PER_DAY = 86400.0


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sm.db")


def _store_dated(sm: SemanticMemory, *, fid: str, age_days: float,
                 confidence: float = 0.9) -> None:
    now = time.time()
    sm.store(Fact(
        id=fid, proposition=f"fact {fid}", topic="t/decay",
        confidence=confidence, created_at=now - age_days * SEC_PER_DAY,
    ))


def test_repeated_pass_same_instant_is_idempotent(sm: SemanticMemory) -> None:
    """Two passes at the SAME instant must not decay twice (the bug)."""
    from engram.decay_job import run_decay_pass
    t = time.time()
    _store_dated(sm, fid="a", age_days=60, confidence=0.9)
    run_decay_pass(sm, tau_seconds=30 * SEC_PER_DAY, floor=0.0, now=t)
    after_first = sm.get("a").confidence
    assert after_first < 0.9, "precondition: the first pass decays the fact"

    summary2 = run_decay_pass(sm, tau_seconds=30 * SEC_PER_DAY, floor=0.0, now=t)
    after_second = sm.get("a").confidence
    assert after_second == pytest.approx(after_first, abs=1e-9), \
        "stesso istante -> nessun ulteriore decadimento (era il doppio-decay)"
    assert summary2["facts_updated"] == 0, \
        "un pass a delta-tempo zero non modifica alcun fatto"


def test_many_passes_same_instant_do_not_collapse(sm: SemanticMemory) -> None:
    """N passes at the same instant must equal ONE pass, not N-fold decay."""
    from engram.decay_job import run_decay_pass
    t = time.time()
    _store_dated(sm, fid="a", age_days=30, confidence=0.9)
    for _ in range(5):
        run_decay_pass(sm, tau_seconds=30 * SEC_PER_DAY, floor=0.05, now=t)
    got = sm.get("a").confidence
    # 30d == 1 tau -> one pass: 0.9/e ≈ 0.331. Buggy: 0.9*e^-5 ≈ 0.006 -> floor.
    assert got == pytest.approx(0.9 * math.e ** -1, abs=1e-6), \
        "5 pass allo stesso istante != collasso al floor"


def test_decay_tracks_real_elapsed_between_passes(sm: SemanticMemory) -> None:
    """Across passes separated by real time, total decay == one continuous
    decay over the elapsed interval (per-pass deltas compose multiplicatively)."""
    from engram.decay_job import run_decay_pass
    t = time.time()
    _store_dated(sm, fid="a", age_days=30, confidence=0.9)
    run_decay_pass(sm, tau_seconds=30 * SEC_PER_DAY, floor=0.0, now=t)
    c1 = sm.get("a").confidence                      # ~0.9/e after 1 tau
    run_decay_pass(sm, tau_seconds=30 * SEC_PER_DAY, floor=0.0,
                   now=t + 30 * SEC_PER_DAY)         # +1 tau of REAL time
    c2 = sm.get("a").confidence
    assert c2 < c1, "real elapsed time keeps decaying the fact"
    assert c2 == pytest.approx(0.9 * math.e ** -2, abs=1e-3), \
        "due tau di tempo reale -> 0.9*e^-2 (non e^-3 del bug ne' fermo a e^-1)"
