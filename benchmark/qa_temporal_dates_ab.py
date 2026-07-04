"""A/B validation of the QA date-prefix lever on LongMemEval temporal-reasoning.

The answer system prompt resolves relative dates "using the [timestamp] prefixes in
the context", but the comparative harness was dropping haystack_dates → temporal-
reasoning measured 0.0. This runs the SAME temporal-reasoning questions through the
engram arm twice — ENGRAM_QA_DATES=0 (old, date-blind) vs =1 (dated context) — to
isolate the lever. Serial claude -p (O5 subscription, no external key).

    python -m benchmark.qa_temporal_dates_ab --n 12 --seed 7 \
        --out benchmark/results/qa_temporal_ab.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
import tempfile
from pathlib import Path


def _engram_acc(data, llm, k):
    from benchmark.qa_comparative import eval_question
    workdir = Path(tempfile.mkdtemp(prefix="qa_ab_"))
    rows = [eval_question(q, llm, k=k, workdir=workdir, arms=("engram",))["arms"]["engram"]
            for q in data]
    n = len(rows)
    return {
        "n": n,
        "qa_accuracy": round(sum(r["correct"] for r in rows) / n, 4) if n else 0.0,
        "abstention_rate": round(sum(r["abstained"] for r in rows) / n, 4) if n else 0.0,
        "n_errors": sum(1 for r in rows if r.get("error")),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(Path.home() / ".cache/longmemeval/longmemeval_s"))
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    raw = json.loads(Path(a.dataset).read_text(encoding="utf-8"))
    temporal = [q for q in raw if q.get("question_type") == "temporal-reasoning"]
    random.Random(a.seed).shuffle(temporal)
    data = temporal[: a.n]

    from benchmark.qa_runner import LeanClaudeCLILLM
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=90)

    os.environ["ENGRAM_QA_DATES"] = "0"
    off = _engram_acc(data, llm, a.k)
    os.environ["ENGRAM_QA_DATES"] = "1"
    on = _engram_acc(data, llm, a.k)

    res = {"question_type": "temporal-reasoning", "n": len(data), "seed": a.seed,
           "model": a.model, "dates_off": off, "dates_on": on,
           "delta_accuracy": round(on["qa_accuracy"] - off["qa_accuracy"], 4)}
    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
