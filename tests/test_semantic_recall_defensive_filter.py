"""Cycle 171 (2026-05-22) — defensive filter for malformed embedding
blobs at recall time, WITHOUT regressing cycle 135 sub-linear scaling.

ROADMAP context
---------------
The mem-architect session 2026-05-21 (fact 82e2b4325657) identified a
catastrophic bug: 108 facts written by ``clp save`` had
``embedding=b""``, deserialize returned a shape-(0,) vector, and
``np.stack(...)`` crashed with "all input arrays must have the same
shape" — killing every ``hippo_facts_recall`` for ~29 hours.

The write-side fix landed in ``clp.verimem.compute_embedding_blob``.
The read-side belt-and-braces guard was attempted in semantic.py via
a Python ``deserialize → filter`` loop, but that loop added a per-row
Python cost that pushed cycle 135 ``recall`` p50(2000)/p50(500) from
~1.5× (target <3×) to ~4.15× — regression.

Cycle 171 RED→GREEN
-------------------
* Test A: a fact with ``embedding=b""`` (or any wrong-byte-length blob)
  must NOT crash ``recall()``. It must be silently filtered out, and
  the well-formed rows must still be returned.
* Test B: same for ``recall_hybrid`` (the path StepInjector uses).
* Test C: cycle 135 sub-linear scaling invariant must hold
  (delegated to existing test_semantic_recall_perf.py — we only
  cross-check we did not re-introduce the Python deserialize loop).

The fix is a SQL-side filter ``AND length(embedding) = 1536`` on the
WHERE clause of the cache load + direct recall fetch. SQL filters
the BLOB before it touches Python — zero per-row deserialize cost,
zero stack call on ragged arrays.

Constant: 1536 = 384 dim × 4 bytes (float32). Verified empirically
on this branch (``verimem.embedding.encode("test").shape == (384,)``,
``serialize(...).__len__() == 1536``).
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import numpy as np
import pytest

from verimem import embedding
from verimem.semantic import Fact, SemanticMemory


def _inject_malformed_row(
    db_path: Path, fact_id: str, proposition: str, blob: bytes,
) -> None:
    """Bypass SemanticMemory.store to inject a malformed-embedding row.

    Reproduces the exact precondition that crashed recall on 2026-05-20:
    an embedding column whose byte length differs from the canonical
    384*4 = 1536.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        # Match the columns set by SemanticMemory.store. We only care
        # about embedding shape — other columns get safe defaults.
        conn.execute(
            "INSERT INTO facts ("
            "id, proposition, topic, confidence, source_episodes, "
            "created_at, embedding, status, verified_by, "
            "source_signature) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                fact_id, proposition, "cycle171/malformed",
                0.9, "", time.time(), blob,
                "model_claim", "[]", None,
            ),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


class TestRecallDefensiveFilter:
    """A malformed embedding blob must NEVER crash recall."""

    def test_empty_blob_does_not_crash_recall(self, sm: SemanticMemory) -> None:
        """clp save bug shape: ``embedding=b""`` blob hides in DB.
        Pre-fix this crashed np.stack; post-fix it is silently skipped.
        """
        # Seed a good row first so the corpus is non-empty.
        sm.store(Fact(
            proposition="well-formed fact about embedding daemon",
            topic="cycle171/good",
            confidence=0.9,
            source_episodes=["ep_seed"],
            status="model_claim",
        ))
        # Now inject a malformed row.
        _inject_malformed_row(
            sm.db_path, "bad_id_empty", "polluted poison row", blob=b"",
        )
        # Bust the cache so the next recall hits the SQL path.
        sm._cache_version += 1  # noqa: SLF001 — bump → cache miss
        # Must not raise.
        hits = sm.recall("embedding daemon", k=5)
        # The well-formed row must still be there.
        assert any(
            "well-formed" in h[0].proposition for h in hits
        ), f"good row dropped: {hits}"
        # The malformed row must NOT appear (no way to score it).
        assert not any(
            h[0].id == "bad_id_empty" for h in hits
        ), f"malformed row leaked into hits: {hits}"

    def test_wrong_dim_blob_does_not_crash_recall(
        self, sm: SemanticMemory,
    ) -> None:
        """A row from a hypothetical different-dim model would also be
        skipped — same defensive shape filter applies.
        """
        sm.store(Fact(
            proposition="another well-formed row alpha beta",
            topic="cycle171/good",
            confidence=0.9,
            source_episodes=["ep_seed2"],
            status="model_claim",
        ))
        # 512-dim float32 = 2048 bytes — wrong shape.
        wrong_dim = np.zeros(512, dtype=np.float32).tobytes()
        _inject_malformed_row(
            sm.db_path, "bad_id_wrong_dim", "wrong dim poison", wrong_dim,
        )
        sm._cache_version += 1  # noqa: SLF001 — bump → cache miss
        hits = sm.recall("alpha beta", k=5)
        assert any(
            h[0].id != "bad_id_wrong_dim" for h in hits
        ), f"corpus empty: {hits}"
        assert not any(
            h[0].id == "bad_id_wrong_dim" for h in hits
        ), f"wrong-dim row leaked: {hits}"

    def test_recall_hybrid_handles_malformed_blob(
        self, sm: SemanticMemory,
    ) -> None:
        """StepInjector uses recall_hybrid — that path must also be
        defensive."""
        sm.store(Fact(
            proposition="hybrid recall fact about consolidation pipeline",
            topic="cycle171/hybrid",
            confidence=0.9,
            source_episodes=["ep_seed3"],
            trigger_keywords=["consolidation", "pipeline"],
            status="model_claim",
        ))
        _inject_malformed_row(
            sm.db_path, "bad_hybrid", "hybrid poison", b"",
        )
        sm._cache_version += 1  # noqa: SLF001 — bump → cache miss
        # Must not raise.
        hits = sm.recall_hybrid(
            "consolidation pipeline", k=5, semantic_weight=0.6,
        )
        assert any(
            "hybrid recall" in f.proposition for f, _ in hits
        ), f"good row missing: {hits}"
        assert not any(
            f.id == "bad_hybrid" for f, _ in hits
        ), f"malformed row leaked: {hits}"

    def test_only_malformed_rows_returns_empty_no_crash(
        self, sm: SemanticMemory,
    ) -> None:
        """Edge case: every row in the DB is malformed. recall returns
        [], does not crash.
        """
        # Bypass sm.store entirely — only malformed rows.
        _inject_malformed_row(sm.db_path, "bad1", "p1", b"")
        _inject_malformed_row(sm.db_path, "bad2", "p2", b"")
        sm._cache_version += 1  # noqa: SLF001 — bump → cache miss
        # Must not raise.
        hits = sm.recall("anything", k=5)
        assert hits == [], f"all-malformed corpus must return []: {hits}"

    def test_cache_path_filters_malformed_rows(
        self, sm: SemanticMemory,
    ) -> None:
        """When the cache builds (cycle 135 hot path), it must skip the
        malformed rows up-front so subsequent recalls see a clean
        matrix — no per-recall Python deserialize loop.
        """
        sm.store(Fact(
            proposition="cache-path well-formed gamma delta",
            topic="cycle171/cache",
            confidence=0.9,
            source_episodes=["ep_cache"],
            status="model_claim",
        ))
        _inject_malformed_row(sm.db_path, "bad_cache", "cache poison", b"")
        sm._cache_version += 1  # noqa: SLF001 — bump → cache miss
        # Warm the cache.
        sm.recall("gamma delta", k=5)
        # Inspect cache directly — the matrix must NOT contain the
        # malformed row's footprint.
        cache = sm._corpus_cache  # noqa: SLF001
        assert cache is not None
        cached_ids = {f.id for f in cache["facts"]}
        assert "bad_cache" not in cached_ids, (
            f"malformed row leaked into cache: {cached_ids}"
        )
        # Cache matrix shape must equal #usable rows × embedding dim.
        assert cache["matrix"].shape == (len(cache["facts"]), 384), (
            f"cache matrix shape wrong: {cache['matrix'].shape}"
        )
