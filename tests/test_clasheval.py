"""ClashEval harness (task #19) — prior-vs-evidence conflict, TDD.

The last unstressed trust-core front (transfer §4): read-path confabulation
that customers see comes from the CONFLICT between the model's prior and the
store's evidence, not from clean evidence. Items are DECLARED COUNTERFACTUALS
— the store's value is the gold BY DEFINITION OF THE TEST (a customer's
memory outranks the model's stale prior); no world-truth claim is made.
"""
from __future__ import annotations

from benchmark.external_clasheval import CLASH_ITEMS, build_clash_prompt


def test_items_are_wellformed_counterfactuals():
    assert len(CLASH_ITEMS) >= 20
    for it in CLASH_ITEMS:
        assert it["class"] in ("prior_conflict", "post_cutoff")
        assert it["store_fact"] and it["question"]
        assert it["store_value"].lower() not in (it.get("prior_value") or "").lower(), (
            "store value must differ from the expected prior")
        # the store fact must actually carry the store value
        assert it["store_value"] in it["store_fact"]


def test_prior_conflict_items_have_a_prior():
    pc = [i for i in CLASH_ITEMS if i["class"] == "prior_conflict"]
    assert len(pc) >= 12
    assert all(i.get("prior_value") for i in pc)


def test_clash_prompt_neutral_with_provenance_and_contract():
    it = CLASH_ITEMS[0]
    ctx = [{"text": it["store_fact"], "status": "admitted", "score": 0.93,
            "id": "f1"}]
    p = build_clash_prompt(it, context=ctx)
    assert it["question"] in p
    assert it["store_fact"] in p and "admitted" in p
    assert "ANSWER:" in p
    # neutral: no pressure wording, no 'ignore your training' coercion
    low = p.lower()
    assert "are you sure" not in low and "ignore" not in low


def test_clash_prompt_baseline_has_no_store():
    it = CLASH_ITEMS[0]
    p = build_clash_prompt(it, context=None)
    assert it["store_value"] not in p, "baseline must not leak the store value"
    assert "memory" not in p.lower()
