"""Calibrate the write-gate admission threshold on real HaluMem data. The moat A/B
showed clean-admission only 62% at threshold=50 — the gate over-rejects valid
(abstractive) memory points. This scores each candidate ONCE (clean vs injected
foreign noise) and sweeps the threshold locally, so the admission precision/recall
curve is data-driven, not a guess. ~ (clean+noise) gate calls total.

    python -m benchmark.halumem_admission_sweep --clean 15 --noise 15 \
        --out benchmark/results/halumem_admission_sweep.json
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--clean", type=int, default=15)
    ap.add_argument("--noise", type=int, default=15)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    from benchmark.halumem_writepath_moat import _all_facts, _clean_facts
    from benchmark.qa_runner import LeanClaudeCLILLM
    from engram.grounding_gate import fact_grounding_score

    rng = random.Random(a.seed)
    users = []
    with open(a.jsonl, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                users.append(json.loads(line))
    rng.shuffle(users)
    u, others = users[0], users[1:4]
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=90)

    clean = _clean_facts(u)
    rng.shuffle(clean)
    clean = clean[: a.clean]
    foreign = []
    for o in others:
        foreign.extend(_all_facts(o))
    rng.shuffle(foreign)
    own_dialogues = [src for _, src in clean] or [""]
    noise = [(foreign[i], rng.choice(own_dialogues)) for i in range(min(a.noise, len(foreign)))]

    clean_scores = [fact_grounding_score(llm, src, txt) for txt, src in clean]
    noise_scores = [fact_grounding_score(llm, src, txt) for txt, src in noise]

    def at(thr):
        ca = sum(1 for s in clean_scores if s >= thr)
        nr = sum(1 for s in noise_scores if s < thr)
        admitted = ca + (len(noise_scores) - nr)  # clean admitted + noise admitted
        prec = ca / admitted if admitted else None  # of admitted, fraction clean
        rec = ca / len(clean_scores) if clean_scores else None  # of clean, fraction admitted
        return {"threshold": thr,
                "clean_admit_rate": round(ca / len(clean_scores), 3) if clean_scores else None,
                "noise_reject_rate": round(nr / len(noise_scores), 3) if noise_scores else None,
                "admission_precision": round(prec, 3) if prec is not None else None,
                "admission_recall": round(rec, 3) if rec is not None else None}

    res = {
        "clean_n": len(clean_scores), "noise_n": len(noise_scores),
        "clean_mean": round(sum(clean_scores) / len(clean_scores), 2) if clean_scores else None,
        "noise_mean": round(sum(noise_scores) / len(noise_scores), 2) if noise_scores else None,
        "clean_scores": clean_scores, "noise_scores": noise_scores,
        "sweep": [at(t) for t in (10, 20, 30, 40, 50, 60, 70, 80)],
    }
    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
