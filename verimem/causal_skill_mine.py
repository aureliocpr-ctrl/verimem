"""R2.2: Mine recurring skill candidates from causal signals.

Aggregate output of causal_extract over many trajectory pairs. If a
rule appears ≥min_evidence times across distinct pairs, propose it as
a skill candidate ready for the consolidation cycle.

The candidate carries:
  - rule (the natural-language proposition)
  - evidence_count
  - avg_confidence (across instances)
  - evidence_pairs (list of {success_id, failure_id})
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def causal_skill_mine(
    signals: list[dict[str, Any]],
    *,
    min_evidence: int = 2,
    top_k: int = 50,
) -> dict[str, Any]:
    """Group signals by rule, keep those with enough recurrences."""
    by_rule: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sig in signals:
        rule = sig.get("rule", "")
        if not rule:
            continue
        by_rule[rule].append(sig)

    candidates: list[dict[str, Any]] = []
    for rule, instances in by_rule.items():
        if len(instances) < min_evidence:
            continue
        avg_conf = sum(s.get("confidence", 0.0) for s in instances) / len(instances)
        candidates.append({
            "rule": rule,
            "evidence_count": len(instances),
            "avg_confidence": avg_conf,
            "evidence_pairs": [
                {
                    "success_id": s.get("evidence", {}).get("success_id"),
                    "failure_id": s.get("evidence", {}).get("failure_id"),
                }
                for s in instances
            ],
        })

    # Sort by evidence_count desc, then avg_confidence desc
    candidates.sort(
        key=lambda c: (-c["evidence_count"], -c["avg_confidence"])
    )

    return {
        "candidates": candidates[:top_k],
        "n_total_signals": len(signals),
        "n_candidates": len(candidates),
    }


__all__ = ["causal_skill_mine"]
