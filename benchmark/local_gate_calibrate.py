"""Calibrate the LOCAL CE write-gate admission threshold on real HaluMem data.

The grounding gate's local backend (``ENGRAM_GROUNDING_BACKEND=local``) ships a
``gate_config.json`` threshold that ``should_store_fact`` applies on the CE
sigmoid scale (sigmoid(logit)*100). Before making ``local`` a default we must
know the REAL clean-vs-noise separation on that scale over a public corpus —
not inherit a single shipped number. This scores each candidate ONCE with the
local judge and sweeps the cut locally, so the admission precision/recall curve
is data-driven.

Zero API cost (O5): pure local CE inference on CPU — no ``claude -p``, no
network. Uses the SAME clean/noise construction as the write-path moat A/B
(``halumem_writepath_moat``): a user's own grounded memory points are CLEAN,
facts sampled from OTHER users are foreign NOISE paired with THIS user's
dialogue (plausible, well-formed, but not entailed by it).

    python -m benchmark.local_gate_calibrate --users 20 --clean 20 --noise 20 \
        --out benchmark/results/local_gate_calibrate.json

    python -m benchmark.local_gate_calibrate --smoke   # tiny end-to-end check
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def _youden_cut(clean: list[float], noise: list[float]) -> dict:
    """Youden's J optimal cut over the observed scores: the threshold t
    maximizing clean_admit_rate(>=t) - noise_admit_rate(>=t). Ties → the
    lower t (more permissive at equal J). Pure, no sklearn."""
    cands = sorted(set(clean + noise))
    if not cands or not clean or not noise:
        return {"threshold": None, "j": None}
    best_t, best_j = cands[0], -2.0
    for t in cands:
        tpr = sum(1 for s in clean if s >= t) / len(clean)
        fpr = sum(1 for s in noise if s >= t) / len(noise)
        if (tpr - fpr) > best_j:
            best_j, best_t = tpr - fpr, t
    return {"threshold": round(float(best_t), 2), "j": round(float(best_j), 4)}


def _at(thr: float, clean: list[float], noise: list[float]) -> dict:
    ca = sum(1 for s in clean if s >= thr)
    nr = sum(1 for s in noise if s < thr)
    admitted = ca + (len(noise) - nr)
    return {
        "threshold": round(float(thr), 2),
        "clean_admit_rate": round(ca / len(clean), 4) if clean else None,
        "noise_reject_rate": round(nr / len(noise), 4) if noise else None,
        "admission_precision": round(ca / admitted, 4) if admitted else None,
        "admission_recall": round(ca / len(clean), 4) if clean else None,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl",
                    default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--users", type=int, default=20)
    ap.add_argument("--clean", type=int, default=20, help="clean facts/user (cap)")
    ap.add_argument("--noise", type=int, default=20, help="foreign noise facts/user (cap)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--focus-budget", type=int, default=0,
                    help="span budget fed to the CE (0 = the model's own config budget)")
    ap.add_argument("--smoke", action="store_true", help="tiny run: 2 users, 3/3")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if a.smoke:
        a.users, a.clean, a.noise = 2, 3, 3

    from benchmark.halumem_writepath_moat import _all_facts, _clean_facts
    from engram.local_grounding import get_local_judge, get_local_threshold

    rng = random.Random(a.seed)
    users = []
    with open(a.jsonl, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                users.append(json.loads(line))
    rng.shuffle(users)
    # need a spare pool for foreign noise beyond the users we calibrate on
    pool = users[: a.users + 5]
    target_users = pool[: a.users]

    judge = get_local_judge()
    fb = a.focus_budget or None

    clean_scores: list[float] = []
    noise_scores: list[float] = []
    for u in target_users:
        clean = _clean_facts(u)
        rng.shuffle(clean)
        clean = clean[: a.clean]
        own_dialogues = [src for _, src in clean] or [""]
        others = [x for x in pool if x is not u]
        foreign_pool: list[str] = []
        for o in others:
            foreign_pool.extend(_all_facts(o))
        rng.shuffle(foreign_pool)
        noise = [(foreign_pool[i], rng.choice(own_dialogues))
                 for i in range(min(a.noise, len(foreign_pool)))]
        for txt, src in clean:
            clean_scores.append(judge.score(src, txt, focus_budget=fb))
        for txt, src in noise:
            noise_scores.append(judge.score(src, txt, focus_budget=fb))

    shipped = get_local_threshold()
    sweep_pts = [40, 50, 60, 70, 80, 85, 90, 95, 98, 99]
    if shipped is not None:
        sweep_pts.append(round(float(shipped), 2))
    sweep_pts = sorted(set(sweep_pts))

    def _mean(xs: list[float]):
        return round(sum(xs) / len(xs), 2) if xs else None

    res = {
        "model_dir": str(judge.model_dir),
        "shipped_threshold": round(float(shipped), 2) if shipped is not None else None,
        "focus_budget": a.focus_budget or "config",
        "clean_n": len(clean_scores),
        "noise_n": len(noise_scores),
        "clean_mean": _mean(clean_scores),
        "noise_mean": _mean(noise_scores),
        "clean_scores": [round(s, 2) for s in clean_scores],
        "noise_scores": [round(s, 2) for s in noise_scores],
        "youden_optimal": _youden_cut(clean_scores, noise_scores),
        "sweep": [_at(t, clean_scores, noise_scores) for t in sweep_pts],
    }
    if shipped is not None:
        res["at_shipped"] = _at(float(shipped), clean_scores, noise_scores)
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("clean_scores", "noise_scores")}, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"\n[written] {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
