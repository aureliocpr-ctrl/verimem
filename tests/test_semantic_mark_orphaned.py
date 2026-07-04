"""Cycle #137 (2026-05-17 sera) — L2 mutation: mark_orphaned.

Aurelio direttiva: "memoria che funziona realmente e realmente bene".
Cycle 132+133 build the DETECTION layer (scan_orphaned_facts pure
function + hippo_anti_confab_scan MCP tool). 75 orphan facts confirmed
in the live corpus (1172 facts total, 52 shipped + 22 diagnosis + 1
task_state). But the corpus stays dirty because nothing FLIPS the
status — the L2 reconciler is read-only.

Cycle 137 closes the loop:

  1. Schema v6: extend ``_VALID_STATUSES`` with ``"orphaned"`` and
     ``_STATUS_RANK[orphaned] = -1`` (below ``legacy_unverified``).
  2. SemanticMemory.mark_orphaned(fact_id, reason) — DB UPDATE +
     cache invalidation (cycle 135.A pattern). Idempotent.
  3. recall() default-filter view EXCLUDES orphaned rows. Opt-in
     ``include_orphaned=True`` keeps them visible for audit.
  4. MCP tool ``hippo_anti_confab_apply(dry_run=True)`` wraps
     scan + batch mark_orphaned.

This is the canonical "L2 detection → L2 mutation" closure. The
75 facts currently sitting as confabulations in the corpus get a
single audit-friendly status label and disappear from the default
recall view.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engram.semantic import (
    _STATUS_RANK,
    _VALID_STATUSES,
    Fact,
    SemanticMemory,
)


class TestSchemaV6EnumAndRank:
    """The status enum and rank table must include 'orphaned'."""

    def test_valid_statuses_includes_orphaned(self) -> None:
        assert "orphaned" in _VALID_STATUSES, (
            "cycle 137: 'orphaned' must be a valid status enum value "
            "so SemanticMemory.mark_orphaned() can persist it."
        )

    def test_orphaned_rank_below_legacy_unverified(self) -> None:
        assert "orphaned" in _STATUS_RANK, (
            "cycle 137: _STATUS_RANK must list 'orphaned' so min_status "
            "filtering works consistently across all statuses."
        )
        assert _STATUS_RANK["orphaned"] < _STATUS_RANK["legacy_unverified"], (
            "cycle 137: orphaned must rank BELOW legacy_unverified — it "
            "represents a fact that L2 reconciler scrubbed because it "
            "failed an L1/L1.5/L1.7 anti-confabulation detector."
        )


class TestMarkOrphanedMutator:
    """SemanticMemory.mark_orphaned() must flip status + invalidate cache."""

    def _seed_two_facts(self, tmp_path: Path) -> tuple[SemanticMemory, str]:
        sm = SemanticMemory(db_path=tmp_path / "s.db")
        a = Fact(id="a-cycle137", proposition="alpha live claim",
                  topic="t/test", confidence=0.9)
        b = Fact(id="b-cycle137", proposition="beta live claim",
                  topic="t/test", confidence=0.9)
        sm.store(a)
        sm.store(b)
        return sm, "a-cycle137"

    def test_mark_orphaned_sets_status_on_disk(
        self, tmp_path: Path,
    ) -> None:
        sm, fact_id = self._seed_two_facts(tmp_path)
        sm.mark_orphaned(fact_id, reason="L1 shipped keyword without commit ref")
        # Read back via .get() — bypasses cache since cycle 132 .get() reads disk.
        f = sm.get(fact_id)
        assert f is not None, "fact must still exist after mark_orphaned"
        assert f.status == "orphaned", (
            f"cycle 137: status must be 'orphaned' after mark_orphaned, got {f.status!r}"
        )

    def test_mark_orphaned_excludes_from_recall_default(
        self, tmp_path: Path,
    ) -> None:
        sm, fact_id = self._seed_two_facts(tmp_path)
        # Pre-mark both facts appear in recall.
        hits_pre = sm.recall("alpha", k=10)
        ids_pre = {f.id for f, _ in hits_pre}
        assert fact_id in ids_pre, "pre-mark sanity"

        sm.mark_orphaned(fact_id, reason="test")

        # Post-mark recall default-filter must NOT surface the orphan.
        hits_post = sm.recall("alpha", k=10)
        ids_post = {f.id for f, _ in hits_post}
        assert fact_id not in ids_post, (
            f"cycle 137: recall default-filter must exclude orphaned "
            f"fact (got ids={ids_post!r})"
        )

    def test_mark_orphaned_bumps_cache_version(
        self, tmp_path: Path,
    ) -> None:
        sm, fact_id = self._seed_two_facts(tmp_path)
        # Force cache build.
        sm.recall("alpha", k=3)
        v_pre = sm._cache_version  # noqa: SLF001 — test inspects internals

        sm.mark_orphaned(fact_id, reason="test")

        assert sm._cache_version > v_pre, (  # noqa: SLF001
            "cycle 137: mark_orphaned must bump _cache_version (cycle 135.A "
            "pattern) so the next recall() rebuilds the cached corpus."
        )

    def test_mark_orphaned_idempotent(
        self, tmp_path: Path,
    ) -> None:
        sm, fact_id = self._seed_two_facts(tmp_path)
        sm.mark_orphaned(fact_id, reason="first")
        # Second call must be a no-op (same status, no exception).
        sm.mark_orphaned(fact_id, reason="second")
        f = sm.get(fact_id)
        assert f is not None and f.status == "orphaned"

    def test_mark_orphaned_unknown_id_returns_false(
        self, tmp_path: Path,
    ) -> None:
        sm = SemanticMemory(db_path=tmp_path / "s.db")
        result = sm.mark_orphaned("does-not-exist", reason="x")
        assert result is False, (
            "cycle 137: mark_orphaned must return False for unknown ids "
            "(no exception — graceful)."
        )


class TestRecallIncludeOrphanedOptIn:
    """An opt-in flag allows the caller to see orphaned facts (audit)."""

    def test_include_orphaned_true_surfaces_them(
        self, tmp_path: Path,
    ) -> None:
        sm = SemanticMemory(db_path=tmp_path / "s.db")
        f = Fact(id="x-orphan", proposition="legacy claim with no commit ref",
                  topic="t/orphan", confidence=0.9)
        sm.store(f)
        sm.mark_orphaned("x-orphan", reason="test")

        # Default: hidden.
        hits_default = sm.recall("legacy", k=10)
        assert "x-orphan" not in {h.id for h, _ in hits_default}

        # Opt-in include_orphaned: visible.
        hits_opt = sm.recall("legacy", k=10, include_orphaned=True)
        assert "x-orphan" in {h.id for h, _ in hits_opt}, (
            "cycle 137: recall(include_orphaned=True) must surface orphans "
            "for audit / undo flows."
        )
