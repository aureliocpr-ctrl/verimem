"""T2 — does CALIBRATION govern the pathology? (Claim 2 of EPISTEMIC_FAILURES_STUDY)

The provable spine says pathology rate is governed by the calibration of the model's
evidential confidence. We elicit a verbalized confidence (0-100) alongside each SQuAD
answer and ask: do FABRICATIONS (answers to impossible questions) carry LOWER
confidence than CORRECT grounded answers? If yes, confidence is a usable signal and a
threshold separates sound from pathological output (cure = calibration). If
fabrications are HIGH-confidence, the model is mis-calibrated/over-confident and the
problem is upstream. We report: mean confidence per class, ECE, and the AUROC of
confidence for separating sound (answerable-correct + impossible-abstained) from
pathological output. Deterministic scoring + numpy AUROC; claude -p lean, O5.
"""
from __future__ import annotations

import argparse
import json
import re
from typing import Any

import numpy as np

from benchmark.hallucination_bench import contains_gold, is_abstention, sample_squad

_CONF_RE = re.compile(r"confidence[:=]?\s*(\d{1,3})", re.I)
_SYSTEM = ("You answer a question from the context. If the context does not contain "
           "the answer, reply 'NO ANSWER'. After your answer, on a new line write "
           "'CONFIDENCE: N' where N is 0-100 = how sure you are the answer is correct "
           "and supported by the context. Respond in English.")


def _parse(text: str) -> tuple[str, float]:
    m = _CONF_RE.search(text)
    conf = float(m.group(1)) if m else 50.0
    ans = _CONF_RE.sub("", text).strip()
    return ans, min(100.0, max(0.0, conf))


def _auroc(scores: list[float], labels: list[int]) -> float:
    """AUROC that `score` ranks positives (label=1) above negatives, via the
    tie-corrected Mann-Whitney U (AVERAGE ranks for ties). Ties matter: a judge that
    emits many identical scores (e.g. lots of '100') would otherwise be scored by
    insertion order, badly biasing the AUC — that artifact produced an impossible
    AUROC<0.5 with sound-mean>patho-mean before this fix."""
    s = np.asarray(scores, float)
    y = np.asarray(labels, int)
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(s, kind="mergesort")
    s_sorted = s[order]
    ranks = np.empty(len(s), float)
    i = 0
    while i < len(s_sorted):
        j = i
        while j + 1 < len(s_sorted) and s_sorted[j + 1] == s_sorted[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0  # 1-based average rank over the tie
        i = j + 1
    r_pos = float(ranks[y == 1].sum())
    return float((r_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def run(llm: Any, *, per_class: int = 50, seed: int = 0) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for ex in sample_squad(per_class, seed):
        raw = llm.complete(
            _SYSTEM, [{"role": "user",
                       "content": f"Context: {ex['context']}\n\nQuestion: "
                                  f"{ex['question']}\nAnswer:"}], max_tokens=60)
        ans, conf = _parse(getattr(raw, "text", "") or "")
        abstained = is_abstention(ans)
        if ex["impossible"]:
            sound = abstained                # correct = abstain
            pathological = not abstained     # fabrication
        else:
            sound = (not abstained) and contains_gold(ans, ex["golds"])
            pathological = not sound
        rows.append({"impossible": ex["impossible"], "conf": conf,
                     "sound": sound, "pathological": pathological})
    fabs = [r["conf"] for r in rows if r["impossible"] and r["pathological"]]
    cor = [r["conf"] for r in rows if (not r["impossible"]) and r["sound"]]
    # AUROC: can confidence flag sound (1) vs pathological (0)?
    sig = [r["conf"] for r in rows]
    lab = [1 if r["sound"] else 0 for r in rows]
    # ECE of confidence vs soundness (10 bins)
    c = np.array([r["conf"] for r in rows]) / 100.0
    y = np.array([1 if r["sound"] else 0 for r in rows], float)
    bins = np.linspace(0, 1, 11)
    ece = 0.0
    for i in range(10):
        m = (c >= bins[i]) & (c < bins[i + 1] if i < 9 else c <= bins[i + 1])
        if m.sum():
            ece += m.mean() * abs(c[m].mean() - y[m].mean())
    return {
        "n": len(rows), "per_class": per_class,
        "mean_conf_correct_grounded": round(float(np.mean(cor)), 1) if cor else None,
        "mean_conf_fabrication": round(float(np.mean(fabs)), 1) if fabs else None,
        "auroc_conf_sound_vs_pathological": round(_auroc(sig, lab), 3),
        "ece": round(float(ece), 3),
        "n_fabrications": len(fabs), "n_correct_grounded": len(cor),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Calibration→pathology test (T2).")
    p.add_argument("--per-class", type=int, default=50)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--model", type=str, default="claude-sonnet-4-6")
    p.add_argument("--out", type=argparse.FileType("w"), default=None)
    args = p.parse_args(argv)
    from benchmark.qa_runner import LeanClaudeCLILLM
    res = run(LeanClaudeCLILLM(model=args.model, timeout_s=60),
              per_class=args.per_class, seed=args.seed)
    res["model"] = args.model
    print(json.dumps(res, indent=2))
    if args.out:
        json.dump(res, args.out, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["run", "main"]
