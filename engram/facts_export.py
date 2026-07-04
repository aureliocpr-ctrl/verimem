"""Batch portable export of facts (semantic memory backup).

FORGIA pezzo #230 — Wave 29.
"""
from __future__ import annotations

from typing import Any

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
        rows.append({
            "id": getattr(f, "id", ""),
            "proposition": getattr(f, "proposition", ""),
            "topic": getattr(f, "topic", ""),
            "confidence": float(getattr(f, "confidence", 0.0)),
            "created_at": float(getattr(f, "created_at", 0.0)),
            "source_episodes": list(
                getattr(f, "source_episodes", []) or []
            ),
        })
    return {
        "schema_version": _SCHEMA_VERSION,
        "n_total": len(rows),
        "facts": rows,
    }


__all__ = ["export_all_facts"]
