"""TDD for the real-corpus source-trust validation (fork B: held-out reproduction
on REAL VeriMem data — the precondition source_trust.py declares for any default
flip). Pure-function tests only; the heavy real-gate run is the experiment, driven
by ``python -m benchmark.source_trust_realcorpus`` and verified empirically.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import json

from benchmark.source_trust_realcorpus import (
    RealCorpusConfig,
    _source_ref,
    build_events,
    load_corpus,
    verdict,
)
from engram.source_trust import canonical_source

_HALUEVAL = (Path(__file__).resolve().parent.parent
             / "benchmark" / "data" / "external" / "halueval_qa_heldout.jsonl")


def test_load_corpus_reads_real_fields():
    """Loads N real HaluEval facts: each has a distinct true vs false value,
    both non-empty — the raw material for a multi-source contest with ground truth."""
    facts = load_corpus(str(_HALUEVAL), n=12, seed=11)
    assert len(facts) == 12
    for f in facts:
        assert f["question"].strip()
        assert f["true_value"].strip()
        assert f["false_value"].strip()
        assert f["true_value"] != f["false_value"]   # a genuine contest
    # deterministic sampling
    assert load_corpus(str(_HALUEVAL), n=12, seed=11) == facts


def test_build_events_honest_assert_truth_liars_assert_false():
    """With zero honest noise every honest source asserts the ground truth and
    every liar asserts the real hallucinated value — the reputation contest."""
    facts = load_corpus(str(_HALUEVAL), n=10, seed=11)
    cfg = RealCorpusConfig(n_honest=4, n_liars=2, n_colluders=0,
                           cartel_keys=0, p_honest_noise=0.0, seed=11)
    events = build_events(facts, cfg)
    assert events, "expected a non-empty write stream"
    by_key = {f["key"]: f for f in facts}
    for ev in events:
        truth = by_key[ev["key"]]
        if ev["kind"] == "honest":
            assert ev["value"] == truth["true_value"]
        elif ev["kind"] == "liar":
            assert ev["value"] == truth["false_value"]
    # every contested key gets >=2 honest writers so a confirmation is possible
    honest_per_key: dict[str, set[str]] = {}
    for ev in events:
        if ev["kind"] == "honest":
            honest_per_key.setdefault(ev["key"], set()).add(ev["source"])
    assert all(len(s) >= 2 for s in honest_per_key.values())


def test_build_events_cartel_shares_one_false_value_across_distinct_ids():
    """A cartel = N colluders with DISTINCT ids all asserting the SAME real false
    value on the cartel keys — the manufactured-consensus attack, on real content."""
    facts = load_corpus(str(_HALUEVAL), n=10, seed=11)
    cfg = RealCorpusConfig(n_honest=4, n_liars=0, n_colluders=4,
                           cartel_keys=3, p_honest_noise=0.0, seed=11)
    events = build_events(facts, cfg)
    coll = [ev for ev in events if ev["kind"] == "colluder"]
    assert coll, "expected cartel events"
    by_key: dict[str, set[str]] = {}
    vals_by_key: dict[str, set[str]] = {}
    for ev in coll:
        by_key.setdefault(ev["key"], set()).add(ev["source"])
        vals_by_key.setdefault(ev["key"], set()).add(ev["value"])
    # exactly cartel_keys contested by the cartel, N distinct colluder ids each,
    # all asserting a SINGLE shared false value per key
    assert len(by_key) == 3
    for k, srcs in by_key.items():
        assert len(srcs) == 4
        assert len(vals_by_key[k]) == 1
        shared = next(iter(vals_by_key[k]))
        assert shared == next(f["false_value"] for f in facts if f["key"] == k)


def test_verdict_holds_only_when_all_criteria_pass():
    """The pre-registered gate: C1 independence denies the cartel, C2 no inversion,
    C3 honest restored, C4 liar-recall halved — reproduction_holds iff all pass."""
    off = {"cartel_consistency": 0.5, "honest_consistency": 0.5,
           "wrong_liar_rate": 0.40, "honest_neutral": False}
    on = {"cartel_consistency": 0.80, "honest_consistency": 0.70,
          "wrong_liar_rate": 0.10, "honest_neutral": False}
    indep = {"cartel_consistency": 0.55, "honest_consistency": 0.80,
             "wrong_liar_rate": 0.05, "honest_neutral": False}
    deconf = {"cartel_consistency": 0.30, "honest_consistency": 0.82,
              "wrong_liar_rate": 0.05, "honest_neutral": False}
    v = verdict(off, on, indep, deconf)
    assert v["C1_independence_denies_cartel"] is True
    assert v["C2_no_inversion_mature"] is True
    assert v["C3_honest_restored"] is True
    assert v["C4_liar_recall_halved"] is True
    assert v["reproduction_holds"] is True

    # break C1: cartel still trusted under independence -> whole verdict fails
    bad = verdict(off, on, {**indep, "cartel_consistency": 0.70}, deconf)
    assert bad["C1_independence_denies_cartel"] is False
    assert bad["reproduction_holds"] is False

    # honest never reach agreement -> inconclusive, not passed
    neutral = {"cartel_consistency": 0.5, "honest_consistency": 0.5,
               "wrong_liar_rate": 0.0, "honest_neutral": True}
    vi = verdict(off, on, neutral, neutral)
    assert vi["honest_inconclusive"] is True
    assert vi["reproduction_holds"] is False


def test_source_ref_survives_retro_demotion_pattern():
    """The write's source ref must (a) canonicalise back to the source and (b) match
    the retro-demotion LIKE pattern `%"<prefix>:<source>:%` (client._retro_demote_source,
    which needs a colon AFTER the source). A bare 'source-doc:liar_0' silently fails
    the pattern, so a sunk source's stored facts are never quarantined and the recall
    never improves — the bug this harness hit on the first real-corpus run."""
    ref = _source_ref("liar_0")
    assert canonical_source([ref]) == "liar_0"
    serialized = json.dumps([ref])                 # how the store persists verified_by
    assert '"source-doc:liar_0:' in serialized     # the retro-demotion pattern bites


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
