"""Audit 2026-06-08 A4: on query-encode budget overrun (cold process / contended
encode daemon) recall() falls back to search_facts(), which did a SINGLE
full-phrase substring LIKE. A normal multi-word query like "memory architecture"
then returned [] even when strongly-relevant facts exist — the caller reads it
as "no memory". Fix: the fallback now TOKENIZES (per-token OR LIKE) so multi-word
queries still match; the default direct substring search is unchanged
(backward-compatible).
"""
from __future__ import annotations

from verimem.semantic import Fact, SemanticMemory


def _sm(tmp_path):
    return SemanticMemory(db_path=tmp_path / "s.db")


def _add(sm, prop, topic="proj/x"):
    sm.store(
        Fact(proposition=prop, topic=topic, status="model_claim", source_episodes=["e1"]),
        embed="defer",
    )


def test_substring_search_misses_nonadjacent_multiword(tmp_path):
    # Documents the gap: default substring search needs the EXACT phrase.
    sm = _sm(tmp_path)
    _add(sm, "the memory subsystem uses a layered architecture")
    assert sm.search_facts("memory architecture") == []


def test_tokenized_search_matches_multiword(tmp_path):
    sm = _sm(tmp_path)
    _add(sm, "the memory subsystem uses a layered architecture")
    hits = sm.search_facts("memory architecture", tokenize=True)
    assert len(hits) >= 1, "tokenized fallback must match facts containing the tokens"


def test_tokenized_search_empty_when_no_token_present(tmp_path):
    sm = _sm(tmp_path)
    _add(sm, "the memory subsystem uses a layered architecture")
    assert sm.search_facts("kubernetes helm", tokenize=True) == []


def test_tokenized_single_token_equivalent_to_substring(tmp_path):
    sm = _sm(tmp_path)
    _add(sm, "the memory subsystem uses a layered architecture")
    assert len(sm.search_facts("architecture", tokenize=True)) == 1
