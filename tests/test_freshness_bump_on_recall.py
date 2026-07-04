"""Freshness window = 45 days + bump-on-recall (2026-06-09, Aurelio "un mese e
mezzo").

Two coupled decisions:
  1. The default staleness half-life drops 90 -> 45 days (a memory not
     re-verified in ~1.5 months ages out of the default recall view).
  2. To stop USED memories from silently vanishing under the shorter window,
     a successful recall REFRESHES last_verified_at to the server clock
     (spaced-repetition). So a memory fades 45 days after its LAST USE, not
     45 days after creation.

SECURITY INVARIANT (regression-guarded): the bump uses the SERVER clock (never
the future), and stale facts are filtered out BEFORE the returned set is built,
so a future-last_verified_at spoof stays excluded and is NEVER bumped back to
life. (Companion to test_freshness_redteam_lv_spoof.py.)
"""
from __future__ import annotations

import sqlite3
import time

import pytest

from engram import semantic as _sem
from engram.semantic import Fact, SemanticMemory, _fact_is_stale

_DAY = 86400.0


def _lv(db_path, fact_id: str) -> float | None:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT last_verified_at FROM facts WHERE id = ?", (fact_id,)
        ).fetchone()
        return row["last_verified_at"] if row else None
    finally:
        conn.close()


def test_default_half_life_is_45_days():
    # Aurelio 2026-06-09: a memory is "old" after a month and a half.
    assert _sem._DEFAULT_HALF_LIFE_DAYS == 45.0


def test_recall_refreshes_last_verified_at(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_BUMP_ON_RECALL", raising=False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    old = now - 40 * _DAY  # fresh under a 45-day window, but 40d since use
    sm.store(Fact(id="f1", proposition="the deploy key lives in vault path X",
                  topic="ops", status="model_claim", source_episodes=["e"],
                  created_at=old, last_verified_at=old))
    # A recall that returns f1 must refresh its last_verified_at to ~now.
    hits = sm.recall("deploy key vault path", k=5)
    assert any(f.id == "f1" for f, _ in hits), "f1 should be recalled (still fresh)"
    bumped = _lv(tmp_path / "s.db", "f1")
    assert bumped is not None and bumped >= now - 5, (
        f"recall must refresh last_verified_at to ~now; got {bumped}, now={now:.0f}"
    )


def test_recalled_fact_survives_past_the_original_window(tmp_path, monkeypatch):
    # Without the bump, a fact created 40d ago would be stale 44d later (84d>45).
    # With the bump-on-use, recalling it resets the clock so it survives.
    monkeypatch.delenv("ENGRAM_BUMP_ON_RECALL", raising=False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    old = now - 40 * _DAY
    sm.store(Fact(id="f1", proposition="the staging region is eu-west-1",
                  topic="infra", status="model_claim", source_episodes=["e"],
                  created_at=old, last_verified_at=old))
    sm.recall("staging region", k=5)  # bumps lv -> ~now
    bumped = _lv(tmp_path / "s.db", "f1")
    # 44 days after the bump it is still fresh (44 < 45); pre-bump it would have
    # been 84 days old => stale.
    future = now + 44 * _DAY
    assert _fact_is_stale(bumped, old, future) is False, "bump must reset the clock"
    assert _fact_is_stale(old, old, future) is True, "pre-bump it would be stale"


def test_future_lv_spoof_is_not_bumped_back_to_life(tmp_path, monkeypatch):
    # SECURITY: a future last_verified_at is stale (anti-spoof) => excluded from
    # recall => must NEVER be bumped (which would reset it to a valid 'now').
    monkeypatch.delenv("ENGRAM_BUMP_ON_RECALL", raising=False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    spoof = now + 3650 * _DAY
    sm.store(Fact(id="evil", proposition="auth module works in prod forever",
                  topic="cap/auth", status="verified", source_episodes=["e"],
                  created_at=now - 5000 * _DAY, last_verified_at=spoof))
    hits = sm.recall("auth module prod", k=5)
    assert not any(f.id == "evil" for f, _ in hits), "future-spoof must stay excluded"
    after = _lv(tmp_path / "s.db", "evil")
    assert after == pytest.approx(spoof), (
        "excluded spoof fact must NOT be bumped (would resurrect it); "
        f"lv changed {spoof} -> {after}"
    )


def test_bump_opt_out_via_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_BUMP_ON_RECALL", "0")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    old = now - 40 * _DAY
    sm.store(Fact(id="f1", proposition="redis runs on port 6379",
                  topic="infra", status="model_claim", source_episodes=["e"],
                  created_at=old, last_verified_at=old))
    sm.recall("redis port", k=5)
    after = _lv(tmp_path / "s.db", "f1")
    assert after == pytest.approx(old), "opt-out: last_verified_at must be untouched"
