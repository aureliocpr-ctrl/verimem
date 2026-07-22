"""HaluMem write-poisoning HEAD-TO-HEAD: verimem (CE gate) vs mem0 (real, no gate).

The CE-gate A/B (halumem_writepath_moat --gate-ce) proxied the no-gate arm with
verimem's own store. This runs the REAL competitor on IDENTICAL items: one
candidate build (clean + same-topic confabs, seeded), three arms answered and
judged by the SAME answerer+judge so the memory layer is the only variable:

  off   verimem store, NO gate  (ingest-everything policy)
  on    verimem store, CE gate  (the product default write path)
  mem0  mem0 2.0.4 real, infer=False raw storage (mem0 HAS no write gate),
        e5-parity embedder = same encoder as verimem — run in .venv-mem0bench
        via benchmark/halumem_mem0_bridge.py (subprocess; mem0's deps never
        touch this venv), retrieval = its own vector store.

Honesty notes carried into the result: C is structurally low in ALL arms (the
sampled memory often lacks the true answer — this measures POISONING RESISTANCE,
not answer-correctness); confabs are regenerated here (claude), so numbers pair
across arms WITHIN this run, not with the earlier CE run.

    python -m benchmark.halumem_mem0_real_arm --users 8 --clean 20 --noise 12 \
        --out benchmark/results/halumem_mem0_real.json      # ~25 min serial
    python -m benchmark.halumem_mem0_real_arm --smoke       # plumbing check
"""
from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MEM0_PY = REPO / ".venv-mem0bench" / "Scripts" / "python.exe"


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - m) / d, 4), round((c + m) / d, 4))


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return None
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) * (0.5 ** n)
    return round(min(1.0, 2.0 * tail), 4)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--users", type=int, default=8)
    ap.add_argument("--clean", type=int, default=20)
    ap.add_argument("--noise", type=int, default=12)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--threshold", type=float, default=40.0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.smoke:
        a.users, a.clean, a.noise = 1, 3, 2

    import os as _os
    _os.environ.setdefault("ENGRAM_QA_DATES", "1")

    from benchmark.halumem_qa_bench import _classify
    from benchmark.halumem_writepath_moat import (
        _SRC_CAP,
        _clean_facts,
        _make_confab,
        _questions_with_source,
    )
    from benchmark.qa_eval import answer_question
    from benchmark.qa_runner import LeanClaudeCLILLM
    from verimem.grounding_gate import fact_grounding_score
    from verimem.semantic import Fact, SemanticMemory

    rng = random.Random(a.seed)
    users = []
    with open(a.jsonl, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                users.append(json.loads(line))
    rng.shuffle(users)
    users = users[: a.users]
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=a.timeout)

    # ---- phase A: ONE candidate build (identical items for every arm) ------
    build = {"users": []}
    gate = {"noise_rejected": 0, "noise_total": 0,
            "clean_admitted": 0, "clean_total": 0}
    for ui, u in enumerate(users):
        clean = _clean_facts(u)
        rng.shuffle(clean)
        clean = clean[: a.clean]
        qsrc = _questions_with_source(u)
        rng.shuffle(qsrc)
        answerable = [(q, src) for q, src in qsrc
                      if "unknown" not in str(q.get("answer", "")).lower()
                      and "not provided" not in str(q.get("answer", "")).lower()]
        noise, questions = [], []
        for q, src in answerable[: a.noise]:
            c = _make_confab(llm, q.get("question", ""), str(q.get("answer", "")))
            if c:
                noise.append((c, src))
                questions.append({"question": q.get("question", ""),
                                  "gold": str(q.get("answer", "") or ""),
                                  "evidence": str(q.get("evidence", "") or "")})
        cands = [(t, s, "clean") for t, s in clean] + \
                [(t, s, "noise") for t, s in noise]
        admitted = []
        for txt, src, kind in cands:
            score = fact_grounding_score(None, src[:_SRC_CAP], txt)
            admit = score >= a.threshold
            key = "clean" if kind == "clean" else "noise"
            gate[f"{key}_total"] = gate.get(f"{key}_total", 0) + 1
            if kind == "noise" and not admit:
                gate["noise_rejected"] += 1
            if kind == "clean" and admit:
                gate["clean_admitted"] += 1
            if admit:
                admitted.append(txt)
        build["users"].append({
            "uid": f"u{ui}",
            "texts": [t for t, _, _ in cands],       # off + mem0 ingest ALL
            "admitted": admitted,                     # on ingests these
            "questions": questions,
        })

    tmp = Path(tempfile.mkdtemp(prefix="halu_mem0_h2h_"))
    cand_path = tmp / "candidates.json"
    ctx_path = tmp / "mem0_ctx.json"
    json.dump(build, open(cand_path, "w", encoding="utf-8"), ensure_ascii=False)

    # ---- phase B: mem0 bridge (isolated venv, local-only) ------------------
    r = subprocess.run(
        [str(MEM0_PY), str(REPO / "benchmark" / "halumem_mem0_bridge.py"),
         "--candidates", str(cand_path), "--out", str(ctx_path), "--k", str(a.k)],
        capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise SystemExit(f"mem0 bridge failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    mem0_ctx = json.load(open(ctx_path, encoding="utf-8"))
    mem0_by_uid = {u["uid"]: {q["question"]: q["ctx"] for q in u["questions"]}
                   for u in mem0_ctx["users"]}

    # ---- phase C: answer + judge, three arms, SAME answerer/judge ----------
    arms = {arm: {"CORRECT": 0, "HALLUCINATION": 0, "OMISSION": 0, "ERROR": 0}
            for arm in ("off", "on", "mem0")}
    pairs = {("off", "on"): {"b": 0, "c": 0},
             ("mem0", "on"): {"b": 0, "c": 0}}
    for ui, u in enumerate(build["users"]):
        sm_off = SemanticMemory(db_path=tmp / f"off{ui}" / "semantic.db")
        sm_on = SemanticMemory(db_path=tmp / f"on{ui}" / "semantic.db")
        for txt in u["texts"]:
            sm_off.store(Fact(proposition=txt, topic=f"halu/{ui}", confidence=0.8),
                         embed="sync")
        for txt in u["admitted"]:
            sm_on.store(Fact(proposition=txt, topic=f"halu/{ui}", confidence=0.8),
                        embed="sync")
        for q in u["questions"]:
            question, gold, key = q["question"], q["gold"], q["evidence"]
            verdicts = {}
            for arm in ("off", "on", "mem0"):
                try:
                    if arm == "mem0":
                        ctx = mem0_by_uid.get(u["uid"], {}).get(question, [])
                    else:
                        sm = sm_off if arm == "off" else sm_on
                        hits = sm.recall(question, k=a.k)
                        ctx = [getattr(fo, "proposition", "") for fo, _ in hits]
                    pred = answer_question(llm, question, ctx)
                    v = _classify(llm, question, gold, key, pred)
                except Exception as exc:  # noqa: BLE001
                    v = f"ERROR:{str(exc)[:50]}"
                bucket = "ERROR" if v.startswith("ERROR") else v
                arms[arm][bucket] = arms[arm].get(bucket, 0) + 1
                verdicts[arm] = bucket
            for (x, y), d in pairs.items():
                if verdicts.get(x) != "ERROR" and verdicts.get(y) != "ERROR":
                    xh = verdicts[x] == "HALLUCINATION"
                    yh = verdicts[y] == "HALLUCINATION"
                    if xh and not yh:
                        d["b"] += 1
                    elif yh and not xh:
                        d["c"] += 1

    def rates(c):
        n = c["CORRECT"] + c["HALLUCINATION"] + c["OMISSION"]
        return {"counts": c, "n": n,
                "correct": round(c["CORRECT"] / n, 4) if n else 0.0,
                "hallucination": round(c["HALLUCINATION"] / n, 4) if n else 0.0,
                "omission": round(c["OMISSION"] / n, 4) if n else 0.0,
                "hallucination_ci95": wilson(c["HALLUCINATION"], n)}

    res = {"users": len(users), "clean": a.clean, "noise": a.noise,
           "seed": a.seed, "threshold": a.threshold, "k": a.k,
           "gate_admission": {
               **gate,
               "noise_rejection_rate": round(gate["noise_rejected"] / gate["noise_total"], 4) if gate["noise_total"] else None,
               "clean_admission_rate": round(gate["clean_admitted"] / gate["clean_total"], 4) if gate["clean_total"] else None},
           "arms": {arm: rates(c) for arm, c in arms.items()},
           "mcnemar": {f"{x}_vs_{y}": {**d, "p_value_exact": mcnemar_exact(d["b"], d["c"])}
                       for (x, y), d in pairs.items()},
           "honesty": ["C structurally low in ALL arms (sampled memory often lacks the "
                       "true answer): poisoning-resistance measure, NOT answer-correctness",
                       "confabs regenerated this run: pair WITHIN this run only",
                       "same answerer+judge for all arms; mem0 retrieval = its own store"]}
    out = a.out or str(REPO / "benchmark" / "results" /
                       ("halumem_mem0_real_smoke.json" if a.smoke else "halumem_mem0_real.json"))
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ("gate_admission", "arms", "mcnemar")}, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
