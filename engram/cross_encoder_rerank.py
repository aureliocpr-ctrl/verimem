"""Cycle 204 (2026-05-23) — cross-encoder rerank primitive.

Closes gap §5.1 of docs/sota/cross-encoder-reranking.md (cycle 203).
Pure function that re-scores a candidate list using an INJECTED
cross-encoder scoring function. Lazy-loads sentence-transformers
CrossEncoder ONLY when no scorer is injected (production code path).

Design choice — injection-only contract
---------------------------------------
For testability + subscription-only safety we DO NOT instantiate
``sentence_transformers.CrossEncoder`` inside this module. The caller
provides a ``scorer: Callable[[list[tuple[str, str]]], list[float]]``
that scores `(query, passage)` pairs. In production wire it to:

    from sentence_transformers import CrossEncoder
    model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-12-v2")
    scorer = lambda pairs: list(model.predict(pairs))
    rerank_candidates(query, candidate_ids, semantic_db,
                       scorer=scorer, top_n=5)

Defensive
---------
* Empty candidate list → ``[]``, no scorer call.
* Scorer raises → fall back to input order with score 0.0 (graceful).
* Missing fact in DB → skipped from the pair list (the input list
  may contain stale ids).
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

#: Default cross-encoder model name (cycle-203 recommendation).
DEFAULT_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"


def _load_propositions(
    db_path: Path, fact_ids: list[str],
) -> dict[str, str]:
    """Fetch propositions for the given ids. Missing rows are
    silently dropped from the result dict."""
    if not fact_ids:
        return {}
    out: dict[str, str] = {}
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            placeholders = ",".join(["?"] * len(fact_ids))
            rows = conn.execute(
                f"SELECT id, proposition FROM facts WHERE id IN ({placeholders})",  # noqa: S608
                tuple(fact_ids),
            ).fetchall()
            for fid, prop in rows:
                out[str(fid)] = str(prop or "")
        finally:
            conn.close()
    except sqlite3.Error:
        return {}
    return out


def rerank_candidates(
    query: str,
    candidate_fact_ids: list[str],
    *,
    semantic_db: Path | str,
    scorer: Callable[[list[tuple[str, str]]], list[float]],
    top_n: int = 5,
) -> list[tuple[str, float]]:
    """Re-score candidates using the injected ``scorer`` callable.

    Args:
        query: the user / agent's recall query.
        candidate_fact_ids: ids returned by the first-stage
            (bi-encoder cosine or fuse_recall) retrieval.
        semantic_db: path to ``semantic.db`` (used to fetch
            propositions for each candidate id).
        scorer: ``(pairs) -> scores`` where pairs is
            ``[(query, proposition), ...]`` and scores is a list
            of floats (higher = more relevant). MUST preserve order.
        top_n: cap on returned list length.

    Returns:
        ``[(fact_id, score), ...]`` sorted by score DESC, length ≤ top_n.
        Empty list when ``candidate_fact_ids`` is empty OR all
        candidates are missing from the DB.
    """
    if not candidate_fact_ids:
        return []

    p = Path(semantic_db)
    if not p.exists():
        return []

    props = _load_propositions(p, candidate_fact_ids)
    if not props:
        return []

    # Preserve caller order; missing ids dropped silently.
    pairs: list[tuple[str, str]] = []
    ordered_ids: list[str] = []
    for fid in candidate_fact_ids:
        if fid in props:
            pairs.append((str(query), props[fid]))
            ordered_ids.append(fid)

    if not pairs:
        return []

    try:
        scores = list(scorer(pairs))
    except Exception:
        # Graceful fallback: preserve input order, all scores 0.0.
        scores = [0.0] * len(pairs)

    # Guard against scorer returning wrong-length output.
    if len(scores) != len(ordered_ids):
        scores = [0.0] * len(ordered_ids)

    # Stable tiebreak on the ORIGINAL input index (not fact_id): equal scores —
    # in particular the all-0.0 scorer-error fallback — must preserve the
    # first-stage (bi-encoder) order, as the docstring promises. (Found by a
    # sister-CLI review 2026-06-09: the previous (-score, fact_id) key scrambled
    # candidates by id whenever the reranker failed.)
    ranked = sorted(
        enumerate(zip(ordered_ids, scores, strict=False)),
        key=lambda it: (-float(it[1][1]), it[0]),
    )
    return [(fid, float(sc)) for _i, (fid, sc) in ranked[: int(top_n)]]


__all__ = ["rerank_candidates", "DEFAULT_MODEL_NAME"]
