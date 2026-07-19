"""External certification of the write-path contradiction JUDGE on a standard NLI
dataset (SNLI), larger-n than the 18 hand-labeled pairs in
``semantic_conflict_bench.py``.

What it measures — the shipped free local NLI ``RelationJudge`` (``LocalRelationJudge``,
MoritzLaurer DeBERTa-v3-large) run exactly as the moat runs it (symmetric: CONTRADICTION
if EITHER direction's contradiction prob ≥ threshold; ENTAILMENT only if BOTH). For each
SNLI pair we compare the judge's verdict to the gold label and report the metrics that
matter for a PRECISION-biased moat (a wrong CONTRADICTION impugns a true fact):

  * contradiction recall  — of gold-CONTRADICTION pairs, % the judge calls CONTRADICTION
  * FALSE-contradiction rate — of gold-{ENTAILMENT,NEUTRAL} pairs, % WRONGLY called
    CONTRADICTION (the precision-critical number)
  * entailment recall     — of gold-ENTAILMENT pairs, % called ENTAILMENT (duplicate
    detection)

HONEST CAVEAT (printed with the result): SNLI is NEAR-IN-DOMAIN for this model
(MoritzLaurer trained on MNLI/FEVER/ANLI/ling/wanli — same NLI distribution, though not
SNLI itself), so these numbers are OPTIMISTIC vs a truly out-of-distribution corpus —
exactly the caveat Phase 0 documented for the 0.96-0.97 SNLI grounding number. This
certifies the judge's NLI competence at scale, NOT an OOD guarantee.

Run:  python -m benchmark.semantic_conflict_external --per-label 150
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

from verimem.local_relation import LocalRelationJudge
from verimem.semantic_conflict import Relation

# SNLI integer labels
_SNLI = {0: "entailment", 1: "neutral", 2: "contradiction"}


def _load_pairs(per_label: int) -> list[tuple[str, str, str]]:
    """(premise, hypothesis, gold) balanced across the three labels from SNLI test."""
    from datasets import load_dataset
    ds = load_dataset("snli", split="test")
    want = {k: per_label for k in _SNLI.values()}
    out: list[tuple[str, str, str]] = []
    for row in ds:
        gold = _SNLI.get(row["label"])
        if gold is None or want.get(gold, 0) <= 0:
            continue
        p, h = (row["premise"] or "").strip(), (row["hypothesis"] or "").strip()
        if not p or not h:
            continue
        out.append((p, h, gold))
        want[gold] -= 1
        if all(v <= 0 for v in want.values()):
            break
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-label", type=int, default=150)
    ap.add_argument("--out", default="benchmark/results/semantic_conflict_snli.json")
    args = ap.parse_args()

    pairs = _load_pairs(args.per_label)
    judge = LocalRelationJudge()  # shipped default, cached
    verdicts = judge.classify_batch([(p, h) for p, h, _ in pairs])

    # confusion[gold][verdict]
    confusion: dict[str, Counter] = {g: Counter() for g in _SNLI.values()}
    for (_, _, gold), v in zip(pairs, verdicts, strict=True):
        confusion[gold][v.value] += 1

    def _rate(gold: str, verdict: str) -> float:
        tot = sum(confusion[gold].values())
        return round(confusion[gold][verdict] / tot, 4) if tot else 0.0

    n_nonconf = sum(sum(confusion[g].values()) for g in ("entailment", "neutral"))
    false_contra = sum(confusion[g][Relation.CONTRADICTION.value]
                       for g in ("entailment", "neutral"))
    result = {
        "dataset": "snli/test", "n": len(pairs), "per_label": args.per_label,
        "model": judge.model_name,
        "contradiction_recall": _rate("contradiction", "contradiction"),
        "entailment_recall": _rate("entailment", "entailment"),
        "false_contradiction_rate": round(false_contra / n_nonconf, 4) if n_nonconf else 0.0,
        "confusion": {g: dict(confusion[g]) for g in _SNLI.values()},
        "caveat": "SNLI is near-in-domain for this model; optimistic vs OOD.",
    }
    import pathlib
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
