"""Local 3-8B LLM as the grounding judge — can a fully-OFFLINE stack close the
CE's plausible-inference blind spot?

The free CE is a high-precision structured-contradiction filter with a
measured blind spot: plausible misconceptions score high and get admitted
(TruthfulQA heldout AUROC 0.829; ~18% escape at the default cut). The
llm-judge closes it, but claude is online. This bench asks the exact
product question: does a LOCAL 3-8B via ollama (already-installed models)
judge well enough to auto-enable as the offline escalation tier?

Apples-to-apples discipline:
  * SAME pairs as the CE certification (external_grounding heldout split,
    never read during development);
  * SAME production scorer path (`fact_grounding_score_ex` with the injected
    llm -> the _FACT_SYSTEM rubric, claude 0-100 scale, threshold 70/40);
  * SAME metrics (rank AUROC, admit/refuse at the production cuts).

Usage
  python -m benchmark.local_llm_judge_bench --models qwen2.5:7b-instruct qwen3:8b --n 80
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from benchmark.external_grounding import auroc, load_split

RESULTS_DIR = Path(__file__).parent / "results"


def bench_model(model: str, pairs: list[dict], *, checkpoint_every: int = 20) -> dict:
    from verimem.grounding_gate import fact_grounding_score_ex
    from verimem.llm import _build
    llm = _build("ollama")
    llm.default_model = model
    scored: list[dict] = []
    t0 = time.time()
    for i, p in enumerate(pairs):
        t = time.time()
        try:
            s, _judge = fact_grounding_score_ex(llm, p["source"], p["claim"])
        except Exception as exc:  # noqa: BLE001 — a dead call is data, not a crash
            s = None
            print(f"  [{model}] pair {i} ERROR: {str(exc)[:80]}")
        scored.append({**p, "score": s, "latency_s": round(time.time() - t, 2)})
        if (i + 1) % checkpoint_every == 0:
            done = i + 1
            el = time.time() - t0
            print(f"  [{model}] {done}/{len(pairs)} "
                  f"({el:.0f}s, {el/done:.1f}s/pair)", flush=True)
    ok = [r for r in scored if r["score"] is not None]
    pos = [r["score"] for r in ok if r["label"] == 1]
    neg = [r["score"] for r in ok if r["label"] == 0]
    out = {
        "model": model,
        "n_pairs": len(pairs), "n_scored": len(ok),
        "n_errors": len(scored) - len(ok),
        "auroc": auroc(pos, neg),
        "mean_latency_s": round(sum(r["latency_s"] for r in ok) / max(1, len(ok)), 2),
        "by_threshold": {},
        "rows": scored,
    }
    for thr in (40.0, 70.0):
        tpr = sum(1 for s in pos if s >= thr) / max(1, len(pos))   # admit true
        escape = sum(1 for s in neg if s >= thr) / max(1, len(neg))  # admit false
        out["by_threshold"][str(int(thr))] = {
            "true_admit_rate": round(tpr, 3),
            "misconception_escape_rate": round(escape, 3),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--n", type=int, default=80,
                    help="pairs from the heldout split (label-balanced by construction)")
    ap.add_argument("--split", default="heldout", choices=["dev", "heldout"])
    args = ap.parse_args()
    pairs = load_split(args.split, limit=args.n)
    print(f"split={args.split} pairs={len(pairs)} "
          f"(pos={sum(1 for p in pairs if p['label']==1)} "
          f"neg={sum(1 for p in pairs if p['label']==0)})")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = {}
    for m in args.models:
        print(f"== {m} ==", flush=True)
        r = bench_model(m, pairs)
        safe = m.replace(":", "_").replace("/", "_")
        (RESULTS_DIR / f"local_llm_judge_{safe}.json").write_text(
            json.dumps(r, indent=2), encoding="utf-8")
        summary[m] = {k: r[k] for k in
                      ("auroc", "n_scored", "n_errors", "mean_latency_s",
                       "by_threshold")}
        print(json.dumps(summary[m], indent=2), flush=True)
    ce_ref = {"auroc": 0.829,
              "note": "CE certified on the same heldout (EVIDENCE-external-2026-07-19)"}
    (RESULTS_DIR / "local_llm_judge_summary.json").write_text(
        json.dumps({"ce_reference": ce_ref, "models": summary}, indent=2),
        encoding="utf-8")
    print("\n=== SUMMARY (CE reference AUROC 0.829, same pairs) ===")
    for m, s in summary.items():
        print(f"  {m:24} AUROC={s['auroc']}  "
              f"t70 admit/escape={s['by_threshold']['70']['true_admit_rate']}/"
              f"{s['by_threshold']['70']['misconception_escape_rate']}  "
              f"lat={s['mean_latency_s']}s")


if __name__ == "__main__":
    main()
