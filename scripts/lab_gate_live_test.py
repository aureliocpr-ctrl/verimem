"""Cycle 138 FASE 4 — live synthetic test of the anti-confab gate.

Generates a controlled mix of 100 hippo_remember-style claims and runs
them through ``run_validation_gate`` against a real-but-temp SemanticMemory
seeded with the live ~/.engram corpus. Measures:

  * action distribution (persist / downgrade / reject) per category
  * latency p50/p95/p99 per validate level
  * false-positive rate: clean claims that get downgraded/rejected
  * false-negative rate: SHIPPED-no-ref claims that get persisted

Categories (synthetic):
  - clean (40)   : plain factual claim, no SHIPPED/MERGED/BUG/da-chiudere kw
  - shipped_no_ref (25)  : "Cycle X SHIPPED..." with verified_by=[]
  - shipped_with_ref (15): same but with ['commit:abc','pr:#1']
  - diagnosis_no_test (10): "Bug #X DIAGNOSED..." with verified_by=[]
  - year_contradiction (10): claim with year disjoint from seeded fact

Output: human-readable report. Empirical, not "vibe-based".
"""
from __future__ import annotations

import random
import shutil
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.anti_confab_gate import run_validation_gate
from engram.semantic import Fact, SemanticMemory


class _AgentShim:
    def __init__(self, sm: SemanticMemory) -> None:
        self.semantic = sm


def _seed_temp_sm() -> tuple[SemanticMemory, Path]:
    """Copy ~/.engram/semantic.db to /tmp so we never mutate the live corpus."""
    src = Path.home() / ".engram" / "semantic" / "semantic.db"
    if not src.exists():
        src = Path.home() / ".engram" / "semantic.db"
    if not src.exists():
        raise RuntimeError("no live semantic.db found")
    tmp = Path.home() / ".engram_lab_cycle138.db"
    if tmp.exists():
        tmp.unlink()
    shutil.copyfile(src, tmp)
    return SemanticMemory(db_path=tmp), tmp


def _generate_claims() -> list[tuple[str, str, list[str], str]]:
    """Return list of (category, proposition, verified_by, topic)."""
    out: list[tuple[str, str, list[str], str]] = []
    # 40 clean
    for i in range(40):
        out.append((
            "clean",
            f"User Aurelio prefers Italian responses #{i}",
            [],
            "preferences/aurelio",
        ))
    # 25 shipped_no_ref → expect downgrade
    for i in range(25):
        out.append((
            "shipped_no_ref",
            f"Cycle {1000+i} SHIPPED to production main",
            [],
            "lab/cycle138",
        ))
    # 15 shipped_with_ref → expect persist (clean)
    for i in range(15):
        out.append((
            "shipped_with_ref",
            f"Cycle {2000+i} SHIPPED to main",
            [f"commit:abc{i:04d}def", f"pr:#{i+90}:merged"],
            "lab/cycle138",
        ))
    # 10 diagnosis_no_test → expect downgrade
    for i in range(10):
        out.append((
            "diagnosis_no_test",
            f"Bug #{3000+i} DIAGNOSED as race in cache.py",
            [],
            "lab/cycle138",
        ))
    # 10 year_contradiction → expect reject (full mode)
    # Use Tonegawa Nobel year as canonical contradiction.
    for i in range(10):
        out.append((
            "year_contradiction",
            f"Tonegawa Susumu won the Nobel Prize in {2014 + i % 3}",
            [],
            "science/biology",
        ))
    random.Random(42).shuffle(out)
    return out


def _seed_contradiction_anchors(sm: SemanticMemory) -> None:
    """Insert known-good anchors so year_contradiction claims have something to clash with."""
    sm.store(Fact(
        id="lab-tonegawa-anchor",
        proposition="Tonegawa Susumu won the Nobel Prize in 1987",
        topic="science/biology",
        confidence=0.95,
        verified_by=["url:wikipedia.org/wiki/Susumu_Tonegawa"],
        status="verified",
    ))


def _run_pass(
    claims: list[tuple[str, str, list[str], str]],
    sm: SemanticMemory,
    level: str,
    mode: str,
) -> dict:
    agent = _AgentShim(sm)
    latencies_ms: list[float] = []
    by_cat: dict[str, dict[str, int]] = {}
    for cat, prop, vb, topic in claims:
        t0 = time.perf_counter()
        r = run_validation_gate(
            proposition=prop, verified_by=vb, topic=topic,
            agent=agent, validate=level, gate_mode=mode,
        )
        dt = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt)
        bucket = by_cat.setdefault(cat, {"persist": 0, "downgrade": 0, "reject": 0})
        bucket[r.action] = bucket.get(r.action, 0) + 1
    latencies_ms.sort()
    return {
        "level": level,
        "mode": mode,
        "n": len(claims),
        "by_cat": by_cat,
        "lat": {
            "min": min(latencies_ms),
            "mean": statistics.mean(latencies_ms),
            "p50": latencies_ms[len(latencies_ms) // 2],
            "p95": latencies_ms[int(len(latencies_ms) * 0.95)],
            "p99": latencies_ms[int(len(latencies_ms) * 0.99)],
            "max": max(latencies_ms),
        },
    }


def main() -> int:
    sm, tmp = _seed_temp_sm()
    try:
        _seed_contradiction_anchors(sm)
        claims = _generate_claims()
        print(f"Loaded corpus copy at {tmp}. Synthetic claims: {len(claims)}")
        print()

        for level in ("fast", "full"):
            for mode in ("downgrade", "reject"):
                r = _run_pass(claims, sm, level, mode)
                print("=" * 60)
                print(f"validate={level}, gate_mode={mode}")
                print("=" * 60)
                print(
                    f"latency_ms: min={r['lat']['min']:.2f} "
                    f"mean={r['lat']['mean']:.2f} "
                    f"p50={r['lat']['p50']:.2f} "
                    f"p95={r['lat']['p95']:.2f} "
                    f"p99={r['lat']['p99']:.2f} "
                    f"max={r['lat']['max']:.2f}"
                )
                print("actions by category:")
                for cat in sorted(r["by_cat"]):
                    print(f"  {cat:<22} {r['by_cat'][cat]}")
                print()

        # FP / FN: judge in fast+downgrade mode (the default).
        baseline = _run_pass(claims, sm, "fast", "downgrade")
        clean = baseline["by_cat"].get("clean", {})
        fp = clean.get("downgrade", 0) + clean.get("reject", 0)
        ship_no_ref = baseline["by_cat"].get("shipped_no_ref", {})
        fn = ship_no_ref.get("persist", 0)
        print("=" * 60)
        print(f"FAST DEFAULT — false positives (clean → not persist): {fp}/40")
        print(f"FAST DEFAULT — false negatives (shipped_no_ref → persist): {fn}/25")
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
