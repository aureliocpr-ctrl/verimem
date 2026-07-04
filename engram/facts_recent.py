"""Last N facts by created_at.

FORGIA pezzo #269 — Wave 68.
"""
from __future__ import annotations

from typing import Any


def facts_recent(
    facts: list[Any],
    *,
    top_k: int = 20,
) -> dict[str, Any]:
    """Return last N facts, newest-first."""
    sorted_facts = sorted(
        facts,
        key=lambda f: -float(getattr(f, "created_at", 0.0) or 0.0),
    )
    records = [
        {
            "id": getattr(f, "id", ""),
            "proposition": (getattr(f, "proposition", "") or "")[:160],
            "topic": getattr(f, "topic", "") or "",
            "confidence": float(getattr(f, "confidence", 0.0) or 0.0),
            "created_at": float(getattr(f, "created_at", 0.0) or 0.0),
        }
        for f in sorted_facts[:top_k]
    ]
    return {"n_total": len(facts), "facts": records}


__all__ = ["facts_recent"]
