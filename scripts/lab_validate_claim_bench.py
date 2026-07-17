"""Cycle 138 FASE 1 — latency benchmark for validate_claim on live corpus.

Goal: decide if validate_claim is fast enough to gate hippo_remember on
every write. Threshold for "gate-feasible" = p99 < 50ms on the live
1183-fact corpus. Above that the gate adds noticeable user-perceived
latency to every save.

Method: sample N random propositions from semantic.db, call
validate_claim against the live SemanticMemory wrapping the same db,
record wall-clock per call.

Run::
    python scripts/lab_validate_claim_bench.py            # N=100 default
    python scripts/lab_validate_claim_bench.py --n 500    # heavier
"""
from __future__ import annotations

import argparse
import sqlite3
import statistics
import sys
import time
from pathlib import Path

# Allow running from repo root without install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.semantic import SemanticMemory
from verimem.validate_claim import validate_claim


class _AgentShim:
    """Minimal agent stub: validate_claim only touches `agent.semantic`."""
    def __init__(self, sm: SemanticMemory) -> None:
        self.semantic = sm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    home = Path.home() / ".engram"
    sem_db = home / "semantic" / "semantic.db"
    if not sem_db.exists():
        sem_db = home / "semantic.db"
    if not sem_db.exists():
        print(f"ERROR: no semantic.db at {home}")
        return 1

    # Sample N random propositions
    with sqlite3.connect(str(sem_db)) as conn:
        rows = conn.execute(
            "SELECT proposition, topic FROM facts "
            "WHERE proposition IS NOT NULL AND length(proposition) > 30 "
            "ORDER BY RANDOM() LIMIT ?",
            (args.n,),
        ).fetchall()
    if not rows:
        print("ERROR: zero facts sampled")
        return 1

    sm = SemanticMemory(db_path=sem_db)
    agent = _AgentShim(sm)

    # Warm-up: 3 calls to load cache
    for prop, topic in rows[:3]:
        validate_claim(agent, prop, topic_hint=topic, threshold=0.6)

    # Real measure
    latencies_ms: list[float] = []
    verdicts: dict[str, int] = {"supported": 0, "contradicted": 0, "unknown": 0}
    for prop, topic in rows:
        t0 = time.perf_counter()
        r = validate_claim(agent, prop, topic_hint=topic, threshold=0.6)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)
        v = r.get("verdict", "unknown")
        verdicts[v] = verdicts.get(v, 0) + 1

    latencies_ms.sort()
    p50 = latencies_ms[len(latencies_ms) // 2]
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
    p99 = latencies_ms[int(len(latencies_ms) * 0.99)]
    mean = statistics.mean(latencies_ms)
    mx = max(latencies_ms)
    mn = min(latencies_ms)

    print("=" * 60)
    print(f"validate_claim BENCHMARK — N={len(rows)}, corpus=~{1183} facts")
    print("=" * 60)
    print(f"latency_ms:  min={mn:.2f}  mean={mean:.2f}  p50={p50:.2f}  "
          f"p95={p95:.2f}  p99={p99:.2f}  max={mx:.2f}")
    print(f"verdicts:   supported={verdicts['supported']}  "
          f"contradicted={verdicts['contradicted']}  "
          f"unknown={verdicts['unknown']}")
    print()
    print(f"GATE-FEASIBLE (<50ms p99)?  "
          f"{'YES' if p99 < 50.0 else 'NO — too slow for synchronous gate'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
