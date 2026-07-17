"""Local-NLI interference detection on the HaluMem moat tasks — can the O4-clean
LocalRelationJudge (no claude -p) do the write-path interference call as well as the
paid LLM judge?

Consumes the SAME stage-0 tasks the LLM judge was scored on (claim + top-k retrieved
candidates + ground-truth ``label`` interference/true). Runs local NLI claim-vs-
candidate in BOTH directions, takes the max contradiction prob across candidates (the
moat's OR logic, mirroring LocalRelationJudge), and reports AUROC (threshold-free) +
TPR/FPR swept over the contradiction threshold. Compare TPR/FPR to the LLM judge's
(benchmark/results/halumem_score_<seed>.json). 100% local, deterministic, no claude -p.

    python -m benchmark.interference_local_nli --tasks benchmark/results/halumem_tasks_seed7.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def roc_auc(labels, scores):
    """Threshold-free AUROC via the Mann-Whitney statistic (ties count 0.5).
    Returns None unless both classes are present."""
    pos = [s for lbl, s in zip(labels, scores) if lbl == 1]
    neg = [s for lbl, s in zip(labels, scores) if lbl == 0]
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return round(wins / (len(pos) * len(neg)), 4)


def sweep_tpr_fpr(labels, scores, thresholds):
    """TPR/FPR at each threshold (predict interference iff score >= threshold)."""
    P = sum(1 for lbl in labels if lbl == 1)
    N = sum(1 for lbl in labels if lbl == 0)
    out = {}
    for t in thresholds:
        tp = sum(1 for lbl, s in zip(labels, scores) if lbl == 1 and s >= t)
        fp = sum(1 for lbl, s in zip(labels, scores) if lbl == 0 and s >= t)
        out[t] = {"tpr": round(tp / P, 4) if P else None,
                  "fpr": round(fp / N, 4) if N else None}
    return out


def load_tasks(path):
    """(label01, claim, [candidate_texts]) per task. label interference->1, true->0."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    tasks = d["tasks"] if isinstance(d, dict) else d
    out = []
    for t in tasks:
        cands = [c.get("text", "") for c in (t.get("candidates") or [])
                 if (c.get("text") or "").strip()]
        out.append((1 if t.get("label") == "interference" else 0,
                    (t.get("claim") or "").strip(), cands))
    return out


def task_candidate_scores(claim, cand_texts, classifier):
    """Per-candidate ``(contra_prob, content_overlap)`` in ONE NLI batch, so an
    overlap floor can be swept post-hoc without re-running the model."""
    from verimem.truth_reconciliation import _content_overlap
    if not claim or not cand_texts:
        return []
    pairs = []
    for c in cand_texts:
        pairs.append((claim, c))
        pairs.append((c, claim))
    probs = classifier(pairs)
    out = []
    for i, c in enumerate(cand_texts):
        ab, ba = probs[2 * i], probs[2 * i + 1]
        contra = max(ab.get("contradiction", 0.0), ba.get("contradiction", 0.0))
        out.append((contra, _content_overlap(claim, c)))
    return out


def score_with_floor(cand_scores, min_overlap=0.0):
    """Moat OR over candidates, dropping any whose claim-overlap is below the floor
    (an unrelated NEW memory the NLI over-calls as a contradiction)."""
    best = 0.0
    for contra, overlap in cand_scores:
        if min_overlap > 0.0 and overlap < min_overlap:
            continue
        best = max(best, contra)
    return best


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="benchmark/results/halumem_tasks_seed7.json")
    ap.add_argument("--nli-model", default=None)
    ap.add_argument("--thresholds", default="0.9,0.95")
    ap.add_argument("--overlaps", default="0.0,0.1,0.15,0.2",
                    help="content-overlap floors to sweep (0 = off) — filters "
                         "unrelated candidates the NLI over-calls as contradictions")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    from verimem.local_relation import DEFAULT_NLI_MODEL, make_nli_classifier
    clf = make_nli_classifier(a.nli_model or DEFAULT_NLI_MODEL)

    rows = load_tasks(a.tasks)
    labels = [lbl for lbl, _, _ in rows]
    cand_scores = [task_candidate_scores(claim, cands, clf) for _, claim, cands in rows]
    thresholds = [float(x) for x in a.thresholds.split(",") if x.strip()]
    overlaps = [float(x) for x in a.overlaps.split(",") if x.strip()]
    grid = {}
    for ov in overlaps:
        scores = [score_with_floor(cs, ov) for cs in cand_scores]
        grid[f"overlap>={ov}"] = {
            "auroc": roc_auc(labels, scores),
            "sweep": {f"thr={t}": sweep_tpr_fpr(labels, scores, [t])[t]
                      for t in thresholds},
        }
    res = {
        "tasks": a.tasks,
        "model": a.nli_model or DEFAULT_NLI_MODEL,
        "n": len(rows), "n_pos": sum(labels), "n_neg": len(labels) - sum(labels),
        "judge_baseline": "LLM judge (claude -p): halumem_score_<seed>.json "
                          "(seed7 TPR 0.675 FPR 0.10)",
        "grid": grid,
        "note": "local NLI (no claude -p) interference detection: max bidirectional "
                "contradiction over the task's top-k candidates, with an optional "
                "content-overlap floor to drop unrelated candidates. Compare TPR/FPR "
                "to the LLM judge. AUROC is threshold-free.",
    }
    print(json.dumps({k: res[k] for k in res if k != "note"}, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
