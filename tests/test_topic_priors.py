"""Cycle #66 — Topic-prefix penalty (leva 2) for off-topic dominance.

Cycle #63 hard-negative analysis identified 2 prompts where the top-1
came from `lessons/*` topic — facts that are long, keyword-rich, and
match too broadly. The decay (cycle #63) did NOT fix these because
they were NOT stale — they were off-topic in a way decay cannot
distinguish.

Strategy: apply a small multiplicative penalty (default -10%) to
facts whose topic starts with a "broadly-matching" prefix (default
`lessons/*`), UNLESS the query itself contains meta-tokens that
suggest the user IS asking about a lesson / how-it-works / definition.

This is asymmetric on purpose: task-style queries get pushed toward
domain-specific facts; meta-style queries see the lesson facts at full
strength.

The function is pure (numpy). Tests cover both the math and the
motivating MISS #2 case from bench v2.
"""
from __future__ import annotations

import numpy as np

from verimem.topic_priors import apply_topic_penalty


def test_penalty_applied_to_lessons_on_task_query():
    """Task-style query + lesson topic → fact gets penalised."""
    sims = np.array([0.80, 0.70], dtype=np.float32)
    topics = ["lessons/agent-orchestration", "pentest/testfire/findings"]
    adj = apply_topic_penalty(
        sims, topics,
        query_text="come strutturo un test di sicurezza tls cert chain audit",
        penalty=0.10,
    )
    # First (lesson) penalised, second (pentest) untouched
    np.testing.assert_allclose(adj, [0.80 * 0.90, 0.70], rtol=1e-5)


def test_no_penalty_on_meta_query():
    """If query contains a meta-token, lesson facts keep full score."""
    sims = np.array([0.80, 0.70], dtype=np.float32)
    topics = ["lessons/agent-orchestration", "pentest/testfire/findings"]
    adj = apply_topic_penalty(
        sims, topics,
        query_text="qual è la lesson sul TDD strict?",
        penalty=0.10,
    )
    np.testing.assert_allclose(adj, sims, rtol=1e-6)


def test_no_penalty_on_non_lesson_topics():
    """Facts whose topic does not match the prefix list are never penalised."""
    sims = np.array([0.80, 0.70], dtype=np.float32)
    topics = ["project/engram/cycle-51", "decisions/architecture"]
    adj = apply_topic_penalty(
        sims, topics,
        query_text="qualunque query",
        penalty=0.10,
    )
    np.testing.assert_allclose(adj, sims, rtol=1e-6)


def test_zero_penalty_is_noop():
    """penalty=0 returns input unchanged regardless of topics/query."""
    sims = np.array([0.8, 0.5], dtype=np.float32)
    topics = ["lessons/foo", "lessons/bar"]
    adj = apply_topic_penalty(
        sims, topics, query_text="task query", penalty=0.0,
    )
    np.testing.assert_allclose(adj, sims, rtol=1e-6)


def test_empty_input_returns_empty():
    sims = np.array([], dtype=np.float32)
    topics: list[str] = []
    adj = apply_topic_penalty(
        sims, topics, query_text="any", penalty=0.10,
    )
    assert adj.shape == (0,)


def test_motivating_case_miss_2_tls_cert():
    """The MISS #2 of bench v2 reproduced with real sims + topics.

    From cycle #61 bench v2:
      query  = "come strutturo un test di sicurezza tls cert chain audit"
      top-1  = lessons/agent-orchestration (sim 0.5971) — WRONG
      top-2  = test/clean-final            (sim 0.5196)
      relevant = pentest/testfire/findings (sim ~0.55 in candidates pool)

    With penalty=0.10 on lessons/* AND a synthetic relevant fact at
    sim 0.55 we verify the ranking flips correctly.
    """
    sims = np.array([0.5971, 0.5196, 0.55], dtype=np.float32)
    topics = [
        "lessons/agent-orchestration",
        "test/clean-final",
        "pentest/testfire/findings",
    ]
    adj = apply_topic_penalty(
        sims, topics,
        query_text="come strutturo un test di sicurezza tls cert chain audit",
        penalty=0.10,
    )
    # adj[0] = 0.5971 * 0.90 = 0.5374
    # adj[1] = 0.5196 (unchanged)
    # adj[2] = 0.55 (unchanged, relevant)
    # New order: 2, 0, 1  →  pentest comes first
    order = np.argsort(-adj)
    assert order[0] == 2, (
        f"pentest/testfire should be top-1 after penalty, got order={order}"
    )


def test_preserves_order_within_lesson_group():
    """Two lesson facts keep their relative order after equal penalty."""
    sims = np.array([0.80, 0.60], dtype=np.float32)
    topics = ["lessons/a", "lessons/b"]
    adj = apply_topic_penalty(
        sims, topics, query_text="task query", penalty=0.10,
    )
    assert adj[0] > adj[1]  # ordering preserved


def test_handles_none_or_empty_topic_gracefully():
    """Facts with topic=None or '' must not crash and not get penalty."""
    sims = np.array([0.8, 0.7, 0.6], dtype=np.float32)
    topics: list[str | None] = [None, "", "lessons/foo"]
    adj = apply_topic_penalty(
        sims, topics, query_text="task query", penalty=0.10,
    )
    # First two untouched, third penalised
    np.testing.assert_allclose(
        adj, [0.8, 0.7, 0.6 * 0.90], rtol=1e-5,
    )
