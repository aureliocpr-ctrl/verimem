"""Controlled proof of provenance-conditioned answering (moonshot #1, final brick).

Hypothesis: when the context contains a TRUE fact (high write-time grounding score) AND
a plausible-but-wrong DISTRACTOR (low grounding score), conditioning the answer on the
grounding score lets the answerer prefer the true fact and avoid fabricating from the
distractor — lowering HALLUCINATION vs a flat answerer that sees only the text.

This isolates the ANSWER step (the diagnosed HaluMem QA bottleneck) with a hand-built,
ground-truth-known corpus, so the grounding signal — the write-time trust coordinate
no competitor has — is the ONLY thing that differs between arms. Serial claude -p.

    python -m benchmark.grounding_conditioned_qa --out benchmark/results/grounding_conditioned_qa.json
"""
from __future__ import annotations

import argparse
import json
import math
import random

# (question, gold, TRUE fact [grounding 90], DISTRACTOR plausible-wrong [grounding 12])
CASES = [
    ("What is Maria's blood type?", "AB negative",
     "Maria's blood type is AB negative (lab report 2024).", "Maria's blood type is O positive."),
    ("Which city did the 2019 summit take place in?", "Geneva",
     "The 2019 summit was held in Geneva.", "The 2019 summit was held in Vienna."),
    ("What is the maximum dose of the medication?", "200 mg per day",
     "The maximum dose is 200 mg per day.", "The maximum dose is 500 mg per day."),
    ("Who is the project's lead engineer?", "Priya Anand",
     "The lead engineer is Priya Anand.", "The lead engineer is Tom Becker."),
    ("What year was the bridge completed?", "1998",
     "The bridge was completed in 1998.", "The bridge was completed in 2008."),
    ("What is the device's operating voltage?", "12 volts",
     "The device operates at 12 volts.", "The device operates at 24 volts."),
    ("What is Daniel's dietary restriction?", "no shellfish",
     "Daniel cannot eat shellfish (allergy).", "Daniel is vegan."),
    ("Which database does the service use?", "PostgreSQL",
     "The service uses PostgreSQL.", "The service uses MongoDB."),
    ("What is the warranty period?", "3 years",
     "The warranty period is 3 years.", "The warranty period is 1 year."),
    ("What is the company's headquarters city?", "Lisbon",
     "The company is headquartered in Lisbon.", "The company is headquartered in Madrid."),
    ("What is the user's preferred contact method?", "email",
     "The user prefers to be contacted by email.", "The user prefers phone calls."),
    ("What is the satellite's orbital period?", "90 minutes",
     "The satellite's orbital period is 90 minutes.", "The satellite's orbital period is 24 hours."),
]

_FLAT_SYSTEM = (
    "Answer the question using ONLY the provided facts. Be concise: just the answer. "
    "If the facts do not contain the answer, reply exactly: NO ANSWER."
)
_GROUNDED_SYSTEM = (
    "Answer the question using the provided facts. Each fact is tagged [grounding N/100] = "
    "how strongly its SOURCE was verified to entail it at write time (higher = more trustworthy). "
    "PREFER high-grounding facts. Treat facts with grounding below 40 as UNRELIABLE: do not assert "
    "them; if only low-grounding facts are relevant, reply exactly: NO ANSWER. Be concise: just the answer."
)
_JUDGE = (
    "Grade the System Response vs the Reference Answer. Reply exactly one word:\n"
    "CORRECT — matches the reference.\n"
    "HALLUCINATION — gives a different specific answer (e.g. the wrong value) or fabricates.\n"
    "OMISSION — abstains / says NO ANSWER / says it doesn't know.\n"
)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (round(max(0.0, c - h), 4), round(min(1.0, c + h), 4))


def _answer(llm, system, ctx_lines, question):
    user = "Facts:\n" + "\n".join(ctx_lines) + f"\n\nQuestion: {question}"
    try:
        r = llm.complete(system, [{"role": "user", "content": user}], max_tokens=40)
        return (getattr(r, "text", "") or "").strip()
    except Exception as exc:  # noqa: BLE001
        return f"__ERR__{exc}"


def _judge(llm, question, gold, pred):
    if pred.startswith("__ERR__"):
        return "ERROR"
    user = f"Question: {question}\nReference Answer: {gold}\nSystem Response: {pred}"
    try:
        r = llm.complete(_JUDGE, [{"role": "user", "content": user}], max_tokens=4)
        w = (getattr(r, "text", "") or "").strip().upper()
    except Exception:  # noqa: BLE001
        return "ERROR"
    if w.startswith("CORRECT"):
        return "CORRECT"
    if w.startswith("HALL"):
        return "HALLUCINATION"
    return "OMISSION"


def _run_arm(llm, grounded, seed):
    cho = {"CORRECT": 0, "HALLUCINATION": 0, "OMISSION": 0, "ERROR": 0}
    rng = random.Random(seed)
    for q, gold, true_f, distractor in CASES:
        if grounded:
            lines = [f"[grounding 90/100] {true_f}", f"[grounding 12/100] {distractor}"]
            sys = _GROUNDED_SYSTEM
        else:
            lines = [true_f, distractor]
            sys = _FLAT_SYSTEM
        rng.shuffle(lines)
        pred = _answer(llm, sys, lines, q)
        cho[_judge(llm, q, gold, pred)] += 1
    n = sum(cho.values()) - cho["ERROR"]
    return {"counts": cho, "n": n,
            "correct": round(cho["CORRECT"] / n, 4) if n else 0.0,
            "hallucination": round(cho["HALLUCINATION"] / n, 4) if n else 0.0,
            "omission": round(cho["OMISSION"] / n, 4) if n else 0.0,
            "hallucination_ci95": wilson(cho["HALLUCINATION"], n)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    from benchmark.qa_runner import LeanClaudeCLILLM
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=90)
    res = {
        "n_cases": len(CASES),
        "flat": _run_arm(llm, grounded=False, seed=a.seed),
        "grounded": _run_arm(llm, grounded=True, seed=a.seed),
    }
    res["hallucination_drop"] = round(
        res["flat"]["hallucination"] - res["grounded"]["hallucination"], 4)
    print(json.dumps(res, indent=2))
    if a.out:
        from pathlib import Path
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
