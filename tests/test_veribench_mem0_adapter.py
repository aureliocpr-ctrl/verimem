"""mem0 adapter — the pure floor-application logic (no mem0 instance needed).

The head-to-head run is integration (needs mem0+chroma+e5); here we pin the only
non-trivial pure logic: applying an abstention floor to cached raw rows, and the
availability guard.
"""
from __future__ import annotations

from benchmark.veribench.mem0_adapter import mem0_available, rows_at_floor
from benchmark.veribench.real_axis import outcomes_for_system
from benchmark.veribench.scoring import Outcome


_ANS = [{"retrieval_hit": True, "top_score": 0.82, "has_hits": True},   # relevant, high
        {"retrieval_hit": True, "top_score": 0.70, "has_hits": True}]   # relevant, mid
_UNANS = [{"top_score": 0.66, "has_hits": True},                        # neighbour
          {"top_score": 0.00, "has_hits": False}]                       # nothing


def test_floor_zero_is_mem0_as_shipped_never_abstains_on_a_hit():
    ans, unans = rows_at_floor(_ANS, _UNANS, floor=0.0)
    assert [r["abstained"] for r in ans] == [False, False]        # both commit
    # the neighbour on an unanswerable probe is committed (fabrication); the
    # genuinely-empty result is the only abstention
    assert [r["abstained"] for r in unans] == [False, True]


def test_a_floor_makes_mem0_abstain_on_low_score_neighbours():
    ans, unans = rows_at_floor(_ANS, _UNANS, floor=0.75)
    assert [r["abstained"] for r in ans] == [False, True]         # 0.70 now abstains
    assert [r["abstained"] for r in unans] == [True, True]        # 0.66 neighbour abstains


def test_outcome_mapping_of_mem0_as_shipped_penalises_fabrication():
    ans, unans = rows_at_floor(_ANS, _UNANS, floor=0.0)
    outs = outcomes_for_system(ans, unans)
    # 2 answerable hits -> CORRECT; unanswerable: neighbour=WRONG, empty=ABSTAIN
    assert outs == [Outcome.CORRECT, Outcome.CORRECT, Outcome.WRONG, Outcome.ABSTAIN]


def test_availability_guard_is_boolean():
    assert isinstance(mem0_available(), bool)
