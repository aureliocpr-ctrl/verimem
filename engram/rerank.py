"""Layer di reranking cross-encoder OPZIONALE per il recall (2026-06-03).

Provato empiricamente (`scripts/bench_rerank.py`, corpus reale): dense e5-base
top-50 -> cross-encoder bge-reranker-v2-m3 alza R@1 0.60->0.80 e MRR 0.71->0.84.

ADDITIVO e isolato: nessun path esistente importa questo modulo finche' non lo
si chiama esplicitamente (``recall_reranked``) o non si abilita ``HIPPO_RERANK``.
``recall()`` NON e' modificato. Fallback A2: se il reranker non e' caricabile o
fallisce, si ritornano gli hit dense invariati (il recall non si rompe MAI).

Wiring (gated, separato): un handler puo' fare
``recall_reranked(sm, q, k) if rerank_enabled() else sm.recall(q, k)``.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from functools import lru_cache
from typing import Any

#: modello reranker di default (override via env). Provato: bge-reranker-v2-m3.
_DEFAULT_RERANKER = os.environ.get("HIPPO_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")


def rerank_enabled() -> bool:
    """True se il reranking e' abilitato via env ``HIPPO_RERANK`` (default OFF)."""
    return os.environ.get("HIPPO_RERANK", "").strip().lower() in ("1", "true", "yes", "on")


@lru_cache(maxsize=2)
def _load_cross_encoder(model_name: str):
    from sentence_transformers import CrossEncoder
    # device CPU di default: il reranker va OOM su GPU piccole (vedi bench_rerank).
    device = os.environ.get("HIPPO_RERANKER_DEVICE", "cpu")
    try:
        # Cache-only: niente round-trip di rete a HF Hub al load (parita' con
        # embedding._load_model, fix 2026-06-04). Fallback CON rete solo al
        # primo download (modello non ancora in cache).
        return CrossEncoder(model_name, trust_remote_code=True, max_length=512,
                            device=device, local_files_only=True)
    except Exception:  # noqa: BLE001 — non in cache -> permetti il download
        return CrossEncoder(model_name, trust_remote_code=True, max_length=512,
                            device=device)


def _default_scorer(pairs: Sequence[tuple[str, str]]) -> list[float]:
    import numpy as np
    ce = _load_cross_encoder(_DEFAULT_RERANKER)
    return [float(x) for x in np.asarray(ce.predict(list(pairs), show_progress_bar=False))]


def _proposition(hit: Any) -> str:
    """Estrae la proposition dall'hit (tupla (Fact, sim, ...) o Fact)."""
    fact = hit[0] if isinstance(hit, tuple) else hit
    return getattr(fact, "proposition", str(fact))


def rerank_hits(
    query: str,
    hits: Sequence[Any],
    top_k: int = 5,
    *,
    scorer: Callable[[Sequence[tuple[str, str]]], list[float]] | None = None,
) -> list[Any]:
    """Riordina ``hits`` (tuple con Fact in posizione 0) per rilevanza
    cross-encoder vs ``query``; ritorna i ``top_k``.

    Fallback A2: scorer assente/eccezione/lunghezza incoerente -> ritorna
    ``hits[:top_k]`` INVARIATI. Il reranker e' best-effort, non rompe mai il recall.
    """
    if not hits:
        return []
    score_fn = scorer or _default_scorer
    pairs = [(query, _proposition(h)) for h in hits]
    try:
        scores = score_fn(pairs)
        if len(scores) != len(hits):
            return list(hits[:top_k])
    except Exception:  # noqa: BLE001 — reranker best-effort
        return list(hits[:top_k])
    order = sorted(range(len(hits)), key=lambda i: -scores[i])
    return [hits[i] for i in order[:top_k]]


def recall_reranked(
    sm: Any,
    query: str,
    k: int = 5,
    *,
    pool: int = 50,
    scorer: Callable | None = None,
    **recall_kwargs: Any,
) -> list[Any]:
    """Recall a 2 stadi (stack provato): retrieve dense top-``pool`` (con gate+v9
    invariati) -> rerank cross-encoder -> top-``k``. ``recall_kwargs`` passati a
    ``sm.recall``. Se il pool e' vuoto, ritorna []."""
    hits = sm.recall(query, k=pool, **recall_kwargs)
    if not hits:
        return []
    return rerank_hits(query, hits, top_k=k, scorer=scorer)
