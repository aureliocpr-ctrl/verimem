"""L1 false-positive reduction (2026-06-14).

The anti-confab gate quarantines a fact when an L1.x detector fires. Measured on
the live store: 57.8% of curated facts are quarantined, ~18% of them real
knowledge (project/lessons with commit SHAs) lost to FALSE POSITIVES — and the
recall path hard-excludes quarantined rows, so that knowledge is invisible.

Two FPs caught dogfooding a real fix-fact:
  - L1.18 (automation): the bare word "recurring" in "recurring recall block"
    (a DESCRIPTIVE recurring *problem*, not a scheduled job) was flagged.
  - L1.9 (performance): a real measure in verified_by ("stress:...3125ms...") was
    not recognized because "stress:" wasn't an accepted evidence prefix.

These tests pin the FIXED behavior WITHOUT weakening the true positives the
detectors exist to catch (M12-PTY perf hallucinations, unscheduled cron claims).
"""
from __future__ import annotations

from verimem.l1_automated_detector import detect_unsupported_automated_claim
from verimem.l1_performance_detector import detect_unsupported_performance_claim

# --- L1.18: "recurring/periodic <problem>" is descriptive, not an automation claim ---

def test_recurring_problem_is_not_an_automation_claim():
    # The exact dogfooded FP.
    assert detect_unsupported_automated_claim(
        proposition="Engram recurring recall/save hang ROOT cause found",
        verified_by=None,
    ) is None
    assert detect_unsupported_automated_claim(
        proposition="killed the recurring recall block (the 3s tail)",
        verified_by=None,
    ) is None
    assert detect_unsupported_automated_claim(
        proposition="a periodic memory leak in the encode path",
        verified_by=None,
    ) is None


def test_real_automation_claim_without_scheduler_evidence_still_flags():
    # True positive MUST survive: an automation claim with no descriptive
    # problem-noun and no scheduler evidence is still caught.
    w = detect_unsupported_automated_claim(
        proposition="the corpus consolidation is scheduled nightly",
        verified_by=None,
    )
    assert w is not None and w.matched_text.lower() == "scheduled"
    w2 = detect_unsupported_automated_claim(
        proposition="the sync runs recurring across all instances",
        verified_by=None,
    )
    assert w2 is not None  # "recurring" with no problem-noun nearby → still flagged


def test_automation_claim_with_scheduler_evidence_passes():
    assert detect_unsupported_automated_claim(
        proposition="the backup runs recurring",
        verified_by=["cron:0 2 * * *"],
    ) is None


def test_real_automation_keyword_coexisting_with_recurring_problem_still_flags():
    """Critic counterexample 2026-06-14: a genuine 'scheduled'/'automated' claim
    must still flag even when a 'recurring <problem>' phrase is in the same
    proposition (the descriptive pass is per-keyword, not proposition-wide)."""
    for prop in (
        "scheduled job to catch the recurring crash",
        "automated cleanup fixes the recurring leak",
        "the recurring crash is handled by a scheduled nightly job",
    ):
        w = detect_unsupported_automated_claim(proposition=prop, verified_by=None)
        assert w is not None, prop
        assert w.matched_text.lower() in ("scheduled", "automated"), prop


# --- L1.9: a measure-bearing stress:/test: ref counts as perf evidence ---

_PERF_PROP = "recall p95 3125ms -> 415ms after the cold-budget fix"


def test_stress_ref_with_measure_counts_as_evidence():
    # The exact dogfooded FP: stress: ref carrying a real measure.
    assert detect_unsupported_performance_claim(
        proposition=_PERF_PROP,
        verified_by=["stress:recall-p95-3125ms-to-415ms,save-p95-71ms-noloss"],
    ) is None
    assert detect_unsupported_performance_claim(
        proposition=_PERF_PROP,
        verified_by=["test:rerank-p95-47ms"],
    ) is None


def test_naked_stress_ref_without_measure_still_flags():
    # No measure in the ref → still unsupported (don't weaken M12-PTY guard).
    w = detect_unsupported_performance_claim(
        proposition=_PERF_PROP,
        verified_by=["stress:much-faster-now"],
    )
    assert w is not None and w.pattern_kind == "arrow_latency"


def test_perf_claim_with_no_evidence_still_flags():
    assert detect_unsupported_performance_claim(
        proposition=_PERF_PROP, verified_by=None,
    ) is not None
