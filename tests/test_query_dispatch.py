"""Memory.ask — end-to-end intent routing (surface-map thesis, read-path twin).

Proves the thesis executable: a natural-language COUNT query returns the RIGHT
number (full-set scan), where plain search (top-k) undercounts; FIND stays
ordinary recall. This is the read-path analogue of gate_router.
"""
from __future__ import annotations

from engram.client import Memory

M = 12


def _mem(tmp_path):
    mem = Memory(tmp_path / "m.db")
    for i in range(M):
        mem.add(f"On day {i} the team reviewed Project Helios progress and "
                f"planned the next milestone.", topic="work/helios")
    for i in range(8):
        mem.add(f"Note {i}: lunch plans and the weather in Lisbon today.",
                topic="misc")
    return mem


def test_count_query_routes_to_full_scan(tmp_path):
    mem = _mem(tmp_path)
    r = mem.ask("how many times did I discuss Project Helios?")
    assert r["intent"] == "count"
    assert r["count"] == M, (
        "a counting query must scan the whole set, not top-k recall")


def test_count_query_beats_plain_search(tmp_path):
    mem = _mem(tmp_path)
    counted = mem.ask("how many times did we mention Helios?")["count"]
    top5 = len(mem.search("Helios", k=5))
    assert counted == M and top5 <= 5 and counted > top5


def test_italian_count_query(tmp_path):
    mem = _mem(tmp_path)
    r = mem.ask("quante volte ho parlato di Helios?")
    assert r["intent"] == "count" and r["count"] == M


def test_find_query_is_ordinary_recall(tmp_path):
    mem = _mem(tmp_path)
    r = mem.ask("where did we review Project Helios?")
    assert r["intent"] == "find"
    assert isinstance(r["results"], list) and r["results"]


def test_exclude_executes_set_difference(tmp_path):
    # F1 negation fall: embeddings ignore "not". ask EXCLUDE must scan+remove.
    mem = Memory(tmp_path / "m.db")
    for i in range(3):
        mem.add(f"The tax module computes rate {i}.", topic="mod")
    for i in range(3):
        mem.add(f"The email module sends message {i}.", topic="mod")
    for i in range(3):
        mem.add(f"The user module stores profile {i}.", topic="mod")
    r = mem.ask("show modules not about tax")
    assert r["intent"] == "exclude"
    texts = " ".join(x["text"].lower() for x in r["results"])
    assert "tax" not in texts, "excluded term must be removed from the set"
    assert len(r["results"]) == 6, "the other 6 facts survive the difference"


def test_list_all_returns_the_set(tmp_path):
    # content_terms is LEXICAL: generic query nouns not in the facts ("notes")
    # over-constrain require_all_tokens. A query naming the entity enumerates
    # the whole set — the point (vs top-k). The extraction limit is declared.
    mem = _mem(tmp_path)
    r = mem.ask("list all Project Helios")
    assert r["intent"] == "list_all"
    assert len(r["results"]) == M
