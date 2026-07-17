"""R48: Top outlier episodes summary — wrapper on anomaly_detection."""
from __future__ import annotations

from typing import Any

from .anomaly_detection import detect_anomalies


def summarize_top_outliers(
    episodes: list[Any],
    *,
    top_k: int = 5,
) -> dict[str, Any]:
    """Quick wrapper that returns the top N outliers with explanations."""
    if not episodes:
        return {"outliers": [], "n_total_scanned": 0}
    raw = detect_anomalies(
        episodes, min_cluster_size=3,
        outcome_majority_threshold=0.6,
    )
    outliers = []
    for a in raw["anomalies"][:top_k]:
        outliers.append({
            "id": a["id"],
            "task_text": a["task_text"],
            "cluster_signature": a["cluster_signature"],
            "explanation": a["reason"],
        })
    return {
        "outliers": outliers,
        "n_total_scanned": raw["n_total_scanned"],
    }


__all__ = ["summarize_top_outliers"]
