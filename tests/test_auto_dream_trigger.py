"""Cycle #69 — Auto-Dream trigger on SessionStart.

Goal: turn HippoAgent from "memory-on-demand" into "memory that ALSO
proposes insight while the agent is dormant". When a fresh Claude
session starts, if enough new episodes/facts piled up since the last
trigger AND a cooldown window has elapsed, schedule **one** Dream
task (`hippo_dream_propose`) in the background. The next session sees
the resulting `pending_task` artifact.

This file covers the *pure decision* layer + the *counter* helper +
one integration test against an in-memory SQLite stub that mimics
`~/.engram/{episodes.db,semantic.db}`. No LLM call, no real Dream
spawn — those belong to `propose_dream_tasks` (cycle #35), which we
re-use unchanged.

The module under test is `verimem.auto_dream_trigger`:

  - `should_trigger(*, last_trigger_ts, now, new_items_count,
                    min_items, min_cooldown_s, enabled)` -> bool
  - `count_new_items(*, episodes_db, semantic_db, since_ts)` -> int
  - `load_last_trigger_ts(state_path)` -> float | None
  - `save_last_trigger_ts(state_path, ts)` -> None

The hook integration is exercised through `maybe_trigger_dream(...)`
which orchestrates the four primitives above.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from verimem.auto_dream_trigger import (
    count_new_items,
    load_last_trigger_ts,
    maybe_trigger_dream,
    save_last_trigger_ts,
    should_trigger,
)

# ---------------------------------------------------------------------------
# 1. should_trigger — pure decision
# ---------------------------------------------------------------------------


def test_no_trigger_when_disabled():
    """The env-gate `enabled=False` short-circuits — never trigger."""
    assert should_trigger(
        last_trigger_ts=None, now=1_000_000.0,
        new_items_count=999, min_items=5, min_cooldown_s=1800,
        enabled=False,
    ) is False


def test_no_trigger_when_few_items():
    """Below the new-items threshold → no trigger even if cooldown elapsed."""
    assert should_trigger(
        last_trigger_ts=None, now=1_000_000.0,
        new_items_count=4, min_items=5, min_cooldown_s=1800,
        enabled=True,
    ) is False


def test_trigger_on_first_run_when_enough_items():
    """No last_trigger_ts AND items >= threshold → trigger."""
    assert should_trigger(
        last_trigger_ts=None, now=1_000_000.0,
        new_items_count=5, min_items=5, min_cooldown_s=1800,
        enabled=True,
    ) is True


def test_cooldown_blocks_trigger():
    """Even with enough items, if last trigger was <cooldown ago → no."""
    now = 1_000_000.0
    last = now - 600  # 10 min ago, cooldown is 30 min
    assert should_trigger(
        last_trigger_ts=last, now=now,
        new_items_count=10, min_items=5, min_cooldown_s=1800,
        enabled=True,
    ) is False


def test_trigger_when_cooldown_elapsed():
    """Enough items AND last trigger >cooldown ago → trigger."""
    now = 1_000_000.0
    last = now - 1900  # 31.6 min ago
    assert should_trigger(
        last_trigger_ts=last, now=now,
        new_items_count=5, min_items=5, min_cooldown_s=1800,
        enabled=True,
    ) is True


def test_zero_items_never_triggers_even_after_long_idle():
    """Empty corpus delta → never trigger no matter how long ago."""
    assert should_trigger(
        last_trigger_ts=0.0, now=1_000_000.0,
        new_items_count=0, min_items=5, min_cooldown_s=1800,
        enabled=True,
    ) is False


# ---------------------------------------------------------------------------
# 2. count_new_items — SQLite-backed helper
# ---------------------------------------------------------------------------


def _seed_episode(conn: sqlite3.Connection, eid: str, ts: float) -> None:
    """Minimal-schema episode insert (only the columns we read)."""
    conn.execute(
        "INSERT INTO episodes (id, task_text, final_answer, outcome, "
        "created_at) VALUES (?, ?, ?, ?, ?)",
        (eid, "t", "a", "success", ts),
    )


def _seed_fact(conn: sqlite3.Connection, fid: str, ts: float) -> None:
    conn.execute(
        "INSERT INTO facts (id, proposition, topic, confidence, "
        "created_at) VALUES (?, ?, ?, ?, ?)",
        (fid, "p", "t", 0.9, ts),
    )


@pytest.fixture()
def stub_dbs(tmp_path: Path) -> tuple[Path, Path]:
    """Create minimal episodes.db and semantic.db with the columns we read."""
    ep_db = tmp_path / "episodes.db"
    sm_db = tmp_path / "semantic.db"
    with sqlite3.connect(ep_db) as c:
        c.execute(
            "CREATE TABLE episodes (id TEXT PRIMARY KEY, task_text TEXT, "
            "final_answer TEXT, outcome TEXT, created_at REAL)"
        )
    with sqlite3.connect(sm_db) as c:
        c.execute(
            "CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT, "
            "topic TEXT, confidence REAL, created_at REAL)"
        )
    return ep_db, sm_db


def test_count_zero_when_no_new(stub_dbs):
    ep_db, sm_db = stub_dbs
    n = count_new_items(
        episodes_db=ep_db, semantic_db=sm_db, since_ts=time.time(),
    )
    assert n == 0


def test_count_sums_episodes_and_facts_since_ts(stub_dbs):
    ep_db, sm_db = stub_dbs
    cutoff = 1_000_000.0
    with sqlite3.connect(ep_db) as c:
        _seed_episode(c, "e_old", cutoff - 10)
        _seed_episode(c, "e_new1", cutoff + 10)
        _seed_episode(c, "e_new2", cutoff + 20)
    with sqlite3.connect(sm_db) as c:
        _seed_fact(c, "f_old", cutoff - 5)
        _seed_fact(c, "f_new", cutoff + 5)
    n = count_new_items(
        episodes_db=ep_db, semantic_db=sm_db, since_ts=cutoff,
    )
    # 2 new episodes + 1 new fact = 3
    assert n == 3


def test_count_handles_missing_dbs_gracefully(tmp_path: Path):
    """Brand-new install: no DB files yet → 0, no crash."""
    n = count_new_items(
        episodes_db=tmp_path / "does_not_exist.db",
        semantic_db=tmp_path / "also_missing.db",
        since_ts=0.0,
    )
    assert n == 0


def test_count_since_ts_none_counts_everything(stub_dbs):
    """since_ts=None → no cutoff, count the whole corpus."""
    ep_db, sm_db = stub_dbs
    with sqlite3.connect(ep_db) as c:
        _seed_episode(c, "e1", 1.0)
        _seed_episode(c, "e2", 2.0)
    n = count_new_items(
        episodes_db=ep_db, semantic_db=sm_db, since_ts=None,
    )
    assert n == 2


# ---------------------------------------------------------------------------
# 3. state file IO — load/save last_trigger_ts
# ---------------------------------------------------------------------------


def test_load_returns_none_when_state_missing(tmp_path: Path):
    state = tmp_path / "never_written.txt"
    assert load_last_trigger_ts(state) is None


def test_save_then_load_roundtrip(tmp_path: Path):
    state = tmp_path / "last_trigger.txt"
    save_last_trigger_ts(state, 1_234_567.89)
    got = load_last_trigger_ts(state)
    assert got == pytest.approx(1_234_567.89, rel=1e-9)


def test_load_handles_corrupt_state_gracefully(tmp_path: Path):
    """Corrupt content must not crash — return None (treat as first run)."""
    state = tmp_path / "corrupt.txt"
    state.write_text("not a number\n", encoding="utf-8")
    assert load_last_trigger_ts(state) is None


def test_load_clamps_future_timestamp_to_none(tmp_path: Path, monkeypatch):
    """Critic counterexample (cycle #69 review, 2026-05-14): clock-skew.

    If the state file contains a timestamp **in the future** relative to
    `time.time()` (NTP correction backward, VM hibernate/resume with
    drifted clock, dual-boot UTC bias, manual file copy), the previous
    implementation kept that future ts and the cooldown check `(now -
    last_ts) < cooldown_s` evaluated against a *negative* delta, which
    blocked Auto-Dream indefinitely.

    Fix: `load_last_trigger_ts` clamps `ts > now + small_tolerance` to
    None — treat as corrupt state, behave as first run.
    """
    state = tmp_path / "future.txt"
    # Write a timestamp 1 hour in the future.
    fake_now = 1_000_000.0
    future_ts = fake_now + 3600

    # Monkeypatch time.time so the function sees fake_now as "current".
    import verimem.auto_dream_trigger as adt
    monkeypatch.setattr(adt.time, "time", lambda: fake_now)

    state.write_text(f"{future_ts:.6f}\n", encoding="utf-8")
    got = load_last_trigger_ts(state)
    assert got is None, (
        f"future ts {future_ts} (now={fake_now}) must be clamped to None, "
        f"got {got}"
    )


def test_load_accepts_timestamps_at_or_before_now(tmp_path: Path, monkeypatch):
    """Boundary check for the clock-skew clamp: present and past pass."""
    state = tmp_path / "present.txt"
    fake_now = 1_000_000.0

    import verimem.auto_dream_trigger as adt
    monkeypatch.setattr(adt.time, "time", lambda: fake_now)

    # Exactly `now` — accept.
    state.write_text(f"{fake_now:.6f}\n", encoding="utf-8")
    assert load_last_trigger_ts(state) == pytest.approx(fake_now)

    # 1 day in the past — accept.
    past = fake_now - 86400
    state.write_text(f"{past:.6f}\n", encoding="utf-8")
    assert load_last_trigger_ts(state) == pytest.approx(past)


def test_maybe_trigger_recovers_from_future_state_file(
    stub_dbs, tmp_path, monkeypatch,
):
    """End-to-end: a future-ts state file MUST NOT block a legitimate
    trigger. The clamp resets last_ts to None → treated as first run."""
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_ENABLED", "1")
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_MIN_ITEMS", "1")
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_COOLDOWN_S", "1800")
    ep_db, sm_db = stub_dbs
    with sqlite3.connect(ep_db) as c:
        _seed_episode(c, "e1", 100.0)

    # Seed a state file 1h in the future relative to `now=1_000_000`.
    (ep_db.parent / "auto_dream_state.txt").write_text(
        f"{1_000_000.0 + 3600:.6f}\n", encoding="utf-8",
    )
    # Monkeypatch time.time so load_last_trigger_ts sees our "now".
    import verimem.auto_dream_trigger as adt
    monkeypatch.setattr(adt.time, "time", lambda: 1_000_000.0)

    out = maybe_trigger_dream(
        engram_dir=ep_db.parent,
        now=1_000_000.0,
        dream_callable=lambda **kw: {"dream_id": "recovered"},
    )
    assert out["triggered"] is True, (
        f"future state file must be treated as corrupt, got {out}"
    )
    assert out.get("dream_id") == "recovered"


# ---------------------------------------------------------------------------
# 4. maybe_trigger_dream — orchestrator (the only thing the hook calls)
# ---------------------------------------------------------------------------


def test_maybe_trigger_returns_status_dict_when_disabled(tmp_path, monkeypatch):
    """Disabled gate returns {'triggered': False, 'reason': 'disabled'}."""
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_ENABLED", "0")
    out = maybe_trigger_dream(
        engram_dir=tmp_path,
        now=1_000_000.0,
        dream_callable=lambda **kw: pytest.fail("must not be called"),
    )
    assert out["triggered"] is False
    assert out["reason"] == "disabled"


def test_maybe_trigger_default_is_enabled(stub_dbs, tmp_path, monkeypatch):
    """Cycle #110.A (2026-05-16): Auto-Dream is on by default.

    Without ENGRAM_AUTO_DREAM_ENABLED set, the gate must NOT short-circuit
    with reason='disabled'. The orchestrator must proceed past the env-gate
    and reach the cooldown/items checks. With empty stub DBs the reason
    becomes 'no_new_items' (or 'not_enough_items'), NEVER 'disabled'.

    Opt-out path: ENGRAM_AUTO_DREAM_ENABLED=0 still works (covered by
    test_maybe_trigger_returns_status_dict_when_disabled above).
    """
    monkeypatch.delenv("ENGRAM_AUTO_DREAM_ENABLED", raising=False)
    ep_db, _sm_db = stub_dbs
    out = maybe_trigger_dream(
        engram_dir=ep_db.parent,
        now=1_000_000.0,
        dream_callable=lambda **kw: pytest.fail("must not be called"),
    )
    assert out["reason"] != "disabled", (
        f"Auto-Dream must be on by default; got reason={out['reason']!r}"
    )
    assert out["reason"] in {"no_new_items", "not_enough_items"}


@pytest.mark.parametrize("falsy_value", [
    "0", "off", "no", "false", "", "banana", "Yes",
])
def test_maybe_trigger_non_truthy_values_still_disable(
    tmp_path, monkeypatch, falsy_value,
):
    """Cycle #110.A: semantics of the env-gate are an allowlist, not a
    denylist. Only known-truthy tokens (``_TRUTHY`` set) enable the worker;
    anything else disables. The only thing cycle #110.A changes is the
    DEFAULT when the var is unset.

    Importantly, this protects against typos: if a user mistypes
    "Y3s" or "trure" or "banana" they get the safe-disabled path, not
    accidentally-enabled.
    """
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_ENABLED", falsy_value)
    out = maybe_trigger_dream(
        engram_dir=tmp_path,
        now=1_000_000.0,
        dream_callable=lambda **kw: pytest.fail("must not be called"),
    )
    assert out["triggered"] is False
    assert out["reason"] == "disabled", (
        f"value {falsy_value!r} should disable, got reason={out['reason']!r}"
    )


def test_maybe_trigger_skips_when_not_enough_items(stub_dbs, tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_ENABLED", "1")
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_MIN_ITEMS", "5")
    # No items seeded — count is 0
    ep_db, sm_db = stub_dbs
    # engram_dir is the parent — the helper looks for episodes.db / semantic.db
    out = maybe_trigger_dream(
        engram_dir=ep_db.parent,
        now=1_000_000.0,
        dream_callable=lambda **kw: pytest.fail("must not be called"),
    )
    assert out["triggered"] is False
    assert out["reason"] in {"not_enough_items", "no_new_items"}


def test_maybe_trigger_invokes_dream_when_all_conditions_met(
    stub_dbs, tmp_path, monkeypatch,
):
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_ENABLED", "1")
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_MIN_ITEMS", "3")
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_COOLDOWN_S", "60")
    ep_db, sm_db = stub_dbs
    # Seed 4 episodes (above the threshold of 3)
    with sqlite3.connect(ep_db) as c:
        for i in range(4):
            _seed_episode(c, f"e{i}", 100.0 + i)

    captured = {}

    def fake_dream(**kw):
        captured.update(kw)
        return {"dream_id": "fake-abc", "pending_tasks": [{"task_id": "t1"}]}

    out = maybe_trigger_dream(
        engram_dir=ep_db.parent,
        now=1_000_000.0,
        dream_callable=fake_dream,
    )
    assert out["triggered"] is True
    assert out["dream_id"] == "fake-abc"
    # dream_callable received engram_dir as a path-like
    assert "engram_dir" in captured or "live_dirs" in captured


def test_maybe_trigger_persists_state_after_firing(
    stub_dbs, tmp_path, monkeypatch,
):
    """After triggering, the state file must be updated to `now`."""
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_ENABLED", "1")
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_MIN_ITEMS", "1")
    ep_db, sm_db = stub_dbs
    with sqlite3.connect(ep_db) as c:
        _seed_episode(c, "e1", 100.0)

    out = maybe_trigger_dream(
        engram_dir=ep_db.parent,
        now=2_000_000.0,
        dream_callable=lambda **kw: {"dream_id": "fake"},
    )
    assert out["triggered"] is True

    state_file = ep_db.parent / "auto_dream_state.txt"
    assert state_file.exists()
    assert load_last_trigger_ts(state_file) == pytest.approx(2_000_000.0)


def test_maybe_trigger_respects_cooldown_across_calls(
    stub_dbs, tmp_path, monkeypatch,
):
    """Second call within cooldown window must NOT fire even if items exist."""
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_ENABLED", "1")
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_MIN_ITEMS", "1")
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_COOLDOWN_S", "1800")
    ep_db, sm_db = stub_dbs
    with sqlite3.connect(ep_db) as c:
        _seed_episode(c, "e1", 100.0)

    calls = []

    def fake_dream(**kw):
        calls.append(kw)
        return {"dream_id": f"d{len(calls)}"}

    # First call: fires
    out1 = maybe_trigger_dream(
        engram_dir=ep_db.parent, now=1_000_000.0,
        dream_callable=fake_dream,
    )
    assert out1["triggered"] is True
    # Second call 5 min later: blocked by cooldown
    out2 = maybe_trigger_dream(
        engram_dir=ep_db.parent, now=1_000_000.0 + 300,
        dream_callable=fake_dream,
    )
    assert out2["triggered"] is False
    assert out2["reason"] == "cooldown"
    # Dream was called exactly once
    assert len(calls) == 1


def test_maybe_trigger_prefers_nested_db_layout(tmp_path, monkeypatch):
    """The real HippoAgent install uses <engram_dir>/episodes/episodes.db
    and <engram_dir>/semantic/semantic.db — the orchestrator must find
    those even when an empty flat-layout stub exists at the root."""
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_ENABLED", "1")
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_MIN_ITEMS", "1")
    # Empty flat stub (mimics legacy ~/.engram/semantic.db emptying)
    (tmp_path / "semantic.db").touch()
    # Nested DB with one fact (real data)
    (tmp_path / "semantic").mkdir()
    with sqlite3.connect(tmp_path / "semantic" / "semantic.db") as c:
        c.execute(
            "CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT, "
            "topic TEXT, confidence REAL, created_at REAL)"
        )
        _seed_fact(c, "f1", 100.0)
    # Episodes also in nested layout
    (tmp_path / "episodes").mkdir()
    with sqlite3.connect(tmp_path / "episodes" / "episodes.db") as c:
        c.execute(
            "CREATE TABLE episodes (id TEXT PRIMARY KEY, task_text TEXT, "
            "final_answer TEXT, outcome TEXT, created_at REAL)"
        )

    out = maybe_trigger_dream(
        engram_dir=tmp_path,
        now=1_000_000.0,
        dream_callable=lambda **kw: {"dream_id": "nested-ok"},
    )
    assert out["triggered"] is True
    assert out["new_items"] == 1
    assert out.get("dream_id") == "nested-ok"


def test_maybe_trigger_handles_dream_exception_gracefully(
    stub_dbs, tmp_path, monkeypatch,
):
    """If the dream call raises, return {triggered: False, reason: 'error', ...}
    — never propagate up to the hook (would block SessionStart)."""
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_ENABLED", "1")
    monkeypatch.setenv("ENGRAM_AUTO_DREAM_MIN_ITEMS", "1")
    ep_db, sm_db = stub_dbs
    with sqlite3.connect(ep_db) as c:
        _seed_episode(c, "e1", 100.0)

    def boom(**kw):
        raise RuntimeError("dream_propose blew up")

    out = maybe_trigger_dream(
        engram_dir=ep_db.parent, now=1_000_000.0,
        dream_callable=boom,
    )
    assert out["triggered"] is False
    assert out["reason"] == "error"
    assert "dream_propose blew up" in out.get("error", "")
