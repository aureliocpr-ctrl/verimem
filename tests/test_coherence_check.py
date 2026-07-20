"""Cycle #116 (2026-05-17) — Live memory coherence check.

Aurelio insight 2026-05-17: hippo_remember is write-only naive.
Two consecutive hippo_remember calls with the same proposition+topic
land as TWO distinct rows (UUID-random id). Numeric clashes on the
same topic accumulate silently. Boolean clashes idem. The cycle #110.B
contradiction detector exists but is never triggered by writes.

This module adds an optional **post-store hook** to `SemanticMemory.store()`
that runs a LOCAL scan on the topic just touched (cheap: typically <50
sibling facts), emits structured `CoherenceWarning`s, and lets the
caller log / store / re-act without forcing auto-supersession.

Test plan
---------
1. **Hook off by default** — backwards-compatible.
2. **Hook detects exact-duplicate** (jaccard >= 0.85) sibling.
3. **Hook detects numeric_clash** sibling.
4. **Hook detects boolean_clash** sibling.
5. **Hook respects topic scoping** — same-proposition across different
   topics are NOT flagged.
6. **No mutation by default** — the stored fact is not changed; the
   warning is observational only.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sm.db")


def _store(sm: SemanticMemory, prop: str, topic: str, *,
           confidence: float = 0.9, fid: str | None = None) -> Fact:
    f = Fact(
        id=fid or f"f-{int(time.time()*1e6)}-{hash(prop) & 0xffff:x}",
        proposition=prop, topic=topic, confidence=confidence,
        status="model_claim", created_at=time.time(),
    )
    sm.store(f)
    return f


class TestHookDefaultOff:
    """Default behaviour: no hook → no warnings, no overhead."""

    def test_store_without_hook_returns_normally(
        self, sm: SemanticMemory,
    ) -> None:
        # Two identical facts on the same topic — pre-cycle-116
        # behaviour: both land, no warning.
        _store(sm, "X uses 5MB memory", "project/x/mem")
        _store(sm, "X uses 5MB memory", "project/x/mem")
        assert sm.count() == 2


class TestCoherenceCheckPureFunction:
    """Pure check: takes a fact + sibling list, returns warnings."""

    def test_no_siblings_no_warning(self) -> None:
        from verimem.coherence_check import check_against_siblings
        f = Fact(id="x", proposition="X uses 5MB", topic="t",
                 confidence=0.9)
        warnings = check_against_siblings(f, siblings=[])
        assert warnings == []

    def test_exact_duplicate_jaccard_flagged(self) -> None:
        from verimem.coherence_check import check_against_siblings
        f = Fact(id="new", proposition="X uses 5MB of memory",
                 topic="t", confidence=0.9)
        sib = Fact(id="old",
                   proposition="X uses 5MB of memory",
                   topic="t", confidence=0.9)
        warnings = check_against_siblings(f, siblings=[sib])
        assert any(w.kind == "near_duplicate" for w in warnings)
        # And the warning carries the other-id for human review.
        w = next(w for w in warnings if w.kind == "near_duplicate")
        assert w.other_fact_id == "old"

    def test_high_jaccard_flagged(self) -> None:
        from verimem.coherence_check import check_against_siblings
        # 80% overlap should still be near_duplicate (threshold 0.7).
        f = Fact(id="new",
                 proposition="The cache uses 5MB of memory total",
                 topic="t", confidence=0.9)
        sib = Fact(id="old",
                   proposition="The cache uses 5MB of memory",
                   topic="t", confidence=0.9)
        warnings = check_against_siblings(f, siblings=[sib])
        assert any(w.kind == "near_duplicate" for w in warnings)

    def test_unrelated_propositions_no_warning(self) -> None:
        from verimem.coherence_check import check_against_siblings
        f = Fact(id="new", proposition="Build pipeline uses GitHub Actions",
                 topic="t", confidence=0.9)
        sib = Fact(id="old", proposition="Cache uses 5MB of memory",
                   topic="t", confidence=0.9)
        warnings = check_against_siblings(f, siblings=[sib])
        assert warnings == []

    def test_numeric_clash_flagged(self) -> None:
        from verimem.coherence_check import check_against_siblings
        f = Fact(id="new", proposition="Cache uses 50MB of memory",
                 topic="t", confidence=0.9)
        sib = Fact(id="old", proposition="Cache uses 5MB of memory",
                   topic="t", confidence=0.9)
        warnings = check_against_siblings(f, siblings=[sib])
        # 50 vs 5 → 10x difference, clearly outside tolerance
        kinds = {w.kind for w in warnings}
        assert "numeric_clash" in kinds

    def test_boolean_clash_flagged(self) -> None:
        from verimem.coherence_check import check_against_siblings
        f = Fact(id="new",
                 proposition="Module X is not deprecated in v0.3.0",
                 topic="t", confidence=0.9)
        sib = Fact(id="old",
                   proposition="Module X is deprecated in v0.3.0",
                   topic="t", confidence=0.9)
        warnings = check_against_siblings(f, siblings=[sib])
        kinds = {w.kind for w in warnings}
        assert "boolean_clash" in kinds


class TestHookIntegrationWithStore:
    """SemanticMemory.store() accepts a coherence_hook callable."""

    def test_hook_called_with_new_fact_and_siblings(
        self, sm: SemanticMemory,
    ) -> None:
        captured: list = []

        def hook(fact: Fact, sm_: SemanticMemory) -> None:
            captured.append((fact.id, fact.topic))

        _store(sm, "First fact", "t/a")
        _store(sm, "Second fact", "t/a")
        # Re-store with hook this time.
        f3 = Fact(
            id="f-3", proposition="Third fact", topic="t/a",
            confidence=0.9, status="model_claim",
        )
        sm.store(f3, coherence_hook=hook)

        assert captured == [("f-3", "t/a")]

    def test_hook_only_runs_when_provided(self, sm: SemanticMemory) -> None:
        """If no hook is passed, store() must behave exactly as before."""
        f1 = Fact(
            id="f-1", proposition="x", topic="t",
            confidence=0.9, status="model_claim",
        )
        # Should not raise; default behaviour preserved.
        sm.store(f1)
        assert sm.get("f-1") is not None


class TestScanTopicLocally:
    """Helper that fetches same-topic siblings, then runs the check."""

    def test_scan_topic_after_store(self, sm: SemanticMemory) -> None:
        from verimem.coherence_check import scan_topic_for_warnings
        # Use longer, lexically-overlapping propositions so the conftest
        # deterministic embedding stub produces high cosine similarity
        # (>0.75) and the numeric_clash detector fires. Real production
        # embeddings give ~0.91 on the short pair; the stub needs more
        # shared tokens to reach the same regime.
        _store(
            sm,
            "Project X cache memory usage measured at 5MB total today",
            "project/x/mem",
        )
        f2 = Fact(
            id="f-clash",
            proposition=(
                "Project X cache memory usage measured at 50MB total today"
            ),
            topic="project/x/mem", confidence=0.9,
            status="model_claim", created_at=time.time(),
        )
        sm.store(f2)
        warnings = scan_topic_for_warnings(f2, sm)
        kinds = {w.kind for w in warnings}
        assert "numeric_clash" in kinds

    def test_scan_topic_filters_by_topic(self, sm: SemanticMemory) -> None:
        """A fact under topic A with same proposition as one under topic B
        must NOT be flagged — coherence is scoped to topic."""
        from verimem.coherence_check import scan_topic_for_warnings
        _store(sm, "X uses 5MB", "topic/a")
        f2 = Fact(
            id="f-cross", proposition="X uses 50MB",
            topic="topic/b", confidence=0.9,
            status="model_claim", created_at=time.time(),
        )
        sm.store(f2)
        warnings = scan_topic_for_warnings(f2, sm)
        # No siblings under topic/b (only one fact) → no warning.
        assert warnings == []

    def test_scan_excludes_self(self, sm: SemanticMemory) -> None:
        """The newly-stored fact must NOT be compared against itself."""
        from verimem.coherence_check import scan_topic_for_warnings
        f = Fact(
            id="f-self", proposition="solo on this topic",
            topic="topic/solo", confidence=0.9,
            status="model_claim", created_at=time.time(),
        )
        sm.store(f)
        warnings = scan_topic_for_warnings(f, sm)
        assert warnings == []


class TestNoMutation:
    """The check is observational — it must not change the stored fact."""

    def test_stored_fact_unchanged_after_check(
        self, sm: SemanticMemory,
    ) -> None:
        from verimem.coherence_check import scan_topic_for_warnings
        f1 = Fact(
            id="f-orig", proposition="Cache uses 5MB",
            topic="config/cache-size", confidence=0.9,
            status="model_claim", created_at=time.time(),
        )
        sm.store(f1)
        f2 = Fact(
            id="f-clash", proposition="Cache uses 50MB",
            topic="config/cache-size", confidence=0.9,
            status="model_claim", created_at=time.time(),
        )
        sm.store(f2)
        _ = scan_topic_for_warnings(f2, sm)
        # both still present, statuses untouched
        got1 = sm.get("f-orig")
        got2 = sm.get("f-clash")
        assert got1 is not None and got1.status == "model_claim"
        assert got2 is not None and got2.status == "model_claim"
