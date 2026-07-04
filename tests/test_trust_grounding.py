"""use_grounding folds the write-time grounding score (the proven moat signal, AUROC
0.971) into trust ranking. Opt-in: default off is byte-identical legacy; on, a strongly-
grounded fact outranks an ungrounded one at equal base/age. Hermetic."""
from __future__ import annotations

import types

from engram.trust_score import compute_trust_score, rank_facts_by_trust


def _fact(fid, prop, conf, ground, created):
    return types.SimpleNamespace(id=fid, proposition=prop, confidence=conf,
                                 grounding_score=ground, created_at=created)


def test_default_off_is_unchanged():
    f = _fact("a", "x", 0.8, 12.0, 1_000_000.0)
    off = compute_trust_score(f, now=1_000_000.0)
    assert off["components"]["grounding_factor"] == 1.0  # neutral when off
    # legacy formula: base*age*(1+corr) with no grounding term
    assert off["trust"] == 0.8


def test_none_grounding_is_neutral_even_when_on():
    f = _fact("a", "x", 0.8, None, 1_000_000.0)
    on = compute_trust_score(f, now=1_000_000.0, use_grounding=True)
    assert on["components"]["grounding_factor"] == 1.0 and on["trust"] == 0.8


def test_grounded_outranks_ungrounded_when_on():
    now = 1_000_000.0
    hi = _fact("hi", "fact one", 0.8, 95.0, now)
    lo = _fact("lo", "fact two", 0.8, 5.0, now)
    th = compute_trust_score(hi, now=now, use_grounding=True)["trust"]
    tl = compute_trust_score(lo, now=now, use_grounding=True)["trust"]
    assert th > tl  # high grounding -> higher trust
    # factors: 95->1.07, 5->0.53
    assert th == round(0.8 * (0.5 + 0.006 * 95), 4)
    assert tl == round(0.8 * (0.5 + 0.006 * 5), 4)


def test_rank_uses_grounding_to_reorder():
    now = 1_000_000.0
    # lo has slightly higher base but much lower grounding -> grounded hi wins when on
    hi = _fact("hi", "alpha", 0.7, 100.0, now)
    lo = _fact("lo", "beta", 0.75, 0.0, now)
    off = rank_facts_by_trust([hi, lo], now=now)["ranked"]
    on = rank_facts_by_trust([hi, lo], now=now, use_grounding=True)["ranked"]
    assert off[0]["id"] == "lo"   # base alone: lo (0.75) > hi (0.70)
    assert on[0]["id"] == "hi"    # grounding flips it: hi 0.7*1.1 > lo 0.75*0.5
