"""Tier-2 semantic judge + trust-assessment pipeline — TDD (RED first).

The pipeline composes the existing deterministic layers with a pluggable
LLM judge:
  Tier-1 (evidence_requirement)  WITHHOLDS trust from a specific unsourced claim.
  Corroboration                  RESTORES it deterministically (independent witnesses).
  Tier-2 judge                   TRIAGES the still-ambiguous remainder.

NON-NEGOTIABLE invariant under test: the judge may only LOWER trust (declass)
or FLAG a promotion candidate — it can NEVER raise trust on its opinion alone.
Only deterministic evidence (corroboration / verified_by) restores trust.
"""
from __future__ import annotations

import pytest

from verimem.evidence_requirement import UNSOURCED_SPECIFIC_CEILING
from verimem.semantic import Fact
from verimem.tier2_judge import (
    FixedJudge,
    Judge,
    JudgeAction,
    JudgeVerdict,
    RecordingJudge,
    assess_claim_trust,
)


def _f(prop, topic="eng/x", confidence=0.9, verified_by=None):
    return Fact(
        proposition=prop,
        topic=topic,
        confidence=confidence,
        verified_by=list(verified_by or []),
    )


def test_judge_protocol_is_runtime_checkable():
    assert isinstance(FixedJudge(JudgeVerdict(JudgeAction.KEEP, "x")), Judge)


def test_sourced_claim_passes_through_and_skips_judge():
    judge = RecordingJudge(JudgeVerdict(JudgeAction.DECLASS, "noise"))
    fact = _f("Latency is 1234 ms.", verified_by=["bash:bench:exit0"])
    d = assess_claim_trust(fact, judge=judge, enabled=True)
    assert d.stage == "pass_through"
    assert d.confidence == pytest.approx(0.9)
    assert judge.calls == []  # sourced → judge never consulted


def test_generic_claim_passes_through():
    judge = RecordingJudge(JudgeVerdict(JudgeAction.DECLASS, "noise"))
    fact = _f("The system feels fast and reliable.")
    d = assess_claim_trust(fact, judge=judge, enabled=True)
    assert d.stage == "pass_through"
    assert judge.calls == []


def test_specific_unsourced_uncorroborated_is_withheld_without_judge():
    fact = _f("The ring holds 4096 entries.", confidence=0.9)
    d = assess_claim_trust(fact, enabled=True)  # no judge supplied
    assert d.stage == "withheld"
    assert d.action == "cap_confidence"
    assert d.confidence == pytest.approx(UNSOURCED_SPECIFIC_CEILING)


def test_corroboration_restores_and_skips_judge():
    judge = RecordingJudge(JudgeVerdict(JudgeAction.DECLASS, "noise"))
    fact = _f("The cache is bounded at 1024 entries.", topic="eng/cache")
    peers = [
        _f("Cache holds 1024 entries maximum.", topic="docs/cache"),
        _f("The cache capacity is 1024 entries.", topic="ops/cache"),
    ]
    d = assess_claim_trust(
        fact, corpus=peers, judge=judge, enabled=True, min_corroborations=2,
    )
    assert d.stage == "restored"
    assert d.corroborations >= 2
    assert d.confidence == pytest.approx(0.9)  # full trust earned back
    assert judge.calls == []  # deterministic evidence beats opinion


def test_judge_declass_lowers_trust():
    fact = _f("The buffer is 4096 entries.", confidence=0.9)
    judge = FixedJudge(JudgeVerdict(JudgeAction.DECLASS, "looks like a log snapshot"))
    d = assess_claim_trust(fact, judge=judge, enabled=True)
    assert d.stage == "judged"
    assert d.action == "declass"
    assert d.status_hint == "quarantined"
    assert d.confidence < UNSOURCED_SPECIFIC_CEILING


def test_judge_promote_candidate_never_auto_raises_trust():
    # THE INVARIANT: judge opinion alone cannot mint trust.
    fact = _f("The buffer is 4096 entries.", confidence=0.9)
    judge = FixedJudge(
        JudgeVerdict(JudgeAction.PROMOTE_CANDIDATE, "plausible durable config", confidence=0.95)
    )
    d = assess_claim_trust(fact, judge=judge, enabled=True)
    assert d.stage == "judged"
    assert d.action == "flag_promote_candidate"
    assert d.confidence <= UNSOURCED_SPECIFIC_CEILING  # NOT promoted
    assert d.confidence <= fact.confidence  # never raised above input


def test_judge_keep_leaves_tier1_cap():
    fact = _f("The buffer is 4096 entries.", confidence=0.9)
    judge = FixedJudge(JudgeVerdict(JudgeAction.KEEP, "neutral"))
    d = assess_claim_trust(fact, judge=judge, enabled=True)
    assert d.stage == "judged"
    assert d.action == "cap_confidence"
    assert d.confidence == pytest.approx(UNSOURCED_SPECIFIC_CEILING)


def test_judge_only_consulted_for_ambiguous_bucket():
    judge = RecordingJudge(JudgeVerdict(JudgeAction.KEEP, "neutral"))
    sourced = _f("A is 10 ms.", topic="eng/a", verified_by=["url:x"])
    generic = _f("B is robust.", topic="eng/b")
    ambiguous = _f("C is 777 entries.", topic="eng/c")
    for fct in (sourced, generic, ambiguous):
        assess_claim_trust(fct, judge=judge, enabled=True)
    props = [p for (p, _t) in judge.calls]
    assert props == ["C is 777 entries."]


def test_disabled_passes_everything_through():
    judge = RecordingJudge(JudgeVerdict(JudgeAction.DECLASS, "noise"))
    fact = _f("The ring holds 4096 entries.", confidence=0.9)
    d = assess_claim_trust(fact, judge=judge, enabled=False)
    assert d.stage == "pass_through"
    assert d.confidence == pytest.approx(0.9)
    assert judge.calls == []


@pytest.mark.parametrize("action", list(JudgeAction))
@pytest.mark.parametrize("conf", [0.95, 0.6, 0.4, 0.2])
def test_confidence_never_raised_above_input_for_any_verdict(action, conf):
    # Global invariant: assess_claim_trust is monotone NON-INCREASING on
    # confidence — no verdict, on any input confidence, can raise it. A judge
    # opinion can only withhold/lower, never mint trust.
    fact = _f("The buffer is 4096 entries.", confidence=conf)
    judge = FixedJudge(JudgeVerdict(action, "r", confidence=0.99))
    d = assess_claim_trust(fact, judge=judge, enabled=True)
    assert d.confidence <= conf + 1e-9
