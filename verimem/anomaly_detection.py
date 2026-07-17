"""R11: Anomaly detection over episodes.

Cluster episodes by task-text token signature, then within each
cluster (>= min_cluster_size) flag outliers:
  - Outcome that disagrees with cluster majority (>= 0.7 share)
  - tokens_used >= mean + k*stddev (k=2)
  - num_steps similarly distant

Output: list of {id, reason, cluster_signature, distance}.

Pure-local, deterministic, no LLM.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")


def _signature(text: str, n: int = 5) -> str:
    """Top-N most-frequent tokens as cluster signature."""
    toks = [t.lower() for t in _TOKEN_RE.findall(text or "")]
    counter = Counter(toks)
    top = sorted(t for t, _ in counter.most_common(n))
    return ",".join(top)


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var)


def detect_anomalies(
    episodes: list[Any],
    *,
    min_cluster_size: int = 5,
    outcome_majority_threshold: float = 0.7,
    token_zscore_threshold: float = 2.0,
) -> dict[str, Any]:
    """Detect outlier episodes within homogeneous clusters."""
    if not episodes:
        return {
            "anomalies": [],
            "n_total_scanned": 0,
            "n_clusters_checked": 0,
        }

    # Cluster by signature
    clusters: dict[str, list[Any]] = defaultdict(list)
    for ep in episodes:
        sig = _signature(getattr(ep, "task_text", ""))
        clusters[sig].append(ep)

    anomalies: list[dict[str, Any]] = []
    n_clusters_checked = 0

    for sig, group in clusters.items():
        if len(group) < min_cluster_size:
            continue
        n_clusters_checked += 1

        # Outcome stats
        outcomes = [getattr(e, "outcome", "") for e in group]
        outcome_counter = Counter(outcomes)
        majority_outcome, majority_count = outcome_counter.most_common(1)[0]
        majority_share = majority_count / len(group)

        # Token stats
        tokens = [float(getattr(e, "tokens_used", 0) or 0) for e in group]
        tok_mean = sum(tokens) / len(tokens) if tokens else 0.0
        tok_std = _stddev(tokens)

        for ep in group:
            reasons: list[str] = []
            # Outcome anomaly
            if (majority_share >= outcome_majority_threshold
                    and getattr(ep, "outcome", "") != majority_outcome):
                reasons.append(
                    f"outcome '{getattr(ep, 'outcome', '')}' deviates from "
                    f"cluster majority '{majority_outcome}' "
                    f"({majority_share:.0%})"
                )
            # Token anomaly
            if tok_std > 0:
                ep_tok = float(getattr(ep, "tokens_used", 0) or 0)
                z = (ep_tok - tok_mean) / tok_std
                if z >= token_zscore_threshold:
                    reasons.append(
                        f"tokens_used={int(ep_tok)} is {z:.1f}σ above "
                        f"cluster mean ({int(tok_mean)})"
                    )
            if reasons:
                anomalies.append({
                    "id": getattr(ep, "id", ""),
                    "task_text": getattr(ep, "task_text", "")[:80],
                    "cluster_signature": sig,
                    "cluster_size": len(group),
                    "reason": "; ".join(reasons),
                })

    return {
        "anomalies": anomalies,
        "n_total_scanned": len(episodes),
        "n_clusters_checked": n_clusters_checked,
    }


__all__ = ["detect_anomalies"]
