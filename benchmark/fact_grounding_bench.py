"""R10 — the WRITE-path moat: does the grounding gate catch confabulated facts?

The answer-path verdict (R9) was negative: an external grounding gate is dominated by a
strict prompt when flagging answers. But a memory's real failure is CONFABULATION ON
WRITE — promoting a plausible INFERENCE to a stored 'fact' the source does not state.
SNLI is the clean test bed: premise = SOURCE, hypothesis = candidate FACT, with HUMAN
labels — ENTAILMENT (faithful, should store), NEUTRAL (plausible but unsupported = a
confabulation, should reject), CONTRADICTION (should reject hardest). We score each pair
with the write-path primitive `fact_grounding_score` and ask: does it SEPARATE faithful
(entailment) from confabulated (neutral)? Here there is no free self-confidence baseline
(the model verifies, it does not generate) and the task is native NLI, so this is where
structural grounding can actually be the moat. Metric: AUROC + AURC + Youden threshold
(tie-corrected). claude -p lean, O5.
"""
from __future__ import annotations

import argparse
import json
from typing import Any

import numpy as np

from benchmark.calibration_bench import _auroc
from benchmark.grounding_signal_bench import _aurc
from benchmark.nli_grounding_bench import sample_snli
from engram.grounding_gate import fact_grounding_score, optimal_threshold

# SNLI integer labels
_ENTAIL, _NEUTRAL, _CONTRA = 0, 1, 2


def run(llm: Any, *, per_class: int = 50, seed: int = 0,
        model: str | None = None) -> dict[str, Any]:
    pairs = sample_snli(per_class, seed)
    rows: list[dict[str, Any]] = []
    for p in pairs:
        score = fact_grounding_score(llm, p["premise"], p["hypothesis"], model=model)
        rows.append({"label": p["label"], "score": score})
    by = {lbl: [r["score"] for r in rows if r["label"] == lbl]
          for lbl in (_ENTAIL, _NEUTRAL, _CONTRA)}
    # primary contrast: faithful (entailment) vs confabulated (neutral)
    fc = [r for r in rows if r["label"] in (_ENTAIL, _NEUTRAL)]
    scores = [r["score"] for r in fc]
    faithful = [1 if r["label"] == _ENTAIL else 0 for r in fc]
    s = np.asarray(scores, float)
    y = np.asarray(faithful, int)
    return {
        "n": len(rows), "per_class": per_class,
        "mean_entailment": round(float(np.mean(by[_ENTAIL])), 1) if by[_ENTAIL] else None,
        "mean_neutral": round(float(np.mean(by[_NEUTRAL])), 1) if by[_NEUTRAL] else None,
        "mean_contradiction": round(float(np.mean(by[_CONTRA])), 1) if by[_CONTRA] else None,
        "auroc_faithful_vs_confab": round(_auroc(scores, faithful), 3),
        "aurc": round(_aurc(s, y), 3),
        "opt_threshold": round(optimal_threshold(scores, faithful), 1),
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Write-path fact-confabulation gate (R10).")
    p.add_argument("--per-class", type=int, default=50)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--model", type=str, default="claude-sonnet-4-6")
    p.add_argument("--out", type=argparse.FileType("w"), default=None)
    args = p.parse_args(argv)
    from benchmark.qa_runner import LeanClaudeCLILLM
    res = run(LeanClaudeCLILLM(model=args.model, timeout_s=60),
              per_class=args.per_class, seed=args.seed)
    res["model"] = args.model
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2))
    if args.out:
        json.dump(res, args.out, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["run", "main"]
