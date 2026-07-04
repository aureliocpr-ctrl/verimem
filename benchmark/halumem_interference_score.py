"""HaluMem interference evaluation, stage 2 (scoring).

Consumes the stage-0 tasks (with ground-truth ``label``) and the stage-1 LLM
verdicts (``relation`` ∈ {CONTRADICTION, UNSUPPORTED, CONSISTENT}) and reports the
HONEST decomposition of Engram on HaluMem's interference axis.

Headline metric = CONTRADICTION-only (the clean, defensible one):
  - TPR  = interference points judged CONTRADICTION / all interference points
  - FPR  = true controls judged CONTRADICTION / all true controls
because a NEW true memory is legitimately *unsupported* by the existing corpus —
so "UNSUPPORTED" cannot be an admission-blocking signal without a per-memory
source (which HaluMem's format does not provide). The UNSUPPORTED share of
interference is reported separately as the fabrication tail that pairwise
contradiction cannot catch (it needs source-grounding).

Wilson 95% score interval for each rate.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def score(tasks: list[dict], verdicts: list[dict]) -> dict:
    rel_by_id = {v["id"]: v["relation"] for v in verdicts if "id" in v and "relation" in v}
    label_by_id = {t["id"]: t["label"] for t in tasks}

    interf = [tid for tid, lab in label_by_id.items() if lab == "interference"]
    control = [tid for tid, lab in label_by_id.items() if lab == "true"]

    def counts(ids: list[int]) -> dict:
        c = {"CONTRADICTION": 0, "UNSUPPORTED": 0, "CONSISTENT": 0, "MISSING": 0}
        for tid in ids:
            r = rel_by_id.get(tid)
            c[r if r in c else "MISSING"] += 1
        return c

    ic = counts(interf)
    cc = counts(control)

    n_i = len(interf)
    n_c = len(control)
    # Headline: contradiction-only. MISSING verdicts count as "not flagged"
    # (conservative — a dropped item is not credited as a catch).
    tpr = ic["CONTRADICTION"] / max(1, n_i)
    fpr = cc["CONTRADICTION"] / max(1, n_c)
    # Upper-bound "flaggable" if a per-memory source existed (contradiction OR
    # unsupported) — reported as an aspiration ceiling, not the headline.
    detect_ceiling = (ic["CONTRADICTION"] + ic["UNSUPPORTED"]) / max(1, n_i)

    return {
        "n_interference": n_i,
        "n_control": n_c,
        "interference_breakdown": ic,
        "control_breakdown": cc,
        "tpr_contradiction": round(tpr, 4),
        "tpr_ci95": [round(x, 4) for x in wilson(ic["CONTRADICTION"], n_i)],
        "fpr_contradiction": round(fpr, 4),
        "fpr_ci95": [round(x, 4) for x in wilson(cc["CONTRADICTION"], n_c)],
        "detect_ceiling_contra_or_unsupported": round(detect_ceiling, 4),
        "unsupported_tail_share": round(ic["UNSUPPORTED"] / max(1, n_i), 4),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--verdicts", type=Path, required=True,
                    help="JSON file: either {verdicts:[...]} or a bare [...] list")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    tasks = json.loads(args.tasks.read_text(encoding="utf-8"))["tasks"]
    vraw = json.loads(args.verdicts.read_text(encoding="utf-8"))
    verdicts = vraw["verdicts"] if isinstance(vraw, dict) else vraw

    summary = score(tasks, verdicts)
    print(json.dumps(summary, indent=2))
    if args.out:
        args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
