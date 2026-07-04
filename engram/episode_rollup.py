"""R13: Episode rollup — compress old episodes into family summaries.

When the episode log grows beyond useful size, take episodes older
than threshold and cluster by task signature. Each cluster gets
collapsed into one summary record:

    "we ran X 12 times between 2024-01 and 2024-03,
     10 success (83%), ~250 avg tokens"

The original episodes can then be archived or pruned. The summary
contains enough information for analytics and future recall.

Pure-local, deterministic.
"""
from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")


def _signature(text: str, n: int = 5) -> str:
    toks = [t.lower() for t in _TOKEN_RE.findall(text or "")]
    counter = Counter(toks)
    top = sorted(t for t, _ in counter.most_common(n))
    return ",".join(top)


def rollup_old_episodes(
    episodes: list[Any],
    *,
    now: float | None = None,
    older_than_days: float = 90.0,
    min_cluster_size: int = 3,
) -> dict[str, Any]:
    """Bucket old episodes by signature, produce 1 rollup per cluster."""
    if now is None:
        now = time.time()
    cutoff = now - older_than_days * 86400.0
    old = [
        e for e in episodes
        if float(getattr(e, "created_at", 0.0) or 0.0) < cutoff
    ]
    if not old:
        return {
            "rollups": [],
            "n_episodes_rolled": 0,
            "n_clusters": 0,
        }

    clusters: dict[str, list[Any]] = defaultdict(list)
    for e in old:
        sig = _signature(getattr(e, "task_text", ""))
        clusters[sig].append(e)

    rollups: list[dict[str, Any]] = []
    n_rolled = 0
    for sig, group in clusters.items():
        if len(group) < min_cluster_size:
            continue
        n_succ = sum(1 for e in group if getattr(e, "outcome", "") == "success")
        n_fail = sum(1 for e in group if getattr(e, "outcome", "") == "failure")
        tokens = [int(getattr(e, "tokens_used", 0) or 0) for e in group]
        avg_tok = sum(tokens) / len(tokens) if tokens else 0.0
        timestamps = [
            float(getattr(e, "created_at", 0.0) or 0.0) for e in group
        ]
        time_span_days = (max(timestamps) - min(timestamps)) / 86400.0
        sample_tasks = [
            getattr(e, "task_text", "")[:80] for e in group[:3]
        ]
        summary = (
            f"Cluster '{sig}': {len(group)} episodes "
            f"({n_succ}/{n_succ + n_fail} success), "
            f"~{int(avg_tok)} avg tokens, "
            f"span={time_span_days:.0f} days"
        )
        rollups.append({
            "cluster_signature": sig,
            "n_episodes": len(group),
            "n_success": n_succ,
            "n_failure": n_fail,
            "success_rate": (n_succ / len(group)) if group else 0.0,
            "avg_tokens": round(avg_tok, 1),
            "time_span_days": round(time_span_days, 1),
            "sample_tasks": sample_tasks,
            "episode_ids": [getattr(e, "id", "") for e in group],
            "summary": summary,
        })
        n_rolled += len(group)

    rollups.sort(key=lambda r: -r["n_episodes"])

    return {
        "rollups": rollups,
        "n_episodes_rolled": n_rolled,
        "n_clusters": len(rollups),
    }


__all__ = ["rollup_old_episodes"]
