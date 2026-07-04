"""R11 — harder, REALISTIC confabulations (falsifies the SNLI-is-clean caveat of R10).

SNLI's neutral hypotheses are human-curated and may be cleaner than real extraction
confabulations. Here the confabulation is the realistic failure: a fact of the RIGHT
type attributed to the WRONG source. We take SQuAD-v2 answerable items (passage + Q +
gold) and build, per passage:
  * FAITHFUL  fact = "Regarding '<q_i>', the answer is <gold_i>."  (the source states it)
  * CONFAB    fact = "Regarding '<q_i>', the answer is <gold_j>."  (gold_j from ANOTHER
              item — a plausible, correctly-typed answer the passage does NOT state)
Both are scored by the write-path primitive `fact_grounding_score(source, fact)`. We ask:
does it separate faithful from these realistic confabulations (AUROC)? This is a harder
test than SNLI because the confab fact is well-formed, on-topic, and only wrong about
THIS source. Deterministic construction (no generation); claude -p lean, O5.
"""
from __future__ import annotations

import argparse
import json
from typing import Any

import numpy as np

from benchmark.calibration_bench import _auroc
from benchmark.grounding_signal_bench import _aurc
from benchmark.hallucination_bench import sample_squad
from engram.grounding_gate import fact_grounding_score, optimal_threshold


def _fact(q: str, ans: str) -> str:
    return f"Regarding the question '{q}', the answer is {ans}."


def run(llm: Any, *, per_class: int = 60, seed: int = 0,
        model: str | None = None) -> dict[str, Any]:
    # answerable items only (they have gold spans we can phrase as facts)
    items = [r for r in sample_squad(per_class * 2, seed)
             if not r["impossible"] and r["golds"]][:per_class]
    n = len(items)
    rows: list[dict[str, Any]] = []
    for i, it in enumerate(items):
        gold_i = it["golds"][0]
        gold_j = items[(i + 1) % n]["golds"][0]  # a real answer from another item
        faithful = _fact(it["question"], gold_i)
        confab = _fact(it["question"], gold_j)
        sf = fact_grounding_score(llm, it["context"], faithful, model=model)
        sc = fact_grounding_score(llm, it["context"], confab, model=model)
        rows.append({"faithful_score": sf, "confab_score": sc,
                     "same": gold_i.strip().lower() == gold_j.strip().lower()})
    # drop accidental collisions where the "confab" gold equals the faithful gold
    valid = [r for r in rows if not r["same"]]
    scores = [r["faithful_score"] for r in valid] + [r["confab_score"] for r in valid]
    labels = [1] * len(valid) + [0] * len(valid)
    s = np.asarray(scores, float)
    y = np.asarray(labels, int)
    return {
        "n_pairs": len(valid), "per_class": per_class,
        "mean_faithful": round(float(np.mean([r["faithful_score"] for r in valid])), 1),
        "mean_confab": round(float(np.mean([r["confab_score"] for r in valid])), 1),
        "auroc_faithful_vs_confab": round(_auroc(scores, labels), 3),
        "aurc": round(_aurc(s, y), 3),
        "opt_threshold": round(optimal_threshold(scores, labels), 1),
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Realistic fact-confabulation gate (R11).")
    p.add_argument("--per-class", type=int, default=60)
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
