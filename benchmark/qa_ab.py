"""General A/B for the QA pipeline: toggle ONE env lever on a fixed question type.

Isolates the causal effect of a single knob (e.g. ENGRAM_ANSWER_STRICT,
ENGRAM_QA_DATES) on the engram arm, same questions both ways. Serial claude -p
(O5 subscription). Example — is the strict answer prompt the preference killer?

    python -m benchmark.qa_ab --type single-session-preference \
        --env ENGRAM_ANSWER_STRICT --on 1 --off 0 --n 16 --seed 7 \
        --out benchmark/results/qa_ab_pref_strict.json
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
    ap.add_argument("--type", required=True, help="question_type to filter")
    ap.add_argument("--env", required=True, help="env var to A/B")
    ap.add_argument("--on", default="1")
    ap.add_argument("--off", default="0")
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    raw = json.loads(Path(a.dataset).read_text(encoding="utf-8"))
    pool = [q for q in raw if q.get("question_type") == a.type]
    random.Random(a.seed).shuffle(pool)
    data = pool[: a.n]

    from benchmark.qa_runner import LeanClaudeCLILLM
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=90)

    os.environ[a.env] = a.off
    off = _engram_acc(data, llm, a.k)
    os.environ[a.env] = a.on
    on = _engram_acc(data, llm, a.k)

    res = {"question_type": a.type, "n": len(data), "seed": a.seed, "env": a.env,
           "off_value": a.off, "on_value": a.on, "model": a.model,
           f"{a.env}={a.off}": off, f"{a.env}={a.on}": on,
           "delta_on_minus_off": round(on["qa_accuracy"] - off["qa_accuracy"], 4)}
    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
