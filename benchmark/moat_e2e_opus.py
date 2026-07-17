"""Moat END-TO-END with the REAL LLM judge (opus) — mandate 2026-07-17.

Not the judge's AUROC in isolation: the PRODUCT behaviour. For each realistic
(source, faithful-fact, distractor) case we call ``Memory(llm=opus).add(fact,
source=...)`` — the exact default write path now that the moat is ON — and
record the stored status. A faithful fact must be ADMITTED, a confab
QUARANTINED. Reports admit/quarantine rates so the calibration is visible, not
asserted. Serial claude -p; ~2 judge calls/case.

    python -m benchmark.moat_e2e_opus --model claude-opus-4-8 --out benchmark/results/moat_e2e_opus.json
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from benchmark.grounding_conditioned_qa_real import CASES
from benchmark.qa_runner import LeanClaudeCLILLM
from verimem.client import Memory


def _status(mem, fact, source):
    r = mem.add(fact, source=source)          # default path: moat ON, judge=llm
    return r.get("status"), r.get("grounding_score")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-4-8")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    llm = LeanClaudeCLILLM(model=a.model, timeout_s=90)
    cases = CASES[: a.limit] if a.limit else CASES
    rows = []
    for src, q, gold, true_f, dist in cases:
        mem = Memory(Path(tempfile.mkdtemp()) / "m.db", llm=llm)
        ts, tscore = _status(mem, true_f, src)
        ds, dscore = _status(mem, dist, src)
        rows.append({"true_fact": true_f, "true_status": ts, "true_score": tscore,
                     "distractor": dist, "dist_status": ds, "dist_score": dscore})
        print(f"[{len(rows)}] true={ts}({tscore}) | distractor={ds}({dscore})")

    n = len(rows)
    faithful_admitted = sum(1 for r in rows if r["true_status"] != "quarantined")
    confab_quarantined = sum(1 for r in rows if r["dist_status"] == "quarantined")
    res = {
        "model": a.model, "n_cases": n,
        "faithful_admitted": faithful_admitted,
        "faithful_admit_rate": round(faithful_admitted / n, 3) if n else None,
        "confab_quarantined": confab_quarantined,
        "confab_quarantine_rate": round(confab_quarantined / n, 3) if n else None,
        "rows": rows,
    }
    print(f"\n=== MOAT E2E (judge {a.model}, n={n}) ===")
    print(f"faithful ADMITTED:   {faithful_admitted}/{n} "
          f"({res['faithful_admit_rate']})")
    print(f"confab QUARANTINED:  {confab_quarantined}/{n} "
          f"({res['confab_quarantine_rate']})")
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
