"""Batch portable export of facts (semantic memory backup).

FORGIA pezzo #230 — Wave 29.
"""
from __future__ import annotations

from typing import Any

from .fact_contract import fact_payload

_SCHEMA_VERSION = 1


def export_all_facts(
    facts: list[Any],
    *,
    topic: str | None = None,
) -> dict[str, Any]:
    """Return all facts as portable JSON dicts.

    Args:
      - `facts`: iterable of fact-likes.
      - `topic`: optional filter (exact match on `f.topic`).

    Returns: `{schema_version, n_total, facts}`.
    """
    rows: list[dict[str, Any]] = []
    for f in facts:
        if topic is not None and getattr(f, "topic", "") != topic:
            continue
        # 2026-07-30: un export che lascia indietro meta' del fatto e' una
        # perdita di dati silenziosa — chi migra il corpus si porta via le
        # proposizioni e non il verdetto del moat, il tier del giudice, chi
        # l'ha scritto, ne' se e' stato superato. Qui il fatto esce INTERO,
        # tramite il contratto unico (Fact.as_payload).
        rows.append(fact_payload(f))
    return {
        "schema_version": _SCHEMA_VERSION,
        "n_total": len(rows),
        "facts": rows,
    }


__all__ = ["export_all_facts"]
