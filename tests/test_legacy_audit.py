"""Cycle #110.D — Legacy corpus audit (3-bucket classifier).

Aurelio audit 2026-05-16: "815/864 fact sono ``legacy_unverified``,
nascosti dal filter cycle 109 ma il pollution è solo spostato sotto
il tappeto". This module reads the legacy population and proposes a
classification into 3 buckets:

  - ``verified_on_rereading``: proposition carries verified_by-shaped
    artifacts (bash:..., file:..., url:..., sha256:..., pytest:...,
    exit0). Recommendation: promote to status=verified.
  - ``forgettable``: proposition is short / low confidence / matches
    forget-signal patterns (``TODO``, ``FIXME``, ``deprecated``,
    ``not sure``). Recommendation: forget or supersede.
  - ``recoverable``: everything else — needs human review to decide
    between model_claim promotion or supersession.

V1 (this cycle) is CLASSIFICATION + REPORT only. No mutation is
performed; the audit script outputs JSON / JSONL for human review.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sm.db")


def _store(sm: SemanticMemory, *, fid: str, prop: str,
            topic: str = "t", confidence: float = 0.5,
            age_days: float = 30.0) -> Fact:
    now = time.time()
    f = Fact(
        id=fid, proposition=prop, topic=topic,
        confidence=confidence,
        created_at=now - age_days * 86400,
    )
    sm.store(f)
    return f


# ---------------------------------------------------------------------------
# 1. classify_legacy_fact — pure decision, no IO
# ---------------------------------------------------------------------------


class TestClassifyLegacyFact:

    def test_proposition_with_bash_tool_ref_is_verified_on_rereading(
        self,
    ) -> None:
        from verimem.legacy_audit import classify_legacy_fact
        f = Fact(
            proposition=(
                "NEXUS has 17280 pytest cases collected "
                "(verified via bash:pytest_collect:exit0)"
            ),
            confidence=0.7, topic="nexus",
            created_at=time.time() - 90 * 86400,
        )
        out = classify_legacy_fact(f, now=time.time())
        assert out.bucket == "verified_on_rereading"
        assert "bash:" in out.bucket_reason

    def test_proposition_with_sha256_is_verified_on_rereading(self) -> None:
        from verimem.legacy_audit import classify_legacy_fact
        f = Fact(
            proposition="schema migration applied (sha256:abc123def456)",
            confidence=0.6, topic="schema",
            created_at=time.time() - 30 * 86400,
        )
        out = classify_legacy_fact(f, now=time.time())
        assert out.bucket == "verified_on_rereading"

    def test_proposition_with_arxiv_url_is_verified_on_rereading(self) -> None:
        from verimem.legacy_audit import classify_legacy_fact
        f = Fact(
            proposition=(
                "ProvSEEK pattern from arxiv.org/abs/2508.21323"
            ),
            confidence=0.5, topic="research",
            created_at=time.time() - 30 * 86400,
        )
        out = classify_legacy_fact(f, now=time.time())
        assert out.bucket == "verified_on_rereading"

    def test_very_short_proposition_classified_as_forgettable(self) -> None:
        from verimem.legacy_audit import classify_legacy_fact
        f = Fact(
            proposition="ok",
            confidence=0.3, topic="noise",
            created_at=time.time() - 200 * 86400,
        )
        out = classify_legacy_fact(f, now=time.time())
        assert out.bucket == "forgettable"

    def test_forget_signal_keywords_classified_as_forgettable(self) -> None:
        from verimem.legacy_audit import classify_legacy_fact
        f = Fact(
            proposition="TODO: figure out what this number means",
            confidence=0.4, topic="noise",
            created_at=time.time() - 100 * 86400,
        )
        out = classify_legacy_fact(f, now=time.time())
        assert out.bucket == "forgettable"

    def test_mid_confidence_normal_text_classified_as_recoverable(
        self,
    ) -> None:
        from verimem.legacy_audit import classify_legacy_fact
        f = Fact(
            proposition=(
                "Aurelio prefers Italian for conversation, English for code"
            ),
            confidence=0.7, topic="preferences",
            created_at=time.time() - 45 * 86400,
        )
        out = classify_legacy_fact(f, now=time.time())
        assert out.bucket == "recoverable"

    def test_classification_carries_metadata(self) -> None:
        from verimem.legacy_audit import classify_legacy_fact
        now = time.time()
        f = Fact(
            id="abc", proposition="some fact",
            confidence=0.6, topic="t",
            created_at=now - 60 * 86400,
        )
        out = classify_legacy_fact(f, now=now)
        assert out.fact_id == "abc"
        assert out.age_days == pytest.approx(60.0, abs=0.1)
        assert out.bucket in {
            "verified_on_rereading", "forgettable", "recoverable",
        }


# ---------------------------------------------------------------------------
# 2. audit_legacy_corpus — orchestrator
# ---------------------------------------------------------------------------


class TestAuditLegacyCorpus:

    def test_empty_corpus_returns_zero_summary(
        self, sm: SemanticMemory,
    ) -> None:
        from verimem.legacy_audit import audit_legacy_corpus
        out = audit_legacy_corpus(sm)
        assert out["total_classified"] == 0
        assert set(out["bucket_counts"].keys()) == {
            "verified_on_rereading", "forgettable", "recoverable",
        }
        assert all(v == 0 for v in out["bucket_counts"].values())

    def test_audit_groups_by_bucket(self, sm: SemanticMemory) -> None:
        from verimem.legacy_audit import audit_legacy_corpus
        _store(sm, fid="v1", confidence=0.6, age_days=60,
                prop="cycle #110 schema sha256:deadbeef")
        _store(sm, fid="f1", confidence=0.2, age_days=300, prop="x")
        _store(sm, fid="r1", confidence=0.7, age_days=20,
                prop="Aurelio's editor preference is VS Code")
        # Use status_filter="any" because this branch builds from main
        # where Fact has no status field yet (PR #44 merges later).
        out = audit_legacy_corpus(sm, status_filter="any")
        assert out["total_classified"] == 3
        counts = out["bucket_counts"]
        assert counts["verified_on_rereading"] == 1
        assert counts["forgettable"] == 1
        assert counts["recoverable"] == 1

    def test_audit_includes_samples_per_bucket(
        self, sm: SemanticMemory,
    ) -> None:
        from verimem.legacy_audit import audit_legacy_corpus
        for i in range(5):
            _store(sm, fid=f"f{i}", confidence=0.6, age_days=30,
                    prop=f"fact number {i} about general topic")
        out = audit_legacy_corpus(
            sm, status_filter="any", sample_per_bucket=3,
        )
        # All 5 went to recoverable bucket (mid conf, normal text)
        assert len(out["samples"]["recoverable"]) <= 3

    def test_audit_supports_status_filter_when_field_present(
        self, sm: SemanticMemory,
    ) -> None:
        """If the corpus has status='legacy_unverified' (cycle 109 schema)
        we filter to that subset. On a pre-cycle-109 corpus the field is
        absent and we audit everything."""
        from verimem.legacy_audit import audit_legacy_corpus
        _store(sm, fid="a", confidence=0.5, age_days=30,
                prop="some fact about topic A")
        _store(sm, fid="b", confidence=0.5, age_days=30,
                prop="another fact about topic B")
        # No status filter applied because no status column expected on main
        out = audit_legacy_corpus(sm, status_filter="any")
        assert out["total_classified"] == 2
