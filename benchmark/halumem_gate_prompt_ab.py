"""A/B the write-gate judge prompt (V1 _FACT_SYSTEM vs V2 _FACT_SYSTEM_V2) on real
HaluMem data, to fix the documented over-rejection of abstractive memories WITHOUT
letting noise/confabs in. Scores each candidate with BOTH prompts and reports, at the
write threshold, clean-admission (want UP) and foreign/confab rejection (want ~100%).

V2 wins only if it raises clean-admit while keeping rejection high.

    python -m benchmark.halumem_gate_prompt_ab --clean 12 --foreign 10 --confab 8 \
        --out benchmark/results/halumem_gate_prompt_ab.json
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--clean", type=int, default=12)
    ap.add_argument("--foreign", type=int, default=10)
    ap.add_argument("--confab", type=int, default=8)
    ap.add_argument("--threshold", type=float, default=40.0)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    from benchmark.halumem_writepath_moat import (_all_facts, _clean_facts,
                                                  _make_confab, _questions)
    from benchmark.qa_runner import LeanClaudeCLILLM
    from engram import grounding_gate as G

    rng = random.Random(7)
    users = []
    with open(a.jsonl, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                users.append(json.loads(line))
    rng.shuffle(users)
    u, others = users[0], users[1:4]
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=a.timeout)

    clean = _clean_facts(u)
    rng.shuffle(clean)
    clean = clean[: a.clean]
    own_dialogues = [src for _, src in clean] or [""]
    foreign_pool = []
    for o in others:
        foreign_pool.extend(_all_facts(o))
    rng.shuffle(foreign_pool)
    foreign = [(foreign_pool[i], rng.choice(own_dialogues))
               for i in range(min(a.foreign, len(foreign_pool)))]
    answerable = [q for q in _questions(u)
                  if "unknown" not in str(q.get("answer", "")).lower()
                  and "not provided" not in str(q.get("answer", "")).lower()]
    rng.shuffle(answerable)
    confab = []
    for q in answerable[: a.confab]:
        c = _make_confab(llm, q.get("question", ""), str(q.get("answer", "")))
        if c:
            confab.append((c, rng.choice(own_dialogues)))

    groups = {"clean": clean, "foreign": foreign, "confab": confab}
    prompts = {"v1": None, "v2": G._FACT_SYSTEM_V2}  # None -> default _FACT_SYSTEM

    res = {"threshold": a.threshold, "arms": {}}
    for pname, sysprompt in prompts.items():
        arm = {}
        for gname, items in groups.items():
            scores = [G.fact_grounding_score(llm, src, txt, system=sysprompt)
                      for txt, src in items]
            n = len(scores)
            admit = sum(1 for s in scores if s >= a.threshold)
            arm[gname] = {
                "n": n,
                "admit_rate": round(admit / n, 3) if n else None,
                "mean": round(sum(scores) / n, 1) if n else None,
                "scores": scores,
            }
        # clean wants admit UP; foreign/confab want admit DOWN (reject high)
        arm["summary"] = {
            "clean_admit": arm["clean"]["admit_rate"],
            "foreign_reject": round(1 - arm["foreign"]["admit_rate"], 3) if arm["foreign"]["n"] else None,
            "confab_reject": round(1 - arm["confab"]["admit_rate"], 3) if arm["confab"]["n"] else None,
        }
        res["arms"][pname] = arm

    v1, v2 = res["arms"]["v1"]["summary"], res["arms"]["v2"]["summary"]
    res["verdict"] = {
        "clean_admit_delta_v2_minus_v1": round((v2["clean_admit"] or 0) - (v1["clean_admit"] or 0), 3),
        "v2_keeps_rejection": (v2["foreign_reject"] or 0) >= 0.9 and (v2["confab_reject"] or 0) >= 0.9,
    }
    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
