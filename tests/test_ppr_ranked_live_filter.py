"""hippo_ppr_retrieve must drop superseded/orphaned facts from BOTH the legacy
`facts` union AND the `facts_ranked` ranked list (bug-hunt #4, HIGH).

HIGH-2 (correctness-hunt #3) added a filter_live_ids pass over result["facts"]
because entity_facts links aren't pruned on supersede. But #206 then added
`facts_ranked` — the PRIMARY retrieval signal — and the live filter was NOT
extended to it, so a superseded/orphaned fact stayed in facts_ranked and
leaked back into callers (e.g. the ranked retrieval a downstream recall uses).

This pins the fix as a pure helper _apply_live_filter(result, live_filter)
applied to both lists, order-preserving.

RED marker: pre-fix _apply_live_filter does not exist (ImportError); the
handler only filtered result["facts"].
"""
from __future__ import annotations

from verimem.mcp_server import _apply_live_filter


def _no_dead(ids):
    """A filter_live_ids stand-in: drops the id 'dead', keeps order."""
    return [i for i in ids if i != "dead"]


def test_filters_dead_from_both_lists():
    result = {
        "facts": ["a", "dead", "b"],
        "facts_ranked": [
            {"fact_id": "a", "score": 3.0, "n_entities": 2},
            {"fact_id": "dead", "score": 9.0, "n_entities": 5},
            {"fact_id": "b", "score": 1.0, "n_entities": 1},
        ],
    }
    out = _apply_live_filter(result, _no_dead)
    assert out["facts"] == ["a", "b"]
    assert [r["fact_id"] for r in out["facts_ranked"]] == ["a", "b"], (
        "facts_ranked must drop the superseded fact AND preserve rank order"
    )


def test_none_filter_is_noop():
    result = {"facts": ["a"], "facts_ranked": [{"fact_id": "a", "score": 1.0}]}
    out = _apply_live_filter(result, None)
    assert out["facts"] == ["a"]
    assert [r["fact_id"] for r in out["facts_ranked"]] == ["a"]


def test_empty_lists_no_crash():
    result = {"facts": [], "facts_ranked": []}
    out = _apply_live_filter(result, lambda ids: ids)
    assert out["facts"] == []
    assert out["facts_ranked"] == []


def test_missing_keys_no_crash():
    # an empty-KG early return may not carry both keys
    out = _apply_live_filter({"ranked": []}, _no_dead)
    assert out == {"ranked": []}
