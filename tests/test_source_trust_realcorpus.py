"""TDD for the real-corpus source-trust validation (fork B: held-out reproduction
on REAL VeriMem data — the precondition source_trust.py declares for any default
flip). Pure-function tests only; the heavy real-gate run is the experiment, driven
by ``python -m benchmark.source_trust_realcorpus`` and verified empirically.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmark.source_trust_realcorpus import (
    RealCorpusConfig,
    _source_ref,
    build_events,
    classify_writer,
    curve_verdict,
    extract_outcomes,
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


def test_extract_outcomes_blames_false_asserts_credits_true():
    """Outcome feed = a-posteriori use feedback: one (source, good) per (source, key),
    good iff the asserted value matches the ground truth. An honest source that
    slipped on a key gets bad THERE only; a liar gets bad everywhere."""
    facts = load_corpus(str(_HALUEVAL), n=6, seed=11)
    cfg = RealCorpusConfig(n_honest=3, n_liars=1, n_colluders=2,
                           cartel_keys=2, p_honest_noise=0.5, seed=11)
    events = build_events(facts, cfg)
    outs = extract_outcomes(events)
    seen = {(s, k) for s, k, _ in outs}
    assert len(seen) == len(outs)                      # one verdict per (source, key)
    by = {(s, k): g for s, k, g in outs}
    for ev in events:
        good = by[(ev["source"], ev["key"])]
        if ev["kind"] in ("liar", "colluder"):
            assert good is False
        else:                                          # honest: good iff no slip
            assert good is (ev["value"] == ev["true_value"])
    # with 50% noise some honest slips must exist — the interesting regime
    assert any(not g for (s, k), g in by.items() if s.startswith("honest"))


def test_curve_verdict_h2_h3():
    """H2: no inversion at ANY point. H3: outcome rescues the recall (<=0.5*OFF)
    and pins the liar under the floor for every noise <= 0.20."""
    def pt(noise, wl_off, wl_dec, wl_out, hon, car, liar_out):
        return {"noise": noise, "off": {"wrong_liar_rate": wl_off},
                "on_indep_deconf": {"wrong_liar_rate": wl_dec,
                                    "honest_consistency": hon,
                                    "cartel_consistency": car},
                "deconf_outcome": {"wrong_liar_rate": wl_out,
                                   "liar_trust_min": liar_out}}
    good_curve = [pt(0.0, .25, .00, .00, .95, .20, .02),
                  pt(0.10, .25, .05, .00, .90, .30, .05),
                  pt(0.20, .30, .15, .10, .85, .40, .10),
                  pt(0.25, .30, .20, .20, .80, .45, .12)]
    v = curve_verdict(good_curve)
    assert v["H2_no_inversion"] is True
    assert v["H3_outcome_rescue"] is True              # 0.25 excluded by design
    assert v["robust_regime_holds"] is True

    inverted = [dict(p) for p in good_curve]
    inverted[2] = pt(0.20, .30, .15, .10, .35, .40, .10)   # cartel out-ranks honest
    v2 = curve_verdict(inverted)
    assert v2["H2_no_inversion"] is False
    assert v2["robust_regime_holds"] is False

    weak_rescue = [dict(p) for p in good_curve]
    weak_rescue[2] = pt(0.20, .30, .15, .20, .85, .40, .10)  # 0.20 > 0.5*0.30
    v3 = curve_verdict(weak_rescue)
    assert v3["H3_outcome_rescue"] is False
    assert v3["robust_regime_holds"] is False


def test_classify_writer_attributes_wrong_answers():
    """Diagnosis axis: a wrong top-hit is attributed to WHO wrote the surviving
    copy — a deceiver (liar/colluder, should have been retro-demoted) or an honest
    slip (admitted because its source is rightly trusted: the informational limit)."""
    assert classify_writer('["source-doc:honest_2:w"]') == "honest_slip"
    assert classify_writer('["source-doc:liar_0:w"]') == "deceiver"
    assert classify_writer('["source-doc:colluder_3:w"]') == "deceiver"
    assert classify_writer('[]') == "other"
    assert classify_writer(None) == "other"


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
