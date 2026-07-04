"""Cycle 271 (2026-05-23) — Cumulative A4-violation tracker.

Pioneering singolarità #27: query persistent critic/* facts in
HippoAgent (cycle 269 CRITIC-AS-MEMORY foundation), parse verdict
keywords, emit rate dashboard.

Tests paper §9.3 prediction: applying M3-M12 as constraints from
cycle 264+ should reduce A4-violation rate compared to cycle 253-263
baseline.

Output: JSON with per-window violation counts + falsifiability test.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

VERDICT_PATTERNS = {
    "CLAIM_FAILS": [r"claim_fails", r"claim.holds=false", r"production_caller_exists.*false"],
    "CLAIM_HOLDS": [r"claim_holds=?:?\s*true", r"HOLD"],
    "SPLIT": [r"\bsplit\b", r"1\s*hold.*1\s*fail"],
    "TIMEOUT": [r"timeout", r"invalid"],
}


def classify_verdict(text: str) -> str:
    """Return CLAIM_FAILS / CLAIM_HOLDS / SPLIT / TIMEOUT / UNKNOWN."""
    for verdict, patterns in VERDICT_PATTERNS.items():
        for rgx in patterns:
            if re.search(rgx, text, re.IGNORECASE):
                return verdict
    return "UNKNOWN"


def extract_cycle(topic: str) -> int | None:
    """Extract cycle number from topic like 'critic/cycle258-...'."""
    m = re.search(r"cycle\s*(\d+)", topic, re.IGNORECASE)
    return int(m.group(1)) if m else None


def query_critic_facts(db_path: Path) -> list[dict]:
    """Query all critic/* facts in memory."""
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.Error:
        return []
    try:
        rows = conn.execute(
            "SELECT id, topic, proposition, created_at FROM facts "
            "WHERE topic LIKE 'critic/%' AND superseded_by IS NULL "
            "ORDER BY created_at"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    out: list[dict] = []
    for r in rows:
        fid, topic, prop, ts = r
        out.append({
            "id": fid,
            "topic": topic,
            "cycle": extract_cycle(topic),
            "created_at": ts,
            "verdict": classify_verdict(prop or ""),
        })
    return out


def compute_stats(facts: list[dict], threshold_cycle: int = 264) -> dict:
    """Compute A4-violation rate before/after threshold cycle."""
    pre = [f for f in facts if f["cycle"] and f["cycle"] < threshold_cycle]
    post = [f for f in facts if f["cycle"] and f["cycle"] >= threshold_cycle]

    def rate(items: list[dict]) -> dict:
        if not items:
            return {"n_total": 0, "n_fails": 0, "rate": 0.0,
                    "by_verdict": {}}
        counts = Counter(f["verdict"] for f in items)
        fails = counts.get("CLAIM_FAILS", 0) + counts.get("SPLIT", 0)
        return {
            "n_total": len(items),
            "n_fails": fails,
            "rate": fails / len(items),
            "by_verdict": dict(counts),
        }

    return {
        "n_critic_facts": len(facts),
        "threshold_cycle": threshold_cycle,
        "pre_threshold": rate(pre),
        "post_threshold": rate(post),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--semantic-db",
        type=Path,
        default=Path.home() / ".engram" / "semantic" / "semantic.db",
    )
    parser.add_argument("--threshold-cycle", type=int, default=264)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    facts = query_critic_facts(args.semantic_db)
    stats = compute_stats(facts, args.threshold_cycle)
    stats["facts"] = facts

    # Falsifiability test (paper §9.3 prediction)
    pre_rate = stats["pre_threshold"]["rate"]
    post_rate = stats["post_threshold"]["rate"]
    baseline_pct = pre_rate * 100
    post_pct = post_rate * 100
    # IMPORTANT: insufficient_data must be checked FIRST. Otherwise
    # post_rate=0/0=0.0 spuriously triggers PREDICTION_SUPPORTED.
    if stats["post_threshold"]["n_total"] < 3:
        verdict = "INSUFFICIENT_DATA (need >= 3 post-threshold critic facts)"
    elif post_rate < 0.10 and pre_rate >= 0.18:
        verdict = "PREDICTION_SUPPORTED"
    elif post_rate >= 0.18:
        verdict = "PREDICTION_FAILED"
    else:
        verdict = "INCONCLUSIVE"
    stats["paper_9_3_prediction"] = {
        "baseline_pct": baseline_pct,
        "post_pct": post_pct,
        "target_post_pct": 10.0,
        "verdict": verdict,
    }

    payload = json.dumps(stats, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
