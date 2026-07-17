"""R29: Skill drift detection.

Compare each skill's success_rate in recent window vs historical.
Drift = |recent_rate - hist_rate|. Threshold (default 0.3) flags.

Direction: "improving" (recent > hist) or "degrading" (recent < hist).
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any


def detect_skill_drift(
    episodes: list[Any],
    *,
    now: float | None = None,
    recent_window_days: float = 14.0,
    history_window_days: float = 90.0,
    min_uses: int = 5,
    drift_threshold: float = 0.3,
    top_k: int = 50,
) -> dict[str, Any]:
    """Detect skills whose success rate changed significantly."""
    if now is None:
        now = time.time()
    recent_cutoff = now - recent_window_days * 86400.0
    history_cutoff = now - history_window_days * 86400.0

    # Per-skill counters
    hist_uses: dict[str, int] = defaultdict(int)
    hist_succ: dict[str, int] = defaultdict(int)
    recent_uses: dict[str, int] = defaultdict(int)
    recent_succ: dict[str, int] = defaultdict(int)

    for ep in episodes:
        ts = float(getattr(ep, "created_at", 0.0) or 0.0)
        outcome = getattr(ep, "outcome", "")
        skills = getattr(ep, "skills_used", []) or []
        for s in skills:
            if ts >= recent_cutoff:
                recent_uses[s] += 1
                if outcome == "success":
                    recent_succ[s] += 1
            elif ts >= history_cutoff:
                hist_uses[s] += 1
                if outcome == "success":
                    hist_succ[s] += 1

    drifts: list[dict[str, Any]] = []
    all_skills = set(hist_uses) | set(recent_uses)
    for sid in all_skills:
        h_uses = hist_uses.get(sid, 0)
        r_uses = recent_uses.get(sid, 0)
        if h_uses + r_uses < min_uses:
            continue
        # SCAN-68 FIX 2026-06-02 (NONNA): un drift e' misurabile SOLO se
        # entrambe le finestre hanno usi. Con una finestra a 0 usi, il suo
        # success_rate veniva fabbricato a 0.0 (0/0 != 0%) -> falso 'degrading'
        # per skill dormiente o falso 'improving' per skill nuovo senza baseline.
        if h_uses == 0 or r_uses == 0:
            continue
        h_rate = (hist_succ[sid] / h_uses) if h_uses else 0.0
        r_rate = (recent_succ[sid] / r_uses) if r_uses else 0.0
        drift = abs(r_rate - h_rate)
        if drift < drift_threshold:
            continue
        direction = "improving" if r_rate > h_rate else "degrading"
        drifts.append({
            "skill_id": sid,
            "historical_rate": round(h_rate, 3),
            "recent_rate": round(r_rate, 3),
            "drift": round(drift, 3),
            "direction": direction,
            "historical_uses": h_uses,
            "recent_uses": r_uses,
        })

    drifts.sort(key=lambda d: -d["drift"])
    return {
        "drifts": drifts[:top_k],
        "n_episodes_scanned": len(episodes),
    }


__all__ = ["detect_skill_drift"]
