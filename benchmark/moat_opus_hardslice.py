"""Opus hard-slice: re-judge the RESIDUAL hard cases of the sonnet external sweep.

From moat_external_judge_sonnet results (HaluEval, held-out): re-score with a
stronger judge (opus) exactly the cases that matter at the NEW threshold 70:
  * label=0 with sonnet score >= 70  (hallucinations sonnet still admits)
  * label=1 with sonnet score <  70  (faithful answers sonnet rejects)
  * up to 6 label=0 with sonnet score < 70 as controls (must stay blocked)

Answers: is the residual miss a MODEL axis (opus closes it) or a PROMPT axis
(opus misses too, comparative/numeric reasoning needs a harder rubric)?

    python -m benchmark.moat_opus_hardslice \
        benchmark/results/moat_external_judge_sonnet_2026-07-17.json \
        --model claude-opus-4-8 --out benchmark/results/moat_opus_hardslice.json
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from benchmark.moat_external_judge import _LOADERS


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sonnet_json")
    ap.add_argument("--model", default="claude-opus-4-8")
    ap.add_argument("--threshold", type=float, default=70.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    res = json.loads(Path(a.sonnet_json).read_text(encoding="utf-8"))
    seed = res.get("seed", 42)
    r = res["per_corpus"]["halueval"]
    pairs = _LOADERS["halueval"](len(r["rows"]), seed)
    assert len(pairs) == len(r["rows"])

    admitted_neg = [(p, row) for p, row in zip(pairs, r["rows"])
                    if row["label"] == 0 and row["score"] >= a.threshold]
    rejected_pos = [(p, row) for p, row in zip(pairs, r["rows"])
                    if row["label"] == 1 and row["score"] < a.threshold]
    controls = [(p, row) for p, row in zip(pairs, r["rows"])
                if row["label"] == 0 and row["score"] < a.threshold][:6]
    plan = [("admitted_neg", x) for x in admitted_neg] + \
           [("rejected_pos", x) for x in rejected_pos] + \
           [("control_neg", x) for x in controls]
    print(f"slice: {len(admitted_neg)} admitted-negs + {len(rejected_pos)} "
          f"rejected-pos + {len(controls)} controls = {len(plan)} opus calls")

    os.environ["ENGRAM_GROUNDING_BACKEND"] = "claude"
    from benchmark.qa_runner import LeanClaudeCLILLM
    from verimem.grounding_gate import fact_grounding_score_ex
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=120)

    out_rows = []
    for i, (group, (p, row)) in enumerate(plan):
        score, _ = fact_grounding_score_ex(llm, p["source"], p["claim"])
        out_rows.append({"group": group, "label": row["label"],
                         "sonnet": row["score"], "opus": round(score, 1),
                         "claim": p["claim"][:160]})
        print(f"  [{i+1}/{len(plan)}] {group:<13} sonnet={row['score']:<6} "
              f"opus={score:.0f}")

    t = a.threshold
    neg_closed = sum(1 for x in out_rows
                     if x["group"] == "admitted_neg" and x["opus"] < t)
    pos_recovered = sum(1 for x in out_rows
                        if x["group"] == "rejected_pos" and x["opus"] >= t)
    ctrl_held = sum(1 for x in out_rows
                    if x["group"] == "control_neg" and x["opus"] < t)
    summary = {
        "model": a.model, "threshold": t,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "admitted_neg_total": len(admitted_neg),
        "admitted_neg_closed_by_opus": neg_closed,
        "rejected_pos_total": len(rejected_pos),
        "rejected_pos_recovered_by_opus": pos_recovered,
        "controls_total": len(controls), "controls_still_blocked": ctrl_held,
        "rows": out_rows,
    }
    print(f"\n=== OPUS HARD-SLICE (t={t}) ===")
    print(f"halluc sonnet-admitted, opus closes: {neg_closed}/{len(admitted_neg)}")
    print(f"faithful sonnet-rejected, opus recovers: {pos_recovered}/{len(rejected_pos)}")
    print(f"controls still blocked: {ctrl_held}/{len(controls)}")
    if a.out:
        Path(a.out).write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
