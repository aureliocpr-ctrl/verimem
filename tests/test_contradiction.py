"""Cycle #110.B — Contradiction detector (REAL, not confabulated).

Aurelio audit 2026-05-16: "il vero core (memoria riflessiva attiva) è
ferro vergine. Cycle #70 contradiction detector daemon era
confabulazione, non implementato."

This module is the daemon-ready core of contradiction detection. It
finds pairs of facts that:
  - share the same ``topic``
  - have high embedding similarity (cosine >= threshold)
  - DIFFER on a measurable axis (numeric, boolean, categorical)

Detection types:
  - ``numeric_clash``: both propositions contain numbers but they
    diverge beyond a relative tolerance (default 5%).
  - ``boolean_clash``: one proposition has a negation marker
    ("is not", "doesn't", "no", "non") that the other lacks while
    talking about the same subject.

Persistence: a new ``contradictions`` table in semantic.db (schema v4
migration). Each detected pair gets a row with detected_at; resolution
sets resolved_at + an optional note.

Tests below are TDD-strict: they MUST fail on master and pass after
``engram/contradiction.py`` + the schema migration land.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from verimem.semantic import Fact, SemanticMemory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sm.db")


def _store(sm: SemanticMemory, *, fid: str, prop: str, topic: str = "t/a",
           confidence: float = 0.9) -> Fact:
    """Helper that works on main (pre-cycle-109) and post-merge.

    We avoid passing ``status`` so the test suite is independent from
    PR #44 merge state — the contradiction detector doesn't need it.
    """
    f = Fact(id=fid, proposition=prop, topic=topic, confidence=confidence)
    sm.store(f)
    return f


# ---------------------------------------------------------------------------
# 1. Numeric clash detection (the most common adversarial pattern)
# ---------------------------------------------------------------------------


class TestNumericClash:

    def test_no_facts_returns_empty(self, sm: SemanticMemory) -> None:
        from verimem.contradiction import detect_numeric_clashes
        out = detect_numeric_clashes(sm.all())
        assert out == []

    def test_single_fact_returns_empty(self, sm: SemanticMemory) -> None:
        from verimem.contradiction import detect_numeric_clashes
        _store(sm, fid="a", prop="NEXUS has 17280 tests")
        assert detect_numeric_clashes(sm.all()) == []

    def test_two_facts_same_topic_diverging_numbers_flagged(
        self, sm: SemanticMemory,
    ) -> None:
        from verimem.contradiction import detect_numeric_clashes
        _store(sm, fid="a", prop="NEXUS has 17280 tests",
                topic="project/nexus/test-count")
        _store(sm, fid="b", prop="NEXUS has 10000 tests",
                topic="project/nexus/test-count")
        out = detect_numeric_clashes(sm.all())
        assert len(out) == 1
        pair = {out[0].fact_a_id, out[0].fact_b_id}
        assert pair == {"a", "b"}
        assert out[0].kind == "numeric_clash"

    def test_two_facts_different_topic_not_flagged(
        self, sm: SemanticMemory,
    ) -> None:
        """Same numbers, different topic → not a contradiction."""
        from verimem.contradiction import detect_numeric_clashes
        _store(sm, fid="a", prop="NEXUS has 17280 tests", topic="nexus")
        _store(sm, fid="b", prop="HippoAgent has 17000 tests", topic="hippo")
        assert detect_numeric_clashes(sm.all()) == []

    def test_numbers_within_tolerance_not_flagged(
        self, sm: SemanticMemory,
    ) -> None:
        """5% relative tolerance: 100 vs 104 → no clash."""
        from verimem.contradiction import detect_numeric_clashes
        _store(sm, fid="a", prop="The threshold is 100 ms", topic="perf/p")
        _store(sm, fid="b", prop="The threshold is 104 ms", topic="perf/p")
        out = detect_numeric_clashes(sm.all(), value_tolerance=0.05)
        assert out == []

    def test_numbers_outside_tolerance_flagged(
        self, sm: SemanticMemory,
    ) -> None:
        """100 vs 200 → 100% delta → clash."""
        from verimem.contradiction import detect_numeric_clashes
        _store(sm, fid="a", prop="The threshold is 100 ms", topic="perf/p")
        _store(sm, fid="b", prop="The threshold is 200 ms", topic="perf/p")
        out = detect_numeric_clashes(sm.all(), value_tolerance=0.05)
        assert len(out) == 1

    def test_low_similarity_not_flagged_even_with_clash(
        self, sm: SemanticMemory,
    ) -> None:
        """Two facts mentioning numbers but talking about totally different
        things should NOT be flagged. Same topic but semantically far apart
        (low cosine) → no clash."""
        from verimem.contradiction import detect_numeric_clashes
        _store(sm, fid="a",
                prop="The forest has 17280 trees by the riverbank",
                topic="t/a")
        _store(sm, fid="b",
                prop="The car costs 17 dollars at the auction",
                topic="t/a")
        # similarity_threshold high enough that these are below it
        out = detect_numeric_clashes(
            sm.all(), similarity_threshold=0.85,
        )
        assert out == []

    def test_clash_carries_similarity_score(
        self, sm: SemanticMemory,
    ) -> None:
        from verimem.contradiction import detect_numeric_clashes
        _store(sm, fid="a", prop="HippoAgent has 200 MCP tools",
                topic="project/hippo")
        _store(sm, fid="b", prop="HippoAgent has 374 MCP tools",
                topic="project/hippo")
        out = detect_numeric_clashes(sm.all())
        assert len(out) == 1
        assert 0.0 <= out[0].similarity <= 1.0


# ---------------------------------------------------------------------------
# 2. Boolean clash detection (negation markers)
# ---------------------------------------------------------------------------


class TestBooleanClash:

    def test_is_vs_is_not_flagged(self, sm: SemanticMemory) -> None:
        from verimem.contradiction import detect_boolean_clashes
        _store(sm, fid="a", prop="The build is passing", topic="ci/build")
        _store(sm, fid="b", prop="The build is not passing", topic="ci/build")
        out = detect_boolean_clashes(sm.all())
        assert len(out) == 1
        assert out[0].kind == "boolean_clash"

    def test_two_positive_assertions_not_flagged(
        self, sm: SemanticMemory,
    ) -> None:
        from verimem.contradiction import detect_boolean_clashes
        _store(sm, fid="a", prop="The build is passing", topic="ci/build")
        _store(sm, fid="b", prop="The build is fast", topic="ci/build")
        out = detect_boolean_clashes(sm.all())
        assert out == []

    def test_different_topic_not_flagged(
        self, sm: SemanticMemory,
    ) -> None:
        from verimem.contradiction import detect_boolean_clashes
        _store(sm, fid="a", prop="The build is passing", topic="ci/build")
        _store(sm, fid="b", prop="The build is not passing", topic="ci/test")
        out = detect_boolean_clashes(sm.all())
        assert out == []


# ---------------------------------------------------------------------------
# 3. Persistence: ContradictionStore (schema v4)
# ---------------------------------------------------------------------------


class TestContradictionStore:

    def test_schema_v4_creates_contradictions_table(
        self, sm: SemanticMemory,
    ) -> None:
        from verimem.contradiction import ContradictionStore
        store = ContradictionStore(sm.db_path)
        with store._connect() as conn:
            tables = {
                r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'",
                ).fetchall()
            }
        assert "contradictions" in tables

    def test_add_and_list_round_trip(self, sm: SemanticMemory) -> None:
        from verimem.contradiction import Contradiction, ContradictionStore
        store = ContradictionStore(sm.db_path)
        c = Contradiction(
            id="c1", fact_a_id="a", fact_b_id="b",
            kind="numeric_clash", similarity=0.92,
            detected_at=time.time(),
        )
        store.add(c)
        out = store.list_unresolved(limit=10)
        assert len(out) == 1
        assert out[0].id == "c1"
        assert out[0].kind == "numeric_clash"

    def test_resolve_marks_resolved_at_and_note(
        self, sm: SemanticMemory,
    ) -> None:
        from verimem.contradiction import Contradiction, ContradictionStore
        store = ContradictionStore(sm.db_path)
        store.add(Contradiction(
            id="c1", fact_a_id="a", fact_b_id="b",
            kind="numeric_clash", similarity=0.9,
            detected_at=1.0,
        ))
        store.resolve("c1", note="kept fact b, forgot fact a")
        unresolved = store.list_unresolved()
        assert unresolved == []  # no longer unresolved

    def test_count_unresolved(self, sm: SemanticMemory) -> None:
        from verimem.contradiction import Contradiction, ContradictionStore
        store = ContradictionStore(sm.db_path)
        for i in range(3):
            store.add(Contradiction(
                id=f"c{i}", fact_a_id=f"a{i}", fact_b_id=f"b{i}",
                kind="numeric_clash", similarity=0.9,
                detected_at=float(i),
            ))
        assert store.count_unresolved() == 3
        store.resolve("c1", note="resolved")
        assert store.count_unresolved() == 2


# ---------------------------------------------------------------------------
# 4. End-to-end: scan_corpus persists + idempotent
# ---------------------------------------------------------------------------


class TestScanCorpus:

    def test_scan_persists_detected_pairs(self, sm: SemanticMemory) -> None:
        from verimem.contradiction import ContradictionStore, scan_corpus
        _store(sm, fid="a", prop="NEXUS has 17280 tests",
                topic="project/nexus/test-count")
        _store(sm, fid="b", prop="NEXUS has 10000 tests",
                topic="project/nexus/test-count")
        store = ContradictionStore(sm.db_path)
        summary = scan_corpus(sm, store=store)
        assert summary["new_detected"] >= 1
        assert store.count_unresolved() >= 1

    def test_scan_is_idempotent(self, sm: SemanticMemory) -> None:
        """Running scan twice does NOT duplicate rows for the same pair."""
        from verimem.contradiction import ContradictionStore, scan_corpus
        _store(sm, fid="a", prop="NEXUS has 17280 tests",
                topic="project/nexus/test-count")
        _store(sm, fid="b", prop="NEXUS has 10000 tests",
                topic="project/nexus/test-count")
        store = ContradictionStore(sm.db_path)
        scan_corpus(sm, store=store)
        count_after_first = store.count_unresolved()
        scan_corpus(sm, store=store)
        count_after_second = store.count_unresolved()
        assert count_after_first == count_after_second
