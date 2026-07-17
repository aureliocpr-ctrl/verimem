"""Moat write-gate JUDGE on EXTERNAL corpora — generalization, not memorization.

Mandate (Aurelio 2026-07-17): the moat must be calibrated on GENERAL/EXTERNAL
data, not the author's hand-made cases, simulating every use case. This scores
the PRODUCTION L4 judge (``fact_grounding_score_ex`` with the real _FACT_SYSTEM
prompt) on never-seen public benchmarks and reports, per corpus:

  * AUROC (rank separation of faithful vs confabulated, threshold-free)
  * faithful ADMIT rate  (label=1 scored >= production threshold)
  * confab  BLOCK rate   (label=0 scored <  production threshold)

Corpora & the use case each simulates (held-out splits, never read):
  * TruthfulQA  — faithful PARAPHRASE (admit) vs MISCONCEPTION trap (block)
  * HaluEval QA — faithful ANSWER (admit) vs HALLUCINATED answer (block)

1 judge call per pair. Model chosen on the CLI (sonnet-5 bulk, opus hard-slice).

    python -m benchmark.moat_external_judge --model claude-sonnet-5 \
        --corpora truthfulqa,halueval --n-per-corpus 120 \
        --out benchmark/results/moat_external_judge_sonnet.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time
from pathlib import Path
from typing import Any

DATA = Path(__file__).parent / "data" / "external"
RESULTS = Path(__file__).parent / "results"


def _auroc(pos: list[float], neg: list[float]) -> float:
    """Rank-based AUROC (Mann-Whitney), ties = half. No sklearn."""
    if not pos or not neg:
        return 0.0
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return round(wins / (len(pos) * len(neg)), 4)


def load_truthfulqa(n: int, seed: int) -> list[dict[str, Any]]:
    rows = [json.loads(x) for x in
            (DATA / "truthfulqa_pairs_heldout.jsonl").read_text(
                encoding="utf-8").splitlines() if x.strip()]
    pos = [r for r in rows if r["label"] == 1]
    neg = [r for r in rows if r["label"] == 0]
    rng = random.Random(seed)
    k = n // 2
    rng.shuffle(pos)
    rng.shuffle(neg)
    return pos[:k] + neg[:k]


def load_halueval(n: int, seed: int) -> list[dict[str, Any]]:
    rows = [json.loads(x) for x in
            (DATA / "halueval_qa_heldout.jsonl").read_text(
                encoding="utf-8").splitlines() if x.strip()]
    rng = random.Random(seed)
    rng.shuffle(rows)
    k = n // 2
    out: list[dict[str, Any]] = []
    for r in rows[:k]:
        src = f"{r['knowledge']}\n\nQuestion: {r['question']}"
        out.append({"source": src, "claim": r["right_answer"], "label": 1,
                    "kind": "faithful_answer", "category": "halueval"})
        out.append({"source": src, "claim": r["hallucinated_answer"], "label": 0,
                    "kind": "hallucination", "category": "halueval"})
    return out


_LOADERS = {"truthfulqa": load_truthfulqa, "halueval": load_halueval}


def evaluate(pairs: list[dict[str, Any]], llm: Any, threshold: float) -> dict[str, Any]:
    from engram.grounding_gate import fact_grounding_score_ex
    pos, neg = [], []
    rows = []
    for i, p in enumerate(pairs):
        score, backend = fact_grounding_score_ex(llm, p["source"], p["claim"])
        (pos if p["label"] == 1 else neg).append(score)
        rows.append({"label": p["label"], "kind": p.get("kind"),
                     "score": round(score, 1), "backend": backend})
        print(f"  [{i+1}/{len(pairs)}] label={p['label']} "
              f"kind={p.get('kind'):<16} score={score:.0f}")
    admit = round(sum(s >= threshold for s in pos) / len(pos), 4) if pos else None
    block = round(sum(s < threshold for s in neg) / len(neg), 4) if neg else None
    return {"n_pos": len(pos), "n_neg": len(neg), "threshold": threshold,
            "auroc": _auroc(pos, neg), "faithful_admit_rate": admit,
            "confab_block_rate": block,
            "pos_scores": [round(s, 1) for s in pos],
            "neg_scores": [round(s, 1) for s in neg], "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--corpora", default="truthfulqa,halueval")
    ap.add_argument("--n-per-corpus", type=int, default=120)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    # Force the LLM judge path (not the local CE) — this bench measures the judge.
    os.environ["ENGRAM_GROUNDING_BACKEND"] = "claude"
    from benchmark.qa_runner import LeanClaudeCLILLM
    from engram.grounding_gate import resolve_write_threshold_for
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=90)
    threshold = resolve_write_threshold_for("claude")

    per_corpus = {}
    for name in [c.strip() for c in a.corpora.split(",") if c.strip()]:
        loader = _LOADERS[name]
        pairs = loader(a.n_per_corpus, a.seed)
        print(f"\n=== {name} (n={len(pairs)} pairs, judge={a.model}) ===")
        per_corpus[name] = evaluate(pairs, llm, threshold)

    allpos = [s for c in per_corpus.values() for s in c["pos_scores"]]
    allneg = [s for c in per_corpus.values() for s in c["neg_scores"]]
    res = {"model": a.model, "threshold": threshold, "seed": a.seed,
           "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "overall_auroc": _auroc(allpos, allneg),
           "overall_admit_rate": round(sum(s >= threshold for s in allpos) / len(allpos), 4) if allpos else None,
           "overall_block_rate": round(sum(s < threshold for s in allneg) / len(allneg), 4) if allneg else None,
           "per_corpus": per_corpus}
    print(f"\n=== MOAT EXTERNAL JUDGE ({a.model}) ===")
    for name, r in per_corpus.items():
        print(f"{name:<12} AUROC={r['auroc']}  admit={r['faithful_admit_rate']}  "
              f"block={r['confab_block_rate']}  (n={r['n_pos']}+{r['n_neg']})")
    print(f"OVERALL      AUROC={res['overall_auroc']}  admit={res['overall_admit_rate']}  "
          f"block={res['overall_block_rate']}")
    if a.out:
        RESULTS.mkdir(exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
