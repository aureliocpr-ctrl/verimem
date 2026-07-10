"""TRUST-CORE block B — L4 grounding judge on EXTERNAL data (TruthfulQA).

The write-gate's entailment judge (local distilled CE, in-house heldout AUROC
0.99 on HaluMem) graded OUT OF DISTRIBUTION on misconception pairs it never
saw. This is the honest number for "does the moat generalise", not "does it
remember its training set".

Pair construction (per TruthfulQA row):
  * source           = "Q: <Question>\nA: <Best Answer>"  (what a document
                        or a verified memory would hold)
  * positive claim   = an ALTERNATIVE correct answer (paraphrase) when one
                        exists — an identical string would test string match,
                        not entailment; identity fallbacks are counted and
                        reported separately (`n_identity_pos`).
  * negative claim   = Best Incorrect Answer — the plausible misconception a
                        sycophantic writer would try to store.
The judge must admit the paraphrase (source ⊢ claim) and refuse the trap.

No LLM, no API: the production scorer is the local CE
(`engram.local_grounding.LocalGroundingJudge`); tests inject a fake.

Usage
  python -m benchmark.external_grounding --make-samples
  python -m benchmark.external_grounding --split dev --n 100
  python -m benchmark.external_grounding --split dev --n 100 --threshold 99.64
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any, Callable

DATA_DIR = Path(__file__).parent / "data" / "external"
CACHE_SRC = DATA_DIR / ".cache" / "TruthfulQA.csv"
RESULTS_DIR = Path(__file__).parent / "results"

ScoreFn = Callable[[str, str], float]


def load_truthfulqa(csv_path: Path) -> list[dict[str, Any]]:
    with open(csv_path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def make_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One positive + one negative entailment pair per usable row."""
    pairs: list[dict[str, Any]] = []
    for row in rows:
        q = (row.get("Question") or "").strip()
        best = (row.get("Best Answer") or "").strip()
        wrong = (row.get("Best Incorrect Answer") or "").strip()
        if not (q and best and wrong):
            continue
        source = f"Q: {q}\nA: {best}"
        corrects = [c.strip() for c in (row.get("Correct Answers") or "").split(";")]
        paraphrase = next(
            (c for c in corrects if c and c.lower() != best.lower()), "")
        pos_claim, kind = (paraphrase, "paraphrase") if paraphrase \
            else (best, "identity")
        cat = (row.get("Category") or "").strip()
        pairs.append({"source": source, "claim": pos_claim, "label": 1,
                      "kind": kind, "category": cat})
        pairs.append({"source": source, "claim": wrong, "label": 0,
                      "kind": "misconception", "category": cat})
    return pairs


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_samples_tqa(src_csv: Path, out_dir: Path, *, n_dev: int = 100,
                     n_heldout: int = 300, seed: int = 42) -> dict[str, Any]:
    """Disjoint deterministic ROW splits, materialised as PAIR jsonl files.
    Held-out discipline as everywhere in block B: dev may be read, heldout is
    run, never read."""
    rows = load_truthfulqa(Path(src_csv))
    rng = random.Random(seed)
    idx = list(range(len(rows)))
    rng.shuffle(idx)
    dev_rows = [rows[i] for i in idx[:n_dev]]
    held_rows = [rows[i] for i in idx[n_dev:n_dev + n_heldout]]

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out: dict[str, Any] = {"seed": seed, "source_sha256": _sha256(Path(src_csv))}
    for name, split_rows in (("dev", dev_rows), ("heldout", held_rows)):
        pairs = make_pairs(split_rows)
        path = out_dir / f"truthfulqa_pairs_{name}.jsonl"
        path.write_text("\n".join(json.dumps(p, ensure_ascii=False)
                                  for p in pairs) + "\n", encoding="utf-8")
        out[f"n_{name}_pairs"] = len(pairs)
    return out


def load_split(name: str, limit: int | None = None) -> list[dict[str, Any]]:
    path = DATA_DIR / f"truthfulqa_pairs_{name}.jsonl"
    rows = [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows[:limit] if limit else rows


def auroc(pos_scores: list[float], neg_scores: list[float]) -> float:
    """Rank-based AUROC (Mann-Whitney), ties count half. No sklearn."""
    if not pos_scores or not neg_scores:
        return 0.0
    wins = sum((p > n) + 0.5 * (p == n)
               for p in pos_scores for n in neg_scores)
    return round(wins / (len(pos_scores) * len(neg_scores)), 4)


def evaluate(pairs: list[dict[str, Any]], score_fn: ScoreFn,
             threshold: float) -> dict[str, Any]:
    """Score every pair; verdict = production thresholding (admit iff ≥ τ)."""
    pos, neg = [], []
    per_category: dict[str, dict[str, int]] = {}
    n_identity = 0
    for p in pairs:
        s = float(score_fn(p["source"], p["claim"]))
        (pos if p["label"] == 1 else neg).append(s)
        if p["label"] == 1 and p.get("kind") == "identity":
            n_identity += 1
        cat = per_category.setdefault(p.get("category", ""),
                                      {"pos_ok": 0, "pos": 0,
                                       "neg_ok": 0, "neg": 0})
        if p["label"] == 1:
            cat["pos"] += 1
            cat["pos_ok"] += int(s >= threshold)
        else:
            cat["neg"] += 1
            cat["neg_ok"] += int(s < threshold)
    return {
        "n_pos": len(pos), "n_neg": len(neg),
        "n_identity_pos": n_identity,
        "tpr": round(sum(s >= threshold for s in pos) / len(pos), 4) if pos else 0.0,
        "tnr": round(sum(s < threshold for s in neg) / len(neg), 4) if neg else 0.0,
        "auroc": auroc(pos, neg),
        "threshold": threshold,
        "per_category": per_category,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--make-samples", action="store_true")
    ap.add_argument("--split", default="dev", choices=["dev", "heldout"])
    ap.add_argument("--n", type=int, default=0,
                    help="max PAIRS (0 = whole split)")
    ap.add_argument("--threshold", type=float, default=None,
                    help="override the production gate threshold")
    args = ap.parse_args()

    if args.make_samples:
        print(json.dumps(make_samples_tqa(CACHE_SRC, DATA_DIR), indent=2))
        return

    from engram.local_grounding import LocalGroundingJudge
    judge = LocalGroundingJudge()
    threshold = args.threshold if args.threshold is not None else (
        judge.threshold or 50.0)
    pairs = load_split(args.split, args.n or None)
    report = evaluate(pairs, judge.score, threshold)
    report.update({
        "dataset": "TruthfulQA (Apache-2.0)", "split": args.split,
        "judge": str(judge.model_dir.name),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    print(json.dumps({k: v for k, v in report.items()
                      if k != "per_category"}, indent=2))
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / (f"external_grounding_truthfulqa_{args.split}"
                         f"_{time.strftime('%Y-%m-%d')}.json")
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
