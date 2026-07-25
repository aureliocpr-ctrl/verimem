"""Deep-then-compress: recuperare in profondità e consegnare k candidati DIVERSI.

Measured 2026-07-25 on the five LoCoMo multi-hop questions we get wrong, with
the prediction stated before the result:

    k=30 (today's default)      1/5
    k=100 raw                   2/5
    k=100 -> MMR 30             3/5   <- same number of chunks as the first

Both halves are load-bearing, and the individual cases show why. Depth alone
brings in evidence that k=30 never sees (one gold element sat at rank 77) but
hands the model more to aggregate, and it aggregates less: on 9:58 the raw
k=100 arm fails where 30 diversified chunks succeed. Compression alone, on a
shallow pool, has nothing to work with — an earlier attempt at deduplicating a
30-chunk context cut it to 2 and made every answer worse.

MMR (Carbonell & Goldstein 1998): pick the most relevant item, then repeatedly
pick the item maximising ``lam * relevance - (1 - lam) * max_similarity_to_
already_picked``. ``lam=1`` is exactly pure relevance, i.e. current behaviour.

OFF by default, and not out of ritual caution: on the product's real recall the
top-30 redundancy is 7.0%, against 77.5% on the conversational bench (whose
windows overlap by construction). On a corpus of distinct propositions there is
nothing to compress and this would be pure overhead. It belongs where the
redundancy is — conversational corpora, documents chunked with overlap — and
the default stays put until a full-bench measurement says otherwise.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

__all__ = ["mmr_select"]


def mmr_select(
    items: Sequence[tuple[Any, np.ndarray]],
    query_vec: np.ndarray,
    *,
    n: int,
    lam: float = 0.7,
) -> list[tuple[Any, np.ndarray]]:
    """Select ``n`` items balancing relevance to ``query_vec`` against
    redundancy among the picks.

    ``items`` are ``(payload, vector)`` pairs; the payload is returned
    untouched, so callers can pass whatever they are ranking. Vectors need not
    be normalised. Deterministic: ties resolve by the original order, because a
    ranking that shifts between identical calls cannot be A/B tested.

    Degenerate inputs answer instead of raising: an empty pool gives an empty
    list, ``n`` beyond the pool gives the pool, and a zero vector scores 0
    rather than producing NaN — a fact whose embedding never landed must not
    poison the ranking of the ones that did.
    """
    if not items or n <= 0:
        return []
    n = min(int(n), len(items))

    q_raw = np.asarray(query_vec, dtype=np.float32).ravel()
    dim = int(q_raw.shape[0])
    # Dimension drift is a real state in a long-lived store (a re-embedded
    # corpus, a model swap). Ranking those items against a query they cannot
    # be compared to would invent a similarity; refusing to rank at all would
    # lose them. They keep their original order at the TAIL, after everything
    # that could actually be scored.
    usable = [(i, it) for i, it in enumerate(items)
              if np.asarray(it[1], dtype=np.float32).ravel().shape[0] == dim]
    odd = [it for i, it in enumerate(items) if not any(i == j for j, _ in usable)]
    if not usable:
        return list(items[:n])
    items_u = [it for _i, it in usable]

    mat = np.asarray([np.asarray(v, dtype=np.float32).ravel()
                      for _p, v in items_u], dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    mat = mat / norms

    q = q_raw / (float(np.linalg.norm(q_raw)) or 1.0)

    rel = mat @ q
    rel = np.where(np.isfinite(rel), rel, -np.inf)

    picked: list[int] = [int(np.argmax(rel))]
    while len(picked) < n:
        sub = mat[picked]
        # similarity of every candidate to its NEAREST already-picked item
        red = (mat @ sub.T).max(axis=1)
        score = lam * rel - (1.0 - lam) * red
        score[picked] = -np.inf
        nxt = int(np.argmax(score))
        if not np.isfinite(score[nxt]):
            break
        picked.append(nxt)
    out = [items_u[i] for i in picked]
    if len(out) < n and odd:
        out.extend(odd[: n - len(out)])
    return out
