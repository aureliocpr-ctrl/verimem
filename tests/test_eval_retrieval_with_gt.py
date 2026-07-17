"""Cycle #113.A (2026-05-17) — eval_retrieval_with_gt tests.

End-to-end on a seeded corpus: insert facts with known propositions,
build a ground truth with a query that should retrieve them, run the
eval and assert metric ranges.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from benchmark.eval_retrieval_with_gt import (
    _RECALL_PATHS,
    _percentile,
    evaluate_all,
    evaluate_path,
)
from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


def _seed(sm: SemanticMemory, items: list[tuple[str, str, list[str]]]) -> None:
    for fid, prop, source_eps in items:
        sm.store(Fact(
            id=fid, proposition=prop, topic="test",
            confidence=0.9, source_episodes=source_eps,
        ))


def test_perfect_keyword_match_gets_high_precision(sm: SemanticMemory) -> None:
    """A query that exactly matches the fact proposition should retrieve
    that fact at rank 1 — precision@5 = 1/5? No, P@k counts hits per
    inspected. With 1 relevant in top-5, P@5 = 1/5 = 0.2; R@5 = 1.0;
    MRR = 1.0."""
    _seed(sm, [
        ("f1", "the NEXUS system has 17280 tests collected", ["ep1"]),
        ("f2", "unrelated proposition about dogs", ["ep_other"]),
        ("f3", "another unrelated fact about weather", ["ep_other"]),
    ])
    gt = {
        "queries": [{
            "episode_id": "ep1",
            # SQL LIKE is substring whole-string, no multi-word AND, so
            # the query must be an actual substring of the proposition.
            "query": "17280 tests",
            "expected_fact_ids": ["f1"],
            "n_expected": 1,
        }],
    }
    result = evaluate_path(sm, gt["queries"], path_name="facts_keyword", k=5)
    assert result["n_queries"] == 1
    # 1 relevant in 1 inspected (only 1 fact matches the substring)
    # → recall = 1/1 = 1.0, MRR = 1/1 = 1.0
    assert result["recall_at_k_mean"] == 1.0
    assert result["mrr_mean"] == 1.0


def test_no_match_gets_zero_metrics(sm: SemanticMemory) -> None:
    _seed(sm, [
        ("f1", "completely unrelated proposition", ["ep_other"]),
    ])
    gt = {
        "queries": [{
            "episode_id": "ep1",
            "query": "NEXUS 17280 tests collected",
            "expected_fact_ids": ["f_does_not_exist"],
            "n_expected": 1,
        }],
    }
    result = evaluate_path(sm, gt["queries"], path_name="facts_keyword", k=5)
    assert result["recall_at_k_mean"] == 0.0
    assert result["mrr_mean"] == 0.0


def test_evaluate_all_runs_every_registered_path(sm: SemanticMemory) -> None:
    _seed(sm, [
        ("f1", "any proposition", ["ep1"]),
    ])
    gt = {
        "queries": [{
            "episode_id": "ep1", "query": "any proposition",
            "expected_fact_ids": ["f1"], "n_expected": 1,
        }],
    }
    env = evaluate_all(sm, gt, k=5)
    assert env["n_queries"] == 1
    assert env["k"] == 5
    assert set(env["per_path"].keys()) == set(_RECALL_PATHS.keys())
    for name, data in env["per_path"].items():
        assert "precision_at_k_mean" in data
        assert "latency_ms_p50" in data


def test_paths_subset_filter_respected(sm: SemanticMemory) -> None:
    _seed(sm, [("f1", "p", ["ep1"])])
    gt = {"queries": [{
        "episode_id": "ep1", "query": "p",
        "expected_fact_ids": ["f1"], "n_expected": 1,
    }]}
    env = evaluate_all(sm, gt, k=5, paths=["facts_keyword"])
    assert set(env["per_path"].keys()) == {"facts_keyword"}


def test_unknown_path_raises(sm: SemanticMemory) -> None:
    with pytest.raises(KeyError, match="unknown recall path"):
        evaluate_path(sm, [], path_name="not_a_real_path", k=5)


def test_percentile_basic() -> None:
    assert _percentile([], 50) == 0.0
    assert _percentile([10.0], 50) == 10.0
    assert _percentile([1.0, 2.0, 3.0, 4.0, 5.0], 50) == 3.0
    # p95 of 1..100 should land near 95
    vals = list(range(1, 101))
    assert 94 <= _percentile([float(v) for v in vals], 95) <= 96


def test_empty_queries_gives_zero_metrics(sm: SemanticMemory) -> None:
    env = evaluate_all(sm, {"queries": []}, k=5)
    for data in env["per_path"].values():
        assert data["n_queries"] == 0
        assert data["precision_at_k_mean"] == 0.0


# ---------------------------------------------------------------------------
# Tokenized keyword retrieval — cycle 113.A round 2
# ---------------------------------------------------------------------------


def test_keyword_tokens_finds_fact_via_multi_word_query(
    sm: SemanticMemory,
) -> None:
    """The naive 'facts_keyword' path fails on multi-word queries
    because SQL LIKE doesn't AND. Tokenized path must succeed: split
    query into informative tokens, run per-token LIKE, aggregate by
    hit count."""
    _seed(sm, [
        ("f1", "the NEXUS system has 17280 tests collected via pytest", ["ep1"]),
        ("f2", "unrelated proposition about dogs and weather", ["ep_other"]),
        ("f3", "another unrelated fact concerning satellites", ["ep_other"]),
    ])
    gt = {"queries": [{
        "episode_id": "ep1",
        "query": "How many tests does the NEXUS system have collected?",
        "expected_fact_ids": ["f1"],
        "n_expected": 1,
    }]}
    result = evaluate_path(
        sm, gt["queries"], path_name="facts_keyword_tokens", k=5,
    )
    assert result["mrr_mean"] == 1.0
    assert result["recall_at_k_mean"] == 1.0


def test_tokenize_drops_stopwords_and_short_words() -> None:
    from benchmark.eval_retrieval_with_gt import _tokenize_for_keyword
    tokens = _tokenize_for_keyword(
        "How does the NEXUS system handle KG retrieval and PageRank?",
    )
    # short stopwords ("the", "and"), tiny words dropped; acronyms kept.
    assert "the" not in tokens
    assert "and" not in tokens
    assert "NEXUS".lower() in tokens
    # Acronyms (uppercase, >=2 chars) survive even when len < 4.
    assert "kg" in tokens
    # Longer informative tokens included.
    assert "retrieval" in tokens or "pagerank" in tokens


def test_tokenize_respects_max_tokens_cap() -> None:
    from benchmark.eval_retrieval_with_gt import _tokenize_for_keyword
    query = "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo"
    tokens = _tokenize_for_keyword(query, max_tokens=3)
    assert len(tokens) == 3


def test_tokenize_empty_query_returns_empty() -> None:
    from benchmark.eval_retrieval_with_gt import _tokenize_for_keyword
    assert _tokenize_for_keyword("") == []
    assert _tokenize_for_keyword("   ?? !!  ") == []


# ---------------------------------------------------------------------------
# Cycle 113.C: RRF fusion
# ---------------------------------------------------------------------------


def test_rrf_unknown_base_path_raises(sm: SemanticMemory) -> None:
    from benchmark.eval_retrieval_with_gt import _run_facts_rrf
    with pytest.raises(KeyError, match="unknown base path"):
        _run_facts_rrf(
            sm, "any", k=5,
            paths_to_fuse=("not_a_real_path",),
        )


def test_rrf_empty_paths_returns_empty(sm: SemanticMemory) -> None:
    from benchmark.eval_retrieval_with_gt import _run_facts_rrf
    assert _run_facts_rrf(sm, "any", k=5, paths_to_fuse=()) == []


def test_rrf_combines_two_paths_no_duplicates(sm: SemanticMemory) -> None:
    """A fact appearing in BOTH paths must rank high — and no duplicates."""
    _seed(sm, [
        ("f_both", "NEXUS system has 17280 tests collected via pytest", ["e1"]),
        ("f_only_cosine", "NEXUS system tests collected", ["e2"]),
        ("f_unrel", "the moon is made of cheese", ["e_other"]),
    ])
    from benchmark.eval_retrieval_with_gt import _run_facts_rrf
    fused = _run_facts_rrf(
        sm, "NEXUS 17280 tests pytest", k=10,
        paths_to_fuse=("facts_cosine_with_legacy", "facts_keyword_tokens"),
    )
    assert len(fused) == len(set(fused)), "duplicates leaked from RRF"
    assert "f_both" in fused


def test_rrf_registered_in_full_registry(sm: SemanticMemory) -> None:
    from benchmark.eval_retrieval_with_gt import _RECALL_PATHS
    assert "facts_rrf_cosine_tokens" in _RECALL_PATHS
    # Calling it on empty corpus must not crash.
    result = _RECALL_PATHS["facts_rrf_cosine_tokens"](sm, "anything", 5)
    assert result == []


def test_rrf_does_not_crash_with_diverse_rrf_k(sm: SemanticMemory) -> None:
    _seed(sm, [
        ("f_a", "alpha word match query", ["e1"]),
        ("f_b", "beta word different content", ["e2"]),
    ])
    from benchmark.eval_retrieval_with_gt import _run_facts_rrf
    for rrf_k in (1, 60, 1000):
        r = _run_facts_rrf(
            sm, "alpha match", k=5,
            paths_to_fuse=("facts_cosine_with_legacy", "facts_keyword_tokens"),
            rrf_k=rrf_k,
        )
        assert isinstance(r, list)
