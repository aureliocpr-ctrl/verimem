"""Rigorous bench: lexical vs semantic conflict detection on SNLI (HUMAN labels).

The hand-crafted semantic_conflict_bench is a demonstration (n=8, author-written
pairs, one live judge run). This is the scientific version: SNLI validation
(Bowman et al. 2015 — independent human-annotated contradiction / entailment /
neutral), balanced seeded sample, with a special focus on the LOW token-overlap
contradictions — the exact "words differ but meaning conflicts" slice the moat is
about. Reports, for BOTH the lexical stack and the NLI detector, real
precision/recall/FP against the gold labels, plus the cosine distribution (the
min_cosine pre-filter is a measured recall risk, not an assumption).

Judge = claude -p lean (subscription, O5). Per-pair verdicts are recorded for
audit. Run: `python -m benchmark.nli_grounding_bench --per-class 50`.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any

from engram.coherence_check import check_against_siblings
from engram.contradiction import _cosine
from engram.semantic import Fact
from engram.semantic_conflict import Relation
from engram.truth_reconciliation import looks_like_conflict

# SNLI integer label -> our Relation
_SNLI = {0: Relation.ENTAILMENT, 1: Relation.NEUTRAL, 2: Relation.CONTRADICTION}
_TOK = re.compile(r"[a-z0-9]+")


def _jaccard(a: str, b: str) -> float:
    ta = {t for t in _TOK.findall(a.lower()) if len(t) > 1}
    tb = {t for t in _TOK.findall(b.lower()) if len(t) > 1}
    return len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0


def _lexical_says_contradiction(prem: str, hyp: str) -> bool:
    f1 = Fact(id="h", proposition=hyp, topic="t")
    f0 = Fact(id="p", proposition=prem, topic="t")
    coh = check_against_siblings(f1, [f0])
    if any(w.kind in ("numeric_clash", "boolean_clash") for w in coh):
        return True
    return looks_like_conflict(prem, hyp)


def sample_snli(per_class: int, seed: int) -> list[dict[str, Any]]:
    from datasets import load_dataset
    ds = load_dataset("snli", split="validation")
    buckets: dict[int, list[dict[str, Any]]] = {0: [], 1: [], 2: []}
    idx = list(range(len(ds)))
    random.Random(seed).shuffle(idx)
    for i in idx:
        row = ds[i]
        lbl = row["label"]
        if lbl in buckets and len(buckets[lbl]) < per_class:
            buckets[lbl].append({"premise": row["premise"],
                                 "hypothesis": row["hypothesis"], "label": lbl})
        if all(len(v) >= per_class for v in buckets.values()):
            break
    return buckets[0] + buckets[1] + buckets[2]


def run(judge: Any, *, per_class: int = 50, seed: int = 0,
        min_cosine: float = 0.7) -> dict[str, Any]:
    pairs = sample_snli(per_class, seed)
    rows: list[dict[str, Any]] = []
    for p in pairs:
        prem, hyp, gold = p["premise"], p["hypothesis"], _SNLI[p["label"]]
        cos = _cosine(Fact(id="p", proposition=prem, topic="t"),
                      Fact(id="h", proposition=hyp, topic="t"))
        # NLI detector: judge is consulted only above the cosine pre-filter
        nli = judge.classify(prem, hyp) if cos >= min_cosine else Relation.NEUTRAL
        rows.append({
            "gold": gold.value, "nli": nli.value,
            "lexical_contra": _lexical_says_contradiction(prem, hyp),
            "cosine": round(cos, 3), "jaccard": round(_jaccard(prem, hyp), 3),
            "below_prefilter": cos < min_cosine,
        })

    def _metrics(rs: list[dict[str, Any]]) -> dict[str, Any]:
        gold_c = [r for r in rs if r["gold"] == "contradiction"]
        gold_n = [r for r in rs if r["gold"] == "neutral"]
        nli_tp = sum(1 for r in gold_c if r["nli"] == "contradiction")
        nli_fp = sum(1 for r in gold_n if r["nli"] == "contradiction")
        lex_tp = sum(1 for r in gold_c if r["lexical_contra"])
        lex_fp = sum(1 for r in gold_n if r["lexical_contra"])
        nc, nn = len(gold_c), len(gold_n)
        nli_prec = nli_tp / (nli_tp + nli_fp) if (nli_tp + nli_fp) else 0.0
        lex_prec = lex_tp / (lex_tp + lex_fp) if (lex_tp + lex_fp) else 0.0
        return {
            "n_contradiction": nc, "n_neutral": nn,
            "nli_contra_recall": round(nli_tp / nc, 3) if nc else 0.0,
            "nli_neutral_fp": round(nli_fp / nn, 3) if nn else 0.0,
            "nli_contra_precision": round(nli_prec, 3),
            "lexical_contra_recall": round(lex_tp / nc, 3) if nc else 0.0,
            "lexical_neutral_fp": round(lex_fp / nn, 3) if nn else 0.0,
            "lexical_contra_precision": round(lex_prec, 3),
        }

    overall = _metrics(rows)
    # the moat slice: contradictions where the WORDS differ (low token overlap)
    low = [r for r in rows if r["gold"] == "contradiction" and r["jaccard"] < 0.30]
    low_nli = sum(1 for r in low if r["nli"] == "contradiction")
    low_lex = sum(1 for r in low if r["lexical_contra"])
    # nli accuracy over the 3 classes + recall risk from the cosine pre-filter
    acc = sum(1 for r in rows if r["nli"] == r["gold"]) / len(rows) if rows else 0.0
    contra_below = [r for r in rows
                    if r["gold"] == "contradiction" and r["below_prefilter"]]
    return {
        "n": len(rows), "per_class": per_class, "seed": seed,
        "min_cosine": min_cosine,
        "nli_3class_accuracy": round(acc, 3),
        "overall": overall,
        "low_overlap_contradiction": {
            "n": len(low),
            "nli_recall": round(low_nli / len(low), 3) if low else 0.0,
            "lexical_recall": round(low_lex / len(low), 3) if low else 0.0,
        },
        "cosine_prefilter_recall_risk": {
            "contradictions_below_min_cosine": len(contra_below),
            "of_total_contradictions": overall["n_contradiction"],
        },
        "gold_dist": dict(Counter(r["gold"] for r in rows)),
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SNLI lexical-vs-NLI grounding bench.")
    p.add_argument("--per-class", type=int, default=50)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--min-cosine", type=float, default=0.7)
    p.add_argument("--model", type=str, default="claude-sonnet-4-6")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    from benchmark.qa_runner import LeanClaudeCLILLM
    from engram.semantic_conflict import LLMRelationJudge

    judge = LLMRelationJudge(LeanClaudeCLILLM(model=args.model, timeout_s=60))
    res = run(judge, per_class=args.per_class, seed=args.seed,
              min_cosine=args.min_cosine)
    res["judge"] = f"claude-cli ({args.model})"
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2))
    if args.out:
        args.out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["sample_snli", "run", "main"]
