"""Cycle #114 — legacy corpus cleanup: forget the `forgettable` bucket.

Cycle 110.D (PR #48) shipped `classify_legacy_fact` + `audit_legacy_corpus`,
both REPORT-ONLY. Cycle #114 closes the schema-debt loop: actually delete
the legacy_unverified facts that the classifier flags as `forgettable`
(short / very-low-confidence / TODO/FIXME/deprecated keyword).

Conservative design:

* Only act on the `forgettable` bucket. `verified_on_rereading` requires
  cycle #111 v2 I/O hard-gate to promote (out of scope here).
  `recoverable` is human-review territory.
* Always default to ``dry_run=True``. The caller must opt-in to mutation.
* Returns a structured report (counts + sample) so the CLI can show
  the user what will / did happen.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sm.db")


def _seed_mixed(sm: SemanticMemory, *, now: float) -> dict[str, str]:
    """Seed a corpus that exercises all 3 buckets + a verified row that
    must NEVER be deleted by the cleanup."""
    facts = {
        "forget_short": Fact(
            id="f-short", proposition="todo fix this",
            topic="lessons/x", confidence=0.5,
            status="legacy_unverified", created_at=now,
        ),
        "forget_lowconf": Fact(
            id="f-low", proposition="some short claim that is questionable",
            topic="lessons/x", confidence=0.2,
            status="legacy_unverified", created_at=now,
        ),
        "forget_keyword": Fact(
            id="f-todo",
            proposition="LESSON LEARNED: deprecated approach we should drop",
            # Cycle 114 guardrail: confidence must be <= 0.85 to be
            # eligible for actual deletion (long / high-confidence rows
            # are kept even if classifier flags them forgettable).
            topic="lessons/x", confidence=0.7,
            status="legacy_unverified", created_at=now,
        ),
        "recoverable_neutral": Fact(
            id="f-rec",
            proposition=(
                "Cycle 109 introduces provenance schema v3 with verified_by, "
                "status, source_signature columns"
            ),
            topic="project/hippoagent", confidence=0.85,
            status="legacy_unverified", created_at=now,
        ),
        "verified_signal_in_text": Fact(
            id="f-ver-in-text",
            proposition="bench passed: pytest exit 0 on 12345 tests",
            topic="project/x", confidence=0.9,
            status="legacy_unverified", created_at=now,
        ),
        "real_verified_keep": Fact(
            id="f-keep",
            proposition="cycle 111 v2 hard-gate landed",
            topic="project/x", confidence=0.95,
            status="model_claim", created_at=now,
        ),
    }
    for f in facts.values():
        sm.store(f)
    return {k: v.id for k, v in facts.items()}


class TestCleanupDryRunIsDefault:
    """Safety: by default the cleanup MUST NOT delete anything."""

    def test_dry_run_default_no_deletion(self, sm: SemanticMemory) -> None:
        from verimem.legacy_cleanup import cleanup_forgettable
        ids = _seed_mixed(sm, now=time.time())
        before = sm.count()

        report = cleanup_forgettable(sm)

        assert report["dry_run"] is True
        assert report["forgotten"] == 0
        # the report still lists candidates that WOULD be deleted
        assert report["would_forget"] >= 3
        # corpus untouched
        assert sm.count() == before
        # every seeded id still exists
        for _, fid in ids.items():
            assert sm.get(fid) is not None


class TestCleanupBucketsForgettableOnly:
    """Only the forgettable bucket is acted upon."""

    def test_wet_run_deletes_forgettable(self, sm: SemanticMemory) -> None:
        from verimem.legacy_cleanup import cleanup_forgettable
        ids = _seed_mixed(sm, now=time.time())
        before = sm.count()

        report = cleanup_forgettable(sm, dry_run=False)

        assert report["dry_run"] is False
        assert report["forgotten"] >= 3
        # exactly the 3 forgettable rows are gone
        assert sm.get(ids["forget_short"]) is None
        assert sm.get(ids["forget_lowconf"]) is None
        assert sm.get(ids["forget_keyword"]) is None
        # non-forgettable rows survive
        assert sm.get(ids["recoverable_neutral"]) is not None
        assert sm.get(ids["verified_signal_in_text"]) is not None
        assert sm.get(ids["real_verified_keep"]) is not None
        # corpus shrunk by exactly the forgotten count
        assert sm.count() == before - report["forgotten"]

    def test_never_touches_non_legacy_statuses(
        self, sm: SemanticMemory,
    ) -> None:
        from verimem.legacy_cleanup import cleanup_forgettable
        # A short 'todo' fact in model_claim status MUST NOT be deleted —
        # cleanup only touches legacy_unverified.
        f = Fact(
            id="f-modelclaim-short", proposition="todo refactor",
            topic="t", confidence=0.5,
            status="model_claim", created_at=time.time(),
        )
        sm.store(f)

        report = cleanup_forgettable(sm, dry_run=False)
        assert report["forgotten"] == 0
        assert sm.get("f-modelclaim-short") is not None


class TestCleanupMaxLimit:
    """`max_forget` caps how many rows can be deleted in one run."""

    def test_max_forget_limits_deletions(self, sm: SemanticMemory) -> None:
        from verimem.legacy_cleanup import cleanup_forgettable
        ids = _seed_mixed(sm, now=time.time())

        report = cleanup_forgettable(sm, dry_run=False, max_forget=1)
        assert report["forgotten"] == 1
        # 2 of 3 forgettable rows still survive
        survivors = sum(
            1 for k in ("forget_short", "forget_lowconf", "forget_keyword")
            if sm.get(ids[k]) is not None
        )
        assert survivors == 2


class TestCleanupReportShape:
    """Report shape used by the CLI."""

    def test_report_has_expected_keys(self, sm: SemanticMemory) -> None:
        from verimem.legacy_cleanup import cleanup_forgettable
        _seed_mixed(sm, now=time.time())

        report = cleanup_forgettable(sm)
        for k in (
            "dry_run", "forgotten", "would_forget", "samples",
            "total_legacy_scanned",
        ):
            assert k in report, f"missing key: {k}"
        # samples are bounded to at most 5
        assert len(report["samples"]) <= 5
        # each sample has the minimum fields a human needs to triage
        for s in report["samples"]:
            assert "fact_id" in s
            assert "proposition" in s
            assert "bucket_reason" in s


class TestCleanupGuardrails:
    """Cycle #114 guardrail: refuse to delete rows that are too long or
    too confident, even if the classifier flagged them as forgettable.

    Rationale: on the real HippoAgent corpus the legacy_audit classifier
    catches 200+ char lesson-learned narratives with confidence=1.0
    just because they mention 'deprecated' or 'TODO' somewhere. Those
    are valuable context, not junk."""

    def test_long_proposition_with_keyword_is_kept(
        self, sm: SemanticMemory,
    ) -> None:
        from verimem.legacy_cleanup import cleanup_forgettable
        long_text = (
            "Lesson learned 2026-05-13: the deprecated old API still has "
            "callers in production and removing it without a migration "
            "plan caused a cascade of failures. This is the same kind of "
            "trap we hit on cycle 87 and again on cycle 102. The pattern "
            "we now follow: add the new API, dual-write, migrate readers, "
            "remove the deprecated one only after a full release cycle."
        )
        assert len(long_text) > 200
        sm.store(Fact(
            id="f-long", proposition=long_text, topic="lessons/x",
            confidence=1.0, status="legacy_unverified",
            created_at=time.time(),
        ))

        report = cleanup_forgettable(sm, dry_run=False)

        assert report["forgotten"] == 0
        assert report["skipped_by_guardrails"] >= 1
        assert sm.get("f-long") is not None

    def test_high_confidence_short_keyword_is_kept(
        self, sm: SemanticMemory,
    ) -> None:
        from verimem.legacy_cleanup import cleanup_forgettable
        sm.store(Fact(
            id="f-shortconf", proposition="todo: refactor module",
            topic="t", confidence=0.95, status="legacy_unverified",
            created_at=time.time(),
        ))

        report = cleanup_forgettable(sm, dry_run=False)

        assert report["forgotten"] == 0
        assert sm.get("f-shortconf") is not None


class TestCleanupEmptyCorpus:
    """Don't crash on an empty corpus."""

    def test_empty_corpus_returns_zero(self, sm: SemanticMemory) -> None:
        from verimem.legacy_cleanup import cleanup_forgettable
        report = cleanup_forgettable(sm)
        assert report["forgotten"] == 0
        assert report["would_forget"] == 0
        assert report["total_legacy_scanned"] == 0
