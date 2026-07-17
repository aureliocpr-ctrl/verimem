"""R7: Time-decay on facts confidence.

Memory should age. A CVE noted 6 months ago is likely patched. A
config decision from 2 years ago may have been superseded.

Exponential decay with parametrizable half-life (default 90 days).
After 1 half-life → confidence halved.
After 2 half-lives → quartered.
etc.

Levels:
  - fresh  : age < 0.5 * half-life
  - stale  : 0.5 * half-life <= age < 3 * half-life
  - expired: age >= 3 * half-life
"""
from __future__ import annotations

import time
from typing import Any

_DAY_SEC = 86400.0


def decay_confidence(
    fact: Any,
    *,
    now: float | None = None,
    half_life_days: float = 90.0,
) -> float:
    """Return decayed confidence based on age."""
    if now is None:
        now = time.time()
    created = float(getattr(fact, "created_at", now))
    age_days = max(0.0, (now - created) / _DAY_SEC)
    original = float(getattr(fact, "confidence", 0.0) or 0.0)
    # exp decay: c(t) = c0 * (0.5) ** (t / half-life)
    decay_factor = 0.5 ** (age_days / half_life_days) if half_life_days > 0 else 1.0
    return round(original * decay_factor, 4)


def assess_freshness(
    fact: Any,
    *,
    now: float | None = None,
    half_life_days: float = 90.0,
) -> dict[str, Any]:
    """Return {status, decayed_confidence, age_days, original_confidence}."""
    if now is None:
        now = time.time()
    created = float(getattr(fact, "created_at", now))
    age_days = max(0.0, (now - created) / _DAY_SEC)
    original = float(getattr(fact, "confidence", 0.0) or 0.0)
    decayed = decay_confidence(fact, now=now, half_life_days=half_life_days)

    if age_days < 0.5 * half_life_days:
        status = "fresh"
    elif age_days < 3 * half_life_days:
        status = "stale"
    else:
        status = "expired"

    return {
        "status": status,
        "decayed_confidence": decayed,
        "original_confidence": original,
        "age_days": round(age_days, 1),
        "half_life_days": half_life_days,
    }


def find_stale_facts(
    facts: list[Any],
    *,
    now: float | None = None,
    threshold_days: float = 90.0,
    top_k: int = 100,
) -> dict[str, Any]:
    """List facts older than threshold_days, sorted oldest first."""
    if now is None:
        now = time.time()
    stale: list[dict[str, Any]] = []
    for f in facts:
        created = float(getattr(f, "created_at", now))
        age = (now - created) / _DAY_SEC
        if age >= threshold_days:
            stale.append({
                "id": getattr(f, "id", ""),
                "topic": getattr(f, "topic", ""),
                "proposition": getattr(f, "proposition", "")[:120],
                "age_days": round(age, 1),
                "original_confidence": float(getattr(f, "confidence", 0.0) or 0.0),
                "decayed_confidence": decay_confidence(
                    f, now=now, half_life_days=threshold_days,
                ),
            })
    stale.sort(key=lambda x: -x["age_days"])
    return {
        "stale_facts": stale[:top_k],
        "n_total_scanned": len(facts),
        "n_stale": len(stale),
        "threshold_days": threshold_days,
    }


__all__ = [
    "decay_confidence",
    "assess_freshness",
    "find_stale_facts",
]
