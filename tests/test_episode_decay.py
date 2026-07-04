"""Tests for FORGIA pezzo #7: Ebbinghaus forgetting curve on episodes.

Without decay, the episode corpus grows monotonically — old irrelevant
episodes pollute every recall and every NREM cluster. The diagnosis
agent flagged this as a real bug ("after 500 episodes the recall
returns ancient stuff with decent cosine but the system has moved on").

Math (Ebbinghaus 1885; Wixted 2004 power-law variant):

  R(t) = exp(-(now - last_accessed_at) / (tau_base * S))

where:
  - `tau_base` is the half-life baseline in seconds
  - `S` is the per-episode strength multiplier:
        S = 1 + γ × access_count + δ × salience_score + ε × skill_fitness

Strength compounds the three "this matters" signals already on the
episode (FORGIA pezzo #6 added the first two columns; skill_fitness
comes from the skills_used list looked up at compute time).

Three measurable invariants:

  1. Old + unaccessed → R below threshold → marked for pruning.
  2. Recent OR high access_count OR high salience → R above threshold
     → preserved.
  3. Pruning is REVERSIBLE before commit (returns the candidate set,
     doesn't delete blindly). The actual delete is a separate step
     that the sleep cycle controls.
"""
from __future__ import annotations

import time

import pytest

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory


def _ep(
    *, id_: str, task_text: str = "fix bug",
    outcome: str = "success",
    age_days: float = 0.0,
    access_count: int = 0,
    salience: float = 0.5,
    last_accessed_age_days: float | None = None,
) -> Episode:
    """Build an Episode with controllable age + usage stats.

    `age_days`: how long ago the episode was created.
    `last_accessed_age_days`: when it was last accessed (None ⇒ never).
    """
    now = time.time()
    last_at = (
        now - last_accessed_age_days * 86400
        if last_accessed_age_days is not None else 0.0
    )
    return Episode(
        id=id_,
        task_id="t",
        task_text=task_text,
        outcome=outcome,
        final_answer="...",
        created_at=now - age_days * 86400,
        last_accessed_at=last_at,
        access_count=access_count,
        salience_score=salience,
        traces=[Trace(
            step=1, thought="x", action="x", action_input="{}",
            observation="x",
        )],
    )


# ---------- Test 1: retention strength formula ---------------------------


def test_retention_strength_decays_with_age():
    """An episode never accessed, 60 days old, with default access/salience
    must score low retention. One hour old, same defaults, must be near 1."""
    fresh = _ep(id_="fresh", age_days=0.04)  # ~1h
    old = _ep(id_="old", age_days=60.0)
    # Effective age uses last_accessed_at when set, otherwise created_at.
    # Neither has been accessed → fall back to created_at.
    r_fresh = fresh.retention_strength()
    r_old = old.retention_strength()
    assert 0.9 <= r_fresh <= 1.0
    assert r_old < 0.3, (
        f"60-day-old never-accessed episode retains {r_old:.3f} — "
        "decay isn't biting"
    )


def test_recent_access_resets_retention():
    """Old episode that was accessed yesterday should retain high R —
    spaced repetition: re-encountering a memory strengthens it."""
    ep = _ep(id_="x", age_days=60.0, last_accessed_age_days=1.0,
             access_count=3)
    r = ep.retention_strength()
    assert r > 0.8, (
        f"recently-accessed (1 day ago) episode with access_count=3 "
        f"retained only {r:.3f} — strength multiplier isn't kicking in"
    )


def test_high_salience_amplifies_strength():
    """Two episodes, same age + accesses, but different salience.
    The high-salience one should retain MORE — surprises are
    encoded more deeply (Buzsáki 2015)."""
    high_sal = _ep(id_="hi", age_days=14.0, salience=0.9)
    low_sal = _ep(id_="lo", age_days=14.0, salience=0.0)
    assert high_sal.retention_strength() > low_sal.retention_strength()


def test_high_access_count_amplifies_strength():
    """Episodes recalled often retain more — that's the heart of
    Wozniak's SuperMemo / spaced-repetition algorithm."""
    a = _ep(id_="a", age_days=14.0, access_count=0, salience=0.3)
    b = _ep(id_="b", age_days=14.0, access_count=10, salience=0.3)
    assert b.retention_strength() > a.retention_strength()


# ---------- Test 2: pruning candidates respect the threshold -------------


def test_decay_pruning_returns_only_low_retention(tmp_path):
    """`memory.decay_pruning_candidates(threshold)` returns ids whose
    retention falls below the threshold. Doesn't delete — caller chooses."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep(id_="ancient", age_days=120.0, access_count=0))
    mem.store(_ep(id_="fresh", age_days=0.5, access_count=0))
    mem.store(_ep(id_="hot", age_days=120.0, access_count=10,
                  last_accessed_age_days=1.0, salience=0.8))

    candidates = mem.decay_pruning_candidates(retention_threshold=0.30)
    ids = {c.id for c in candidates}
    assert "ancient" in ids
    assert "fresh" not in ids
    assert "hot" not in ids, (
        "hot episode got pruned — retention strength didn't account for "
        "recent access + high salience"
    )


def test_decay_prune_actually_deletes(tmp_path):
    """`memory.decay_prune(threshold)` deletes the candidates and
    returns the deleted-ids set. Used by the sleep cycle.
    """
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep(id_="ancient", age_days=120.0, access_count=0))
    mem.store(_ep(id_="hot", age_days=0.5, access_count=5,
                  last_accessed_age_days=0.04, salience=0.7))

    before = mem.count()
    deleted = mem.decay_prune(retention_threshold=0.30)
    after = mem.count()

    assert "ancient" in deleted
    assert "hot" not in deleted
    assert after == before - len(deleted)


# ---------- Test 3: empty memory + edge cases ----------------------------


def test_decay_pruning_empty_memory_does_not_crash(tmp_path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    assert mem.decay_pruning_candidates(retention_threshold=0.30) == []
    assert mem.decay_prune(retention_threshold=0.30) == set()


def test_retention_with_zero_tau_returns_zero():
    """Defensive: tau=0 would divide by zero. The formula must clamp
    or return a reasonable default rather than raise."""
    ep = _ep(id_="x", age_days=1.0)
    r = ep.retention_strength(tau_base_s=0.0)
    assert 0.0 <= r <= 1.0  # no crash, no inf, no nan


# ---------- Test 4: spaced-repetition style — recall reinforces -----------


def test_recall_strengthens_retention_via_access_tracking(tmp_path):
    """The integration check: recall() bumps `access_count` and
    `last_accessed_at` (pezzo #6), which feed retention_strength
    (pezzo #7). After being recalled, an old episode should retain
    significantly more than its untouched twin."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    # An old episode about 'fix calc.py'
    old_ep = _ep(id_="old", age_days=30.0, access_count=0, salience=0.5)
    mem.store(old_ep)

    # Initial retention (never accessed → falls back to created_at)
    r_before = mem.get("old").retention_strength()
    # Recall it three times
    for _ in range(3):
        mem.recall(old_ep.task_text, k=1)

    after = mem.get("old")
    r_after = after.retention_strength()
    assert after.access_count == 3
    assert r_after > r_before, (
        f"retention before {r_before:.3f}, after 3 recalls {r_after:.3f} "
        "— spaced repetition isn't kicking in"
    )


# ---------- Test 5: deterministic ordering -------------------------------


def test_decay_candidates_ordered_lowest_retention_first(tmp_path):
    """Pruning candidates ordered worst-first lets the caller cap by
    count (e.g. 'prune up to 100') without re-scoring."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep(id_="d150", age_days=150.0))
    mem.store(_ep(id_="d90", age_days=90.0))
    mem.store(_ep(id_="d60", age_days=60.0))
    mem.store(_ep(id_="d2", age_days=2.0))  # should NOT be a candidate

    candidates = mem.decay_pruning_candidates(retention_threshold=0.50)
    ids = [c.id for c in candidates]
    # Ordered ascending by retention → most-decayed first
    assert ids[0] == "d150"
    if len(ids) > 1:
        assert ids[-1] != "d150"  # not all same
