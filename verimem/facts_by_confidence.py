"""Filter facts by confidence range.

FORGIA pezzo #263 — Wave 62. Useful: show only high-conf facts,
or find low-conf candidates to verify.
"""
from __future__ import annotations

from typing import Any

from .fact_contract import fact_payload


def facts_by_confidence(
    facts: list[Any],
    *,
    min_conf: float = 0.0,
    max_conf: float = 1.0,
    top_k: int = 50,
) -> dict[str, Any]:
    """Return facts with confidence in [min_conf, max_conf]."""
    filtered = []
    for f in facts:
        c = float(getattr(f, "confidence", 0.0) or 0.0)
        if min_conf <= c <= max_conf:
            filtered.append((f, c))
    filtered.sort(key=lambda x: -x[1])

    # 2026-07-30: ordinare per confidenza senza mostrare il verdetto lasciava
    # credere che la confidenza fosse una misura di verifica. Non lo e': il
    # moat non la scrive. Il contratto unico porta entrambi, cosi' chi legge
    # vede quale delle due sta guardando.
    records = [
        {**fact_payload(f),
         "proposition": (getattr(f, "proposition", "") or "")[:160],
         "confidence": float(c)}
        for f, c in filtered[:top_k]
    ]

    return {
        "n_total": len(filtered),
        "min_conf": min_conf,
        "max_conf": max_conf,
        "facts": records,
    }


__all__ = ["facts_by_confidence"]
