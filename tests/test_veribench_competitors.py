"""VeriBench competitor adapter (#11) — mem0 on the abstention axis, hermetic.

The load-bearing test is `test_mem0_vs_verimem_abstention_under_net`: same probes,
mem0 fabricates on the unanswerable item (no floor) and loses to Verimem under
NET(λ>1) — the trust gap made numeric.
"""
from __future__ import annotations

from benchmark.veribench.axes import ProbeItem, run_axis
from benchmark.veribench.competitors import make_mem0_answer_fn
from benchmark.veribench.scoring import Outcome, net_score

C, W, A = Outcome.CORRECT, Outcome.WRONG, Outcome.ABSTAIN


class FakeMem0:
    """mem0-shaped store that, like the real one, returns its NEAREST memory for
    any query — even an unrelated one (no abstention floor)."""

    def __init__(self, index):
        self.index = index

    def search(self, query, **_):
        hit = self.index.get(query, ("some unrelated nearest memory", 0.1))
        return {"results": [{"memory": hit[0], "score": hit[1]}]}


def test_mem0_never_abstains_by_default():
    store = FakeMem0({"where is Alice?": ("Alice lives in Berlin", 0.8)})
    ans = make_mem0_answer_fn(store)
    assert ans("where is Alice?") == "Alice lives in Berlin"
    # unanswerable -> mem0 STILL returns its nearest (no floor) -> fabricates
    assert ans("the CEO's blood type?") == "some unrelated nearest memory"


def test_mem0_with_explicit_floor_can_abstain():
    store = FakeMem0({})  # every query -> weak 0.1 nearest
    assert make_mem0_answer_fn(store, min_score=0.5)("q") is None


def test_mem0_vs_verimem_abstention_under_net():
    items = [
        ProbeItem("where is Alice?", "Berlin"),     # answerable
        ProbeItem("the CEO's blood type?", None),   # UNANSWERABLE (honest = abstain)
    ]
    known = {"where is Alice?": ("Alice lives in Berlin", 0.8)}
    mem0 = make_mem0_answer_fn(FakeMem0(known))     # answers both

    def verimem(q):                                  # abstains when unsupported
        return "Alice lives in Berlin" if q in known else None

    o_mem0 = run_axis(items, mem0)      # [C, W] — fabricates on the unanswerable
    o_vm = run_axis(items, verimem)     # [C, A] — abstains honestly
    assert o_mem0 == [C, W] and o_vm == [C, A]
    # where a wrong answer costs more than silence, trust wins — numerically
    assert net_score(o_vm, 5.0) > net_score(o_mem0, 5.0)
    assert net_score(o_mem0, 5.0) < 0 <= net_score(o_vm, 5.0)
