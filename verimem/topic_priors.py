"""Topic-prefix penalty for off-topic dominance.

Cycle #66 (2026-05-14). Pure numpy function. Used by the embedding daemon
after time decay, before final argsort.

Motivating cases (cycle #63 hard-negative analysis):
    bench v2 MISS #2: query "tls cert chain audit" → top-1 was
        `lessons/agent-orchestration` (an off-topic lesson with overlapping
        keywords "test/audit"), beating the actual `pentest/testfire/*`
        relevant facts.
    bench v2 MISS #3: query "estendere mcp_server.py nuovo tool" → top-1
        was `lessons/hippoagent-deploy` (a sys.path operational rule),
        beating the actual cycle-specific docs.

Decay (cycle #63) could not fix these — they were not stale, they were
keyword-stuffed lesson facts dominating task-style queries.

Strategy: when the query is task-style (no meta-token), penalise facts
whose topic starts with a broadly-matching prefix (default `lessons/*`)
by a small multiplicative factor (default -10%). When the query IS
meta-style ("qual è la lesson", "what is the rule", "definizione"),
no penalty applies — the user is explicitly asking for lessons.

Parameters (all overridable, daemon routes env vars):
    penalty_prefixes:   topic prefixes to consider broadly-matching
                        (default: lessons/)
    meta_query_tokens:  if any of these appears in query (case-insensitive),
                        no penalty applies (default: lesson, lezione,
                        regola, errore, "come funziona", "what is",
                        definizione)
    penalty:            multiplicative factor strength (default 0.10)

Formula:
    is_meta_q = any(tok in query.lower() for tok in meta_query_tokens)
    if is_meta_q: return sims
    factor[i] = (1 - penalty)  if topic[i].startswith(any prefix)
              = 1.0              otherwise
    adj = sims * factor
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np

DEFAULT_PENALTY_PREFIXES: tuple[str, ...] = ("lessons/",)
DEFAULT_META_QUERY_TOKENS: tuple[str, ...] = (
    "lesson", "lezione", "regola", "errore",
    "come funziona", "what is", "definizione",
    "definition",
)
DEFAULT_PENALTY: float = 0.10


def apply_topic_penalty(
    sims: np.ndarray,
    topics: Sequence[str | None],
    *,
    query_text: str,
    penalty_prefixes: Iterable[str] = DEFAULT_PENALTY_PREFIXES,
    meta_query_tokens: Iterable[str] = DEFAULT_META_QUERY_TOKENS,
    penalty: float = DEFAULT_PENALTY,
) -> np.ndarray:
    """Apply a topic-prefix penalty to similarity scores.

    Args:
        sims: 1-D array of similarity scores (cosine, possibly already
              time-decayed by cycle #63).
        topics: per-fact topic strings (None or "" treated as no-topic
                and never penalised).
        query_text: the original user prompt (used for meta-token check).
        penalty_prefixes: prefixes to consider broadly-matching.
        meta_query_tokens: if any appears in `query_text.lower()`,
                           the function is a no-op (lesson facts kept
                           at full score).
        penalty: multiplicative factor in [0, 1). penalty=0 is a no-op.

    Returns:
        np.ndarray same shape and dtype as `sims`, with off-topic-prone
        lesson facts pushed down for task-style queries.
    """
    sims_arr = np.asarray(sims)
    if sims_arr.size == 0:
        return sims_arr.copy()
    if penalty <= 0.0:
        return sims_arr.copy()

    q_lower = (query_text or "").lower()
    prefixes_t = tuple(penalty_prefixes)
    meta_tokens_t = tuple(meta_query_tokens)

    if any(tok in q_lower for tok in meta_tokens_t):
        return sims_arr.copy()

    factor = np.ones_like(sims_arr, dtype=sims_arr.dtype)
    for i, topic in enumerate(topics):
        if not topic:
            continue
        if any(topic.startswith(p) for p in prefixes_t):
            factor[i] = sims_arr.dtype.type(1.0 - penalty)
    return sims_arr * factor


__all__ = [
    "apply_topic_penalty",
    "DEFAULT_PENALTY_PREFIXES",
    "DEFAULT_META_QUERY_TOKENS",
    "DEFAULT_PENALTY",
]
