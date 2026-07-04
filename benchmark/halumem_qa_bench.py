"""HaluMem QA-hallucination, the official-protocol slice that is Engram's home turf.

HaluMem (arXiv 2511.03506) scores QA as Correct / Hallucination / Omission (the C/H/O
triple). Engram's anti-confab thesis predicts a LOW Hallucination rate (it abstains /
omits rather than fabricate) — the trade a memory system SHOULD make. This isolates the
QA/answer step: ingest the REFERENCE memory points into Engram, then for each question
retrieve→answer (strict + dates) and LLM-judge C/H/O with the HaluMem-style rubric.

SERIAL claude -p (O5 subscription, no external key). Per-question try/except so a
throttle/timeout records an error and never crashes the run.

    python -m benchmark.halumem_qa_bench --users 4 --q-per-user 15 --seed 7 \
        --out benchmark/results/halumem_qa_cho.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import tempfile
from pathlib import Path

_TRUE = ("system", "secondary", "primary")

_CHO_SYSTEM = (
    "You grade a memory system's ANSWER on the HaluMem rubric. Using ONLY the Reference "
    "Answer and the Key Memory Points, classify the System Response as exactly one word:\n"
    "CORRECT — semantically equivalent to the reference, no contradiction. IMPORTANT: if the "
    "Reference Answer says the information is unknown / not provided / cannot be determined, then "
    "a System Response that abstains, says 'NO ANSWER', or says it does not know IS CORRECT "
    "(correctly refusing to answer an unanswerable question).\n"
    "HALLUCINATION — contradicts the reference, or fabricates a specific answer to a question whose "
    "reference says unknown/not-provided.\n"
    "OMISSION — the reference HAS a concrete answer but the system abstains or gives incomplete / "
    "missing information.\n"
    "Reply with exactly one word: CORRECT, HALLUCINATION, or OMISSION."
)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (round(max(0.0, c - h), 4), round(min(1.0, c + h), 4))


def _classify(llm, question, gold, key_points, pred):
    # NOTE: do NOT short-circuit an empty/abstaining pred to OMISSION — many HaluMem
    # questions are UNANSWERABLE (gold = "unknown / not provided"), where abstaining is
    # CORRECT (the anti-confab moat). The judge decides using the reference answer.
    pred_shown = pred if (pred and pred.strip()) else "NO ANSWER (system abstained)"
    user = (f"QUESTION: {question}\nReference Answer: {gold}\nKey Memory Points: {key_points}\n"
            f"System Response: {pred_shown}")
    try:
        resp = llm.complete(_CHO_SYSTEM, [{"role": "user", "content": user}], max_tokens=4)
        w = (getattr(resp, "text", "") or "").strip().upper()
    except Exception as exc:  # noqa: BLE001
        return f"ERROR:{str(exc)[:60]}"
    if w.startswith("CORRECT"):
        return "CORRECT"
    if w.startswith("HALL"):
        return "HALLUCINATION"
    return "OMISSION"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--users", type=int, default=4)
    ap.add_argument("--q-per-user", type=int, default=15)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--with-interference", action="store_true",
                    help="also ingest interference memory points (no perfect gate)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    os.environ.setdefault("ENGRAM_QA_DATES", "1")

    from benchmark.qa_eval import answer_question
    from benchmark.qa_runner import LeanClaudeCLILLM
    from engram.semantic import Fact, SemanticMemory

    rng = random.Random(a.seed)
    users = []
    with open(a.jsonl, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                users.append(json.loads(line))
    rng.shuffle(users)
    users = users[: a.users]
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=90)

    cho = {"CORRECT": 0, "HALLUCINATION": 0, "OMISSION": 0, "ERROR": 0}
    n_q = 0
    for ui, u in enumerate(users):
        tmp = Path(tempfile.mkdtemp(prefix=f"halu_qa_{ui}_"))
        sm = SemanticMemory(db_path=tmp / "semantic" / "semantic.db")
        qs = []
        for s in u.get("sessions", []):
            for mp in s.get("memory_points", []):
                src = str(mp.get("memory_source", "")).lower()
                txt = (mp.get("memory_content") or "").strip()
                if not txt:
                    continue
                if src in _TRUE or (a.with_interference and src == "interference"):
                    try:
                        sm.store(Fact(proposition=txt, topic=f"halu/{ui}",
                                      confidence=0.8), embed="sync")
                    except Exception:  # noqa: BLE001
                        pass
            for q in s.get("questions", []) or []:
                qs.append(q)
        rng.shuffle(qs)
        for q in qs[: a.q_per_user]:
            question = q.get("question", "")
            gold = str(q.get("answer", "") or "")
            key = str(q.get("evidence", "") or "")
            try:
                hits = sm.recall(question, k=a.k)
                ctx = [getattr(fobj, "proposition", "") for fobj, _ in hits]
                pred = answer_question(llm, question, ctx)
                verdict = _classify(llm, question, gold, key, pred)
            except Exception as exc:  # noqa: BLE001
                verdict = f"ERROR:{str(exc)[:60]}"
            bucket = "ERROR" if verdict.startswith("ERROR") else verdict
            cho[bucket] = cho.get(bucket, 0) + 1
            n_q += 1

    scored = cho["CORRECT"] + cho["HALLUCINATION"] + cho["OMISSION"]
    res = {
        "n_questions": n_q, "n_scored": scored, "n_errors": cho["ERROR"],
        "users": len(users), "with_interference": a.with_interference,
        "counts": cho,
        "correct_rate": round(cho["CORRECT"] / scored, 4) if scored else 0.0,
        "hallucination_rate": round(cho["HALLUCINATION"] / scored, 4) if scored else 0.0,
        "omission_rate": round(cho["OMISSION"] / scored, 4) if scored else 0.0,
        "hallucination_ci95": wilson(cho["HALLUCINATION"], scored),
    }
    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
