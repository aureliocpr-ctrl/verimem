"""R45: Composite priority score combining confidence + freshness + corroboration.

Priority = 0.5 * confidence + 0.3 * freshness + 0.2 * corroboration
"""
from __future__ import annotations

import re
import time
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")
_DAY = 86400.0


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _freshness(fact: Any, now: float, half_life_days: float) -> float:
    created = float(getattr(fact, "created_at", now))
    age_days = max(0.0, (now - created) / _DAY)
    return 0.5 ** (age_days / half_life_days) if half_life_days > 0 else 1.0


def _corroboration(fact: Any, others: list[Any], threshold: float) -> float:
    ftok = _tokens(getattr(fact, "proposition", ""))
    if not ftok:
        return 0.0
    fid = getattr(fact, "id", "")
    matches = 0
    for o in others:
        if getattr(o, "id", "") == fid:
            continue
        if _jaccard(ftok, _tokens(getattr(o, "proposition", ""))) >= threshold:
            matches += 1
    return min(1.0, matches * 0.2)


def rank_facts_by_priority(
    facts: list[Any],
    *,
    now: float | None = None,
    half_life_days: float = 180.0,
    corr_threshold: float = 0.5,
    top_k: int = 50,
) -> dict[str, Any]:
    """Rank facts by composite priority."""
    if now is None:
        now = time.time()

    ranked: list[dict[str, Any]] = []
    for f in facts:
        conf = float(getattr(f, "confidence", 0.0) or 0.0)
        fresh = _freshness(f, now, half_life_days)
        corr = _corroboration(f, facts, corr_threshold)
        priority = 0.5 * conf + 0.3 * fresh + 0.2 * corr
        ranked.append({
            "id": getattr(f, "id", ""),
            "topic": getattr(f, "topic", ""),
            "proposition": getattr(f, "proposition", "")[:80],
            "priority": round(min(1.0, priority), 4),
            "components": {
                "confidence": round(conf, 3),
                "freshness": round(fresh, 3),
                "corroboration": round(corr, 3),
            },
        })
    ranked.sort(key=lambda r: -r["priority"])
    return {
        "ranked": ranked[:top_k],
        "n_facts_scanned": len(facts),
    }


__all__ = ["rank_facts_by_priority"]
