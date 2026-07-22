"""L3-semantic NLI pre-filter — DEFAULT ON with the converged SAFE rule.

History (2026-07-22): the first cut skipped every different-subject sibling
(same_subject). External adversarial review (GLM-5.2 + Kimi-K3, independent
convergence) refuted that rule: a HEAD MISMATCH is the alias signature
("North Macedonia"~"FYROM", measured 35.2% FN on Wikidata skos:altLabel), and
renames are where conflicts concentrate (mergers, rebrands) — an attacker
bypasses the NLI by renaming the subject. Their converged prescription, shipped
here as the DEFAULT:

  SKIP the judge ONLY for same-head + both-sided DISJOINT-modifier pairs
  ("the payments team ..." vs "the design team ..." — the measured FP class).
  Head mismatch NEVER skips. Bare heads and pronoun/empty subjects never skip.
  FPs quarantine (recoverable); FNs poison (permanent) — asymmetric harm.

ENGRAM_L3_SUBJECT_FILTER: default ON; "0"/"false"/"off"/"no" opts out to the
unfiltered judge. Wiring idiom: detect_semantic_conflicts stubbed with a spy
(no e5, no claude, no NLI model).
"""
from __future__ import annotations

import types

import pytest

from verimem import anti_confab_gate, semantic_conflict
from verimem.coherence_check import CoherenceWarning

CANDIDATE = "The payments team migrated to Stripe in 2025."
SIB_FP = "The design team runs a weekly critique on Fridays."       # skip class
SIB_SAME = "The payments team still runs on the legacy processor."  # judge
SIB_RENAME = "The checkout squad reverted to the legacy processor." # judge (head mismatch)
SIB_BARE = "The team adopted a new processor."                      # judge (bare head)


class _StubSemantic:
    def __init__(self, props):
        self._props = props

    def all(self):
        return [types.SimpleNamespace(id=f"sib{i}", proposition=p, topic="t")
                for i, p in enumerate(self._props)]


class _StubLLM:
    def complete(self, *a, **k):  # never consulted: detector is stubbed
        return types.SimpleNamespace(text="NEUTRAL")


def _agent(props):
    a = types.SimpleNamespace()
    a.llm = _StubLLM()
    a.semantic = _StubSemantic(props)
    return a


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    monkeypatch.delenv("ENGRAM_L3_SUBJECT_FILTER", raising=False)
    yield


def _spy(monkeypatch):
    """Stub the detector; record the sibling propositions it receives and flag
    every one of them as a contradiction (worst-case judge)."""
    seen: list[list[str]] = []

    def _fake(new, sibs, judge):
        sib_list = list(sibs)
        seen.append([getattr(s, "proposition", "") for s in sib_list])
        return [CoherenceWarning(kind="semantic_conflict",
                                 other_fact_id=getattr(s, "id", ""))
                for s in sib_list]
    monkeypatch.setattr(semantic_conflict, "detect_semantic_conflicts", _fake)
    return seen


def _gate(props, proposition=CANDIDATE):
    return anti_confab_gate.run_validation_gate(
        proposition=proposition, verified_by=None, topic="t",
        agent=_agent(props), validate="full")


def test_default_on_fp_class_skipped_rename_and_same_judged(monkeypatch):
    """DEFAULT ON: only the same-head-disjoint-modifier sibling is skipped;
    same-subject, RENAMED-subject (head mismatch = alias signature) and
    bare-head siblings all still reach the judge."""
    seen = _spy(monkeypatch)
    _gate([SIB_FP, SIB_SAME, SIB_RENAME, SIB_BARE])
    assert seen and set(seen[0]) == {SIB_SAME, SIB_RENAME, SIB_BARE}
    assert SIB_FP not in seen[0]


def test_default_on_brand_as_modifier_rebrand_reaches_judge(monkeypatch):
    """Critic bfa3bce6 counterexample, pinned: 'the Twitter app' vs 'the X app'
    share the head with disjoint modifiers, but the modifier IS the identity —
    a rebrand, not a different subject. The skip is restricted to
    ORGANIZATIONAL-UNIT heads (team/group/…) where modifiers partition;
    artifact heads (app/platform/…) must always reach the judge."""
    seen = _spy(monkeypatch)
    res = anti_confab_gate.run_validation_gate(
        proposition="The Twitter app was banned in India.",
        verified_by=None, topic="t",
        agent=_agent(["The X app was restored in India."]), validate="full")
    assert seen and seen[0] == ["The X app was restored in India."]
    assert any(w.get("layer") == "L3-semantic" for w in res.warnings)
    seen2 = _spy(monkeypatch)
    anti_confab_gate.run_validation_gate(
        proposition="The Facebook platform was fined in 2022.",
        verified_by=None, topic="t",
        agent=_agent(["The Meta platform was cleared in 2022."]),
        validate="full")
    assert seen2 and seen2[0] == ["The Meta platform was cleared in 2022."]


def test_default_on_head_mismatch_never_skipped(monkeypatch):
    """The GLM+Kimi poisoning vector, pinned: a renamed subject must reach the
    judge — skipping on head mismatch would let 'Aurora (formerly Northwind)'
    contradictions in silently."""
    seen = _spy(monkeypatch)
    res = _gate([SIB_RENAME])
    assert seen and seen[0] == [SIB_RENAME]
    assert any(w.get("layer") == "L3-semantic" for w in res.warnings)


def test_default_on_unattributable_candidate_judges_everything(monkeypatch):
    seen = _spy(monkeypatch)
    _gate([SIB_FP, SIB_RENAME], proposition="It was migrated on Tuesday.")
    assert seen and set(seen[0]) == {SIB_FP, SIB_RENAME}


def test_optout_restores_unfiltered_judge(monkeypatch):
    monkeypatch.setenv("ENGRAM_L3_SUBJECT_FILTER", "0")
    seen = _spy(monkeypatch)
    _gate([SIB_FP, SIB_SAME, SIB_RENAME])
    assert seen and set(seen[0]) == {SIB_FP, SIB_SAME, SIB_RENAME}
