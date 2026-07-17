"""Cycle #135.A (2026-05-17) — cache invalidation regression on supersede.

Critic-orchestrator counterexample worker job 6d739c07e07b5734 verdict
(confidence 0.95) found a REAL bug introduced by cycle #135 cache:

  engram/semantic.py:887 supersede() executes
      UPDATE facts SET superseded_by=? ... WHERE id=?
  without bumping self._cache_version. The cache built by
  _get_corpus_cache() is keyed by version; if version doesn't move, the
  next recall() reuses the stale matrix that still includes A as a
  live fact, contradicting the cycle #78 contract (default-filter view
  = live rows).

Same bug propagates to:
  * supersede_chain() (calls supersede() in a loop)
  * _restore_supersession_snapshots() (raw UPDATE for atomic rollback,
    line 1075)

Reproduction (deterministic, single-thread, no race):
  1. store(A), store(B) — cache_version=2 after each store.
  2. recall("q") — populates the cache snapshot at version=2 with [A, B].
  3. supersede(A.id, B.id) — UPDATE DB, but BUG: version stays at 2.
  4. recall("q") — cache HIT at version=2 → returns A as live.
     PRE-#135 (legacy SQL path): SELECT WHERE superseded_by IS NULL ran
     on every recall, so A was correctly excluded.

These tests pin the bug RED on the cache branch as currently committed
and force the fix to bump _cache_version on every superseding mutation.
"""
from __future__ import annotations

from pathlib import Path


def _store_pair(sm) -> tuple:
    """Helper: create two live facts (A, B) in the given store, warm the
    recall cache, and return the ids."""
    from verimem.semantic import Fact

    a = Fact(
        id="a-aaaa", proposition="alpha old claim",
        topic="cycle135A/test", confidence=0.9,
    )
    b = Fact(
        id="b-bbbb", proposition="alpha new claim",
        topic="cycle135A/test", confidence=0.9,
    )
    sm.store(a)
    sm.store(b)
    # Warm the cache so the bug is observable.
    _ = sm.recall("alpha", k=5)
    return a, b


def _live_ids(hits) -> set[str]:
    return {f.id for f, _ in hits}


class TestSupersedeBumpsCacheVersion:
    """Reproduce the critic counterexample on supersede()."""

    def test_supersede_invalidates_recall_cache(
        self, tmp_path: Path,
    ) -> None:
        from verimem.semantic import SemanticMemory

        sm = SemanticMemory(db_path=tmp_path / "s.db")
        a, b = _store_pair(sm)

        # Pre-supersede: both A and B are live → both should appear.
        hits_before = sm.recall("alpha", k=5)
        ids_before = _live_ids(hits_before)
        assert a.id in ids_before, "warmup: A must be live before supersede"
        assert b.id in ids_before, "warmup: B must be live before supersede"

        # Apply supersede.
        sm.supersede(a.id, b.id, reason="cycle135A/test invalidation")

        # Post-supersede: A is no longer live.
        hits_after = sm.recall("alpha", k=5)
        ids_after = _live_ids(hits_after)
        assert a.id not in ids_after, (
            "cycle 135.A: supersede(A,B) must invalidate the recall "
            "cache so subsequent recall() excludes A from default-filter "
            "live view. Critic counterexample: cache_version not bumped "
            "→ A leaks back as live."
        )
        assert b.id in ids_after, "B must remain live"


class TestSupersedeReasonUpdateBumpsCacheVersion:
    """Same pair, only reason changes — the idempotent-reason path also
    mutates the row, so it must also bump cache_version (defensive: this
    branch doesn't change visibility but the recall result string fields
    should still reflect the latest DB state)."""

    def test_reason_only_update_keeps_invariant(
        self, tmp_path: Path,
    ) -> None:
        from verimem.semantic import SemanticMemory

        sm = SemanticMemory(db_path=tmp_path / "s.db")
        a, b = _store_pair(sm)

        sm.supersede(a.id, b.id, reason="first reason")
        # Second call with same pair, different reason → idempotent_noop=False
        # path that only updates reason.
        sm.supersede(a.id, b.id, reason="second reason")

        # A is now superseded → must NOT appear in default recall.
        hits = sm.recall("alpha", k=5)
        ids = _live_ids(hits)
        assert a.id not in ids, (
            "reason-only update path must still invalidate cache; "
            "otherwise stale snapshot from the first supersede might "
            "still include A through some other inconsistency."
        )


class TestRestoreSupersessionSnapshotsBumpsCacheVersion:
    """Cycle #81b rollback helper restores pre-state via raw UPDATE.
    After rollback, A returns to being live → cache must be invalidated
    so the next recall() picks A up again."""

    def test_rollback_restores_a_as_live_in_recall(
        self, tmp_path: Path,
    ) -> None:
        from verimem.semantic import SemanticMemory

        sm = SemanticMemory(db_path=tmp_path / "s.db")
        a, b = _store_pair(sm)

        sm.supersede(a.id, b.id, reason="cycle135A/rollback test")
        # After supersede A is hidden.
        ids_mid = _live_ids(sm.recall("alpha", k=5))
        assert a.id not in ids_mid

        # Now roll back: restore A to its pre-supersede state (all None).
        sm._restore_supersession_snapshots(  # noqa: SLF001
            [(a.id, None, None, None)],
        )

        ids_after = _live_ids(sm.recall("alpha", k=5))
        assert a.id in ids_after, (
            "cycle 135.A: _restore_supersession_snapshots must "
            "invalidate the recall cache. Critic flag — raw UPDATE on "
            "superseded_by without bumping cache_version leaks the "
            "stale 'A is hidden' view."
        )
