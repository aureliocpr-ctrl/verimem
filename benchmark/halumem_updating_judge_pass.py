"""Claude-judge pass over saved UPDATING-slice artifacts — the declared-asterisk
layer that makes the local number leaderboard-comparable.

The official HaluMem updating score is LLM-judged (gpt-4o in their eval config;
O4 policy forbids external APIs, so ours is a DECLARED Claude-judge). This pass
does NOT re-run the memory system: it samples the per-item artifacts saved by
``halumem_updating_bench`` (stratified by local outcome, deterministic seed)
and asks the judge to classify each update operation with the official rubric:

  CORRECT      — the system updated the right memory (the GT original)
  HALLUCINATED — the system updated a memory that is NOT the GT original
  OMITTED      — the system updated nothing although a GT original existed

Outputs: judge-vs-local agreement matrix, per-class agreement, and the
judge-corrected accuracy estimate on the FULL run (local class rates reweighted
by the sampled judge-agreement per class — stated, not hidden).

    python -m benchmark.halumem_updating_judge_pass \
        --results benchmark/results/halumem_updating_full20_local.json \
        --per-class 20 --out benchmark/results/halumem_updating_judged.json
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

_JUDGE_SYSTEM = (
    "You judge ONE memory-update operation performed by a memory system.\n"
    "You are given: the UPDATE (new information), the TARGET MEMORY the update "
    "should modify (ground truth), and the memory the SYSTEM actually chose to "
    "update (or NONE).\n"
    "Answer with exactly one word:\n"
    "CORRECT - the system chose a memory that expresses the same fact as the "
    "ground-truth target (paraphrase counts).\n"
    "HALLUCINATED - the system chose a memory that is NOT the ground-truth "
    "target (it would corrupt an unrelated memory).\n"
    "OMITTED - the system chose NONE although a ground-truth target exists."
)

_VALID = ("correct", "hallucinated", "omitted")

#: local outcome -> the judge label it claims to be
LOCAL_TO_CLAIM = {"correct": "correct", "wrong": "hallucinated",
                  "missed": "omitted", "missed_unreachable": "omitted"}


def stratified_sample(items, per_class: int, seed: int):
    """Deterministic per-outcome sample: up to ``per_class`` items per local
    outcome class, preserving nothing else. Returns a flat list."""
    rng = random.Random(seed)
    by_class: dict[str, list] = {}
    for it in items:
        by_class.setdefault(it["outcome"], []).append(it)
    out = []
    for cls in sorted(by_class):
        pool = list(by_class[cls])
        rng.shuffle(pool)
        out.extend(pool[:per_class])
    return out


def parse_verdict(raw: str) -> str:
    """First valid label in the judge's (expected single-word) reply; a
    malformed reply is an explicit 'error', never silently coerced."""
    w = (raw or "").strip().lower()
    for label in _VALID:
        if w.startswith(label[:4]):
            return label
    return "error"


def judge_prompt(item) -> str:
    sel = (item.get("selected") or "").strip() or "NONE"
    gts = "\n".join(f"- {g}" for g in item.get("gt_originals", []))
    return (f"UPDATE (new information): {item['update']}\n"
            f"GROUND-TRUTH TARGET MEMORY (should be updated):\n{gts}\n"
            f"SYSTEM chose to update: {sel}")


def agreement_and_correction(judged, full_counts):
    """Per-class judge agreement + judge-corrected full-run accuracy.

    For each local class c with full-run count N_c and sampled judge verdicts,
    the share of sampled items the judge calls CORRECT estimates
    P(judge=correct | local=c); the corrected accuracy is
    sum_c N_c * P(correct|c) / sum_c N_c. Classes never sampled contribute
    their local claim (stated in the output)."""
    per_class: dict[str, dict] = {}
    for it in judged:
        c = it["local_outcome"]
        d = per_class.setdefault(c, {"n": 0, "judge_correct": 0, "agree": 0})
        d["n"] += 1
        v = it["judge"]
        if v == "correct":
            d["judge_correct"] += 1
        if v == LOCAL_TO_CLAIM.get(c):
            d["agree"] += 1
    total = sum(full_counts.values())
    corrected = 0.0
    for c, n_c in full_counts.items():
        d = per_class.get(c)
        if d and d["n"]:
            p = d["judge_correct"] / d["n"]
        else:
            p = 1.0 if LOCAL_TO_CLAIM.get(c) == "correct" else 0.0
        corrected += n_c * p
    return per_class, (corrected / total if total else None)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--per-class", type=int, default=20)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--model", default="claude-sonnet-4-6",
                    help="same judge as the existing QA/reconcile harnesses")
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--pause-s", type=float, default=2.0,
                    help="serial pacing between judge calls (subscription)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    from benchmark.halumem_qa_bench import wilson
    from benchmark.qa_runner import LeanClaudeCLILLM

    res = json.loads(Path(a.results).read_text(encoding="utf-8"))
    sample = stratified_sample(res["items"], a.per_class, a.seed)
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=a.timeout)

    judged = []
    t0 = time.time()
    for i, it in enumerate(sample):
        try:
            resp = llm.complete(_JUDGE_SYSTEM,
                                [{"role": "user", "content": judge_prompt(it)}],
                                max_tokens=6)
            verdict = parse_verdict(getattr(resp, "text", ""))
        except Exception as exc:  # noqa: BLE001 — one throttled call must not kill the pass
            verdict = "error"
            print(f"[{i}] judge error: {str(exc)[:80]}")
        judged.append({"local_outcome": it["outcome"], "judge": verdict,
                       "update": it["update"][:120],
                       # full texts: every bought verdict doubles as a future
                       # matcher-calibration row without heuristic re-joins
                       "selected": it.get("selected") or "",
                       "gt_originals": it.get("gt_originals", [])})
        if a.pause_s and i < len(sample) - 1:
            time.sleep(a.pause_s)

    ok = [j for j in judged if j["judge"] != "error"]
    per_class, corrected = agreement_and_correction(ok, res["outcomes"])
    n_corr_sample = sum(1 for j in ok if j["judge"] == "correct")
    out = {
        "results_file": a.results, "judge_model": a.model,
        "note": "DECLARED Claude-judge (official protocol uses gpt-4o; O4 "
                "forbids external APIs). Judge scores target-SELECTION per the "
                "official rubric; corrected accuracy reweights full-run local "
                "class counts by sampled P(judge=correct|class).",
        "sampled": len(sample), "errors": len(judged) - len(ok),
        "per_class": per_class,
        "judge_correct_rate_on_sample": round(n_corr_sample / len(ok), 4) if ok else None,
        "full_run_local_accuracy": res.get("update_accuracy"),
        "judge_corrected_accuracy": round(corrected, 4) if corrected is not None else None,
        "judge_corrected_accuracy_wilson_on_sample": wilson(n_corr_sample, len(ok)),
        "wall_s": round(time.time() - t0, 1),
        "judged": judged,
    }
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(out, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if k != "judged"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
