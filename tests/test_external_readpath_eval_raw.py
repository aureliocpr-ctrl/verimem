"""eval_raw — the per-probe (hit, top_score) capture that lets a floor be swept
post-hoc. Stubbed memory: no e5, no store — pins the shape and the id-decidable
hit + top-score extraction that the VeriBench floor sweep depends on.
"""
from __future__ import annotations

from benchmark.external_readpath import eval_raw


class _StubMem:
    """Returns canned hits per question; mimics Memory.search -> [{id, score}]."""
    def __init__(self, table):
        self.table = table

    def search(self, q, k=5):
        return self.table.get(q, [])


def test_eval_raw_captures_hit_and_top_score():
    mem = _StubMem({
        "q-own": [{"id": "f0", "score": 0.9}, {"id": "fX", "score": 0.4}],   # own fact top
        "q-miss": [{"id": "fY", "score": 0.7}],                              # own fact absent
        "q-unans": [{"id": "fZ", "score": 0.55}],
    })
    items = [{"question": "q-own"}, {"question": "q-miss"}]
    fact_ids = ["f0", "f1"]                       # item0's own id f0 present; item1's f1 absent
    ans, unans = eval_raw(mem, items, fact_ids, ["q-unans"], k=5)

    assert ans[0] == {"retrieval_hit": True, "top_score": 0.9, "has_hits": True}
    assert ans[1] == {"retrieval_hit": False, "top_score": 0.7, "has_hits": True}
    assert unans[0] == {"top_score": 0.55, "has_hits": True}


def test_eval_raw_blocked_ingest_is_a_no_hit_zero_score():
    mem = _StubMem({})
    ans, unans = eval_raw(mem, [{"question": "q"}], [None], [], k=5)
    assert ans[0] == {"retrieval_hit": False, "top_score": 0.0, "has_hits": False}


def test_eval_raw_empty_search_is_zero_score():
    mem = _StubMem({})                            # every search returns []
    ans, unans = eval_raw(mem, [{"question": "q"}], ["f0"], ["u"], k=5)
    assert ans[0]["has_hits"] is False and ans[0]["top_score"] == 0.0
    assert unans[0]["has_hits"] is False and unans[0]["top_score"] == 0.0
