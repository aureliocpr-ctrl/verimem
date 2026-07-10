"""Aggregation primitive — Memory.count (surface map, retrieval-vs-set-algebra).

F1 sweep 2026-07-10: "how many times did I discuss X?" via recall(k=5) sees
5/12 (undercount 58%) because recall is top-k similarity, not a set operation.
count() is the honest primitive: it SCANS (search_facts / list_facts / total),
so it sees the whole matching set, not the top-k. This does not make recall
count — it gives the caller (and, later, an intent router) the right tool.
"""
from __future__ import annotations

from engram.client import Memory

M = 12  # ground-truth Helios mentions


def _mem(tmp_path):
    mem = Memory(tmp_path / "m.db")
    for i in range(M):
        mem.add(f"On day {i} the team reviewed Project Helios progress and "
                f"planned the next milestone.", topic="work/helios")
    for i in range(8):
        mem.add(f"Note {i}: lunch plans and the weather in Lisbon today.",
                topic="misc")
    return mem


def test_count_by_topic_is_exact(tmp_path):
    assert _mem(tmp_path).count(topic="work/helios") == M


def test_count_by_query_sees_whole_set_not_topk(tmp_path):
    mem = _mem(tmp_path)
    # recall top-k undercounts; count scans and sees all M
    assert mem.count(query="Helios") == M
    assert len(mem.search("how many times Project Helios", k=5)) <= 5


def test_count_total_corpus(tmp_path):
    assert _mem(tmp_path).count() == M + 8


def test_count_empty_topic_is_zero(tmp_path):
    assert _mem(tmp_path).count(topic="does/not/exist") == 0
