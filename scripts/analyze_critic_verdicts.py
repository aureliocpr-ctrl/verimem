"""Cycle 293 (2026-05-23) — Critic verdict pattern analyzer.

Pioneering singolarità #32: query critic/* facts (cycle 269
CRITIC-AS-MEMORY foundation), extract worker confidence patterns,
evidence-keyword frequencies, verdict trends.

Outputs:
- per-cycle confidence (per worker)
- evidence keyword histogram
- pre/post threshold rates
- candidate new M-rules (from "GAP" / "missed" / "second" patterns)
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

EVIDENCE_KEYWORDS = [
    r"dead.code",
    r"production.caller",
    r"second.call.site",
    r"edge.cases.covered",
    r"timeout",
    r"surrogate",
    r"counterexample",
    r"GAP",
    r"missed",
    r"falsification",
    r"production.ready",
]

WORKER_PATTERNS = {
    "falsification": r"falsification",
    "caller_verification": r"caller.verification",
    "counterexample": r"counterexample",
}


def query_critic_facts(db: Path) -> list[dict]:
    if not db.exists():
        return []
    try:
        conn = sqlite3.connect(str(db))
    except sqlite3.Error:
        return []
    try:
        rows = conn.execute(
            "SELECT id, topic, proposition, created_at FROM facts "
            "WHERE topic LIKE 'critic/%' AND superseded_by IS NULL "
            "ORDER BY created_at"
        ).fetchall()
    finally:
        conn.close()
    return [
        {"id": r[0], "topic": r[1], "prop": r[2] or "", "ts": r[3]}
        for r in rows
    ]


def extract_cycle(topic: str) -> int | None:
    m = re.search(r"cycle\s*(\d+)", topic, re.IGNORECASE)
    return int(m.group(1)) if m else None


def classify_verdict(prop: str) -> str:
    # Check SPLIT first (most specific overall consensus marker)
    if re.search(r"consensus.{0,40}SPLIT|\bSPLIT\b", prop, re.IGNORECASE):
        return "SPLIT"
    # Then CLAIM_FAILS (also specific)
    if re.search(
        r"consensus.{0,40}claim_fails|CLAIM_FAILS|claim_fails\b",
        prop, re.IGNORECASE,
    ):
        return "CLAIM_FAILS"
    # Then CLAIM_HOLDS (3-0-0 unanimous OR consensus claim_holds)
    if re.search(
        r"consensus.{0,40}claim_holds|3-0-0\s*UNANIMOUS|CLAIM_HOLDS\s*3-0-0",
        prop, re.IGNORECASE,
    ):
        return "CLAIM_HOLDS"
    # Fallback: presence of "HOLD" without consensus marker
    if re.search(r"\bHOLD\b|claim_holds=true", prop, re.IGNORECASE):
        return "CLAIM_HOLDS_PARTIAL"
    return "UNKNOWN"


def extract_confidences(prop: str) -> dict[str, float]:
    """Find patterns like 'conf 0.9' or 'confidence 0.95'."""
    out: dict[str, float] = {}
    for w_name, w_rgx in WORKER_PATTERNS.items():
        # Look for "<worker>.*conf(idence)? <float>"
        pat = rf"{w_rgx}.{{0,200}}?conf(?:idence)?\s*[:=]?\s*([\d.]+)"
        m = re.search(pat, prop, re.IGNORECASE | re.DOTALL)
        if m:
            try:
                out[w_name] = float(m.group(1))
            except ValueError:
                pass
    return out


def evidence_keyword_freq(facts: list[dict]) -> dict[str, int]:
    counter: Counter = Counter()
    for f in facts:
        for kw in EVIDENCE_KEYWORDS:
            if re.search(kw, f["prop"], re.IGNORECASE):
                counter[kw] += 1
    return dict(counter)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=Path.home() / ".engram" / "semantic" / "semantic.db",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    facts = query_critic_facts(args.db)
    if not facts:
        print("[error] no critic/* facts found", file=sys.stderr)
        return 1

    per_cycle: list[dict] = []
    for f in facts:
        cycle = extract_cycle(f["topic"])
        verdict = classify_verdict(f["prop"])
        conf = extract_confidences(f["prop"])
        per_cycle.append({
            "cycle": cycle,
            "id": f["id"][:10],
            "topic": f["topic"],
            "verdict": verdict,
            "worker_confidences": conf,
        })

    verdict_dist = Counter(p["verdict"] for p in per_cycle)
    kw_freq = evidence_keyword_freq(facts)

    # Trend over cycles
    cycles_sorted = sorted(
        (p for p in per_cycle if p["cycle"]),
        key=lambda p: p["cycle"],
    )
    trend = [
        {"cycle": p["cycle"], "verdict": p["verdict"]}
        for p in cycles_sorted
    ]

    # Per-worker confidence trend (where available)
    worker_conf_trend: dict[str, list[dict]] = {}
    for w in WORKER_PATTERNS:
        worker_conf_trend[w] = [
            {"cycle": p["cycle"], "conf": p["worker_confidences"].get(w)}
            for p in cycles_sorted
            if p["worker_confidences"].get(w) is not None
        ]

    report = {
        "n_critic_facts": len(facts),
        "verdict_distribution": dict(verdict_dist),
        "evidence_keyword_freq": kw_freq,
        "per_cycle": per_cycle,
        "verdict_trend": trend,
        "worker_confidence_trend": worker_conf_trend,
    }

    payload = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
