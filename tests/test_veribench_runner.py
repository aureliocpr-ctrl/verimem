"""VeriBench runner (#11) — Verimem-wiring + scorecard, hermetic (fake store)."""
from __future__ import annotations

from benchmark.veribench.axes import ProbeItem
from benchmark.veribench.runner import make_verimem_answer_fn, run_bench


class FakeStore:
    """Minimal ``search(query, k) -> [hit]`` stand-in: a store whose floor
    returns nothing for queries it can't support (the abstention signal)."""

    def __init__(self, index):
        # index: query -> (text, score)  (absent query = nothing above the floor)
        self.index = index

    def search(self, query, k=1, **_):
        hit = self.index.get(query)
        return [{"text": hit[0], "score": hit[1]}] if hit else []


def test_answer_fn_returns_text_or_abstains():
    store = FakeStore({"where is Alice?": ("Alice lives in Berlin", 0.82)})
    ans = make_verimem_answer_fn(store)
    assert ans("where is Alice?") == "Alice lives in Berlin"
    assert ans("the CEO's blood type?") is None       # nothing above the floor


def test_min_score_forces_abstention_on_weak_hits():
    store = FakeStore({"q": ("a weak, barely-related fact", 0.20)})
    assert make_verimem_answer_fn(store)("q") == "a weak, barely-related fact"
    assert make_verimem_answer_fn(store, min_score=0.5)("q") is None


def test_run_bench_scorecard_on_mixed_items():
    store = FakeStore({
        "where is Alice?": ("Alice lives in Berlin", 0.82),
        "capital of France?": ("Paris is the capital of France", 0.80),
    })
    items = [
        ProbeItem("where is Alice?", "Berlin"),        # answerable -> CORRECT
        ProbeItem("capital of France?", "Paris"),      # answerable -> CORRECT
        ProbeItem("the CEO's blood type?", None),      # unanswerable -> abstains -> CORRECT
    ]
    sc = run_bench(items, make_verimem_answer_fn(store))
    # 2 answerable answered right (CORRECT) + 1 unanswerable abstained (ABSTAIN)
    assert sc["n"] == 3 and sc["correct"] == 2 and sc["abstain"] == 1 and sc["wrong"] == 0
    assert sc["net"]["lambda_5"] == round(2 / 3, 4)    # no wrong -> λ-immune
    assert sc["crossover_lambda"] is None              # never goes net-negative
