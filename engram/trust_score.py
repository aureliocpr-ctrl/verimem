"""R14: Composite trust score per fact.

Trust(fact) = base_confidence * age_decay * (1 + corroboration_boost)

- base_confidence: the fact's own declared confidence
- age_decay: exp decay (half-life 180 days, gentler than R7 default)
- corroboration_boost: 0..0.3 based on # of supporting facts with
  high token overlap

Output: 0..1 trust score per fact + components + rationale.
"""
from __future__ import annotations

import re
import time
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")
_DAY_SEC = 86400.0


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _age_decay(fact: Any, now: float, half_life_days: float) -> float:
    created = float(getattr(fact, "created_at", now))
    age_days = max(0.0, (now - created) / _DAY_SEC)
    if half_life_days <= 0:
        return 1.0
    return 0.5 ** (age_days / half_life_days)


def _corroboration(
    fact: Any,
    others: list[Any],
    *,
    sim_threshold: float = 0.4,
    max_boost: float = 0.3,
) -> float:
    """Count facts that overlap significantly with this one."""
    fact_tokens = _tokens(getattr(fact, "proposition", ""))
    if not fact_tokens:
        return 0.0
    target_id = getattr(fact, "id", "")
    matches = 0
    for o in others:
        if getattr(o, "id", "") == target_id:
            continue
        o_tokens = _tokens(getattr(o, "proposition", ""))
        if _jaccard(fact_tokens, o_tokens) >= sim_threshold:
            matches += 1
    # Diminishing returns: 1 match = 0.15, 2 = 0.22, 3+ = 0.30 max
    return min(max_boost, 0.15 * (matches ** 0.5))


def _grounding_factor(fact: Any, use_grounding: bool) -> float:
    """Multiplicative trust factor from the WRITE-time grounding score (source⊢fact,
    AUROC 0.971). Connects the proven write-path moat to read-path trust: a fact whose
    source strongly entailed it is more trustworthy than an ungrounded one. Maps
    grounding 0→0.5 (penalize ungrounded), 50→0.8, 100→1.1 (modest boost). Neutral (1.0)
    when disabled OR the fact has no grounding score (backward-compatible — most facts)."""
    if not use_grounding:
        return 1.0
    g = getattr(fact, "grounding_score", None)
    if g is None:
        return 1.0
    g = max(0.0, min(100.0, float(g)))
    return 0.5 + 0.006 * g


def compute_trust_score(
    fact: Any,
    *,
    now: float | None = None,
    half_life_days: float = 180.0,
    corroborating_facts: list[Any] | None = None,
    use_grounding: bool = False,
) -> dict[str, Any]:
    """Composite trust score for a fact. ``use_grounding`` (opt-in, default off =
    byte-identical legacy) folds in the write-time grounding score as a multiplier."""
    if now is None:
        now = time.time()
    base = float(getattr(fact, "confidence", 0.0) or 0.0)
    age = _age_decay(fact, now=now, half_life_days=half_life_days)
    corr = (_corroboration(fact, corroborating_facts)
            if corroborating_facts else 0.0)
    gf = _grounding_factor(fact, use_grounding)
    raw_trust = base * age * (1.0 + corr) * gf
    trust = round(min(1.0, max(0.0, raw_trust)), 4)
    rationale = (
        f"base={base:.2f}, age_decay={age:.2f}, corr_boost={corr:.2f}"
        + (f", grounding_factor={gf:.2f}" if use_grounding else "")
    )
    return {
        "trust": trust,
        "components": {
            "base_confidence": round(base, 4),
            "age_decay": round(age, 4),
            "corroboration": round(corr, 4),
            "grounding_factor": round(gf, 4),
        },
        "rationale": rationale,
    }


def rank_facts_by_trust(
    facts: list[Any],
    *,
    now: float | None = None,
    half_life_days: float = 180.0,
    top_k: int = 50,
    use_grounding: bool = False,
) -> dict[str, Any]:
    """Rank facts by trust desc. ``use_grounding`` folds write-time grounding into trust."""
    ranked: list[dict[str, Any]] = []
    for f in facts:
        out = compute_trust_score(
            f, now=now, half_life_days=half_life_days,
            corroborating_facts=facts, use_grounding=use_grounding,
        )
        ranked.append({
            "id": getattr(f, "id", ""),
            "topic": getattr(f, "topic", ""),
            "proposition": getattr(f, "proposition", "")[:80],
            "trust": out["trust"],
            "components": out["components"],
        })
    ranked.sort(key=lambda r: -r["trust"])
    return {
        "ranked": ranked[:top_k],
        "n_scanned": len(facts),
    }


__all__ = [
    "compute_trust_score",
    "rank_facts_by_trust",
]
