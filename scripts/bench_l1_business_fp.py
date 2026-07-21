"""Measure the L1.x false-positive rate on legitimate vertical facts.

Drives the PUBLIC write path (Memory.add) exactly as a customer would, each on
a fresh store, and reports how many ordinary lawyer/engineer/HR/clinician facts
the anti-confabulation detectors QUARANTINE — keeping them out of default
recall. Every fact ships its own source (source == fact), so admission is clean
by grounding; a quarantine here is a keyword false-positive, not a grounding
decision.

    python scripts/bench_l1_business_fp.py           # human summary
    python scripts/bench_l1_business_fp.py --json out.json
"""
from __future__ import annotations

import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from benchmark.l1_business_corpus import BUSINESS_CONTROLS, BUSINESS_FACTS  # noqa: E402
from verimem.client import Memory  # noqa: E402


def _add(fact: str, i: int) -> dict:
    m = Memory(path=Path(tempfile.mkdtemp(prefix="verimem_l1fp_")) / "m.db")
    r = m.add(fact, topic="bench/l1fp", source=fact,
              verified_by=[f"source-doc:l1fp:{i}"])
    warns = [w.get("layer") or w.get("code") or "?"
             for w in (r.get("warnings") or [])]
    return {"status": r.get("status"), "layers": warns,
            "grounding": r.get("grounding_score")}


def main() -> None:
    rows = []
    for i, (fact, vertical, expected) in enumerate(BUSINESS_FACTS):
        res = _add(fact, i)
        quarantined = res["status"] == "quarantined"
        rows.append({"fact": fact, "vertical": vertical, "expected": expected,
                     "status": res["status"], "layers": res["layers"],
                     "quarantined": quarantined})

    controls = []
    for i, (fact, vertical) in enumerate(BUSINESS_CONTROLS):
        res = _add(fact, 1000 + i)
        controls.append({"fact": fact, "vertical": vertical,
                         "status": res["status"],
                         "quarantined": res["status"] == "quarantined"})

    q = [r for r in rows if r["quarantined"]]
    by_detector = Counter(r["expected"] for r in q)
    by_vertical = Counter(r["vertical"] for r in q)
    ctrl_q = [c for c in controls if c["quarantined"]]

    res = {
        "n_facts": len(rows),
        "quarantined": len(q),
        "fp_rate": round(len(q) / len(rows), 3),
        "by_detector": dict(by_detector.most_common()),
        "by_vertical": dict(by_vertical.most_common()),
        "n_controls": len(controls),
        "controls_quarantined": len(ctrl_q),
        "rows": rows,
        "controls": controls,
    }

    if "--json" in sys.argv:
        idx = sys.argv.index("--json")
        Path(sys.argv[idx + 1]).write_text(
            json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")

    print("L1.x FALSE-POSITIVE on legitimate vertical facts")
    print(f"  quarantined: {res['quarantined']}/{res['n_facts']}  "
          f"(FP rate {res['fp_rate']:.1%})")
    print(f"  controls (no trigger word) quarantined: "
          f"{res['controls_quarantined']}/{res['n_controls']}")
    print("\n  by detector:")
    for det, n in res["by_detector"].items():
        print(f"    {det:14} {n}")
    print("\n  by vertical:")
    for v, n in res["by_vertical"].items():
        print(f"    {v:14} {n}")
    print("\n  quarantined facts:")
    for r in q:
        print(f"    [{','.join(r['layers']) or '?':10}] {r['fact']}")
    if ctrl_q:
        print("\n  !! CONTROL facts quarantined (should be 0):")
        for c in ctrl_q:
            print(f"    {c['fact']}")


if __name__ == "__main__":
    main()
