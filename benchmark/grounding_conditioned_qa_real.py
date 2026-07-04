"""Provenance-conditioned answering — REAL-gate proof (closes the idealized caveat).

The idealized proof (grounding_conditioned_qa.py) HAND-SET the grounding scores 90/12 and
showed that, GIVEN perfect separation, conditioning kills hallucination (0.33 -> 0.00).
That proved the second half (conditioning works) but assumed the first half (the gate
separates true from distractor). This harness proves BOTH end-to-end:

  1. Each case has a realistic multi-sentence SOURCE (a conversational memory entry), a
     TRUE fact the source states, and a plausible DISTRACTOR the source does NOT state.
  2. The write-time grounding score for each fact is COMPUTED by the real gate
     (engram.grounding_gate.fact_grounding_score, source⊢fact) — not hand-set.
  3. We report the gate's SEPARATION (mean true vs mean distractor, ROC-AUC) AND the
     end-to-end C/H/O for flat vs grounded answering using those computed scores.

If the gate fails to separate on real text, this will show it (honest falsifiability).
Serial claude -p. ~6 calls/case (2 grounding + 2 answer + 2 judge).

    python -m benchmark.grounding_conditioned_qa_real --out benchmark/results/grounding_conditioned_qa_real.json
"""
from __future__ import annotations

import argparse
import json
import math
import random

# (source passage, question, gold, TRUE fact [source states it], DISTRACTOR [source does NOT])
CASES = [
    ("We finally got Maria's lab results back from the clinic this week. The hematology "
     "panel came back clean except they flagged her blood type as AB negative, which the "
     "nurse said is rare. She's cleared for the procedure.",
     "What is Maria's blood type?", "AB negative",
     "Maria's blood type is AB negative.", "Maria's blood type is O positive."),
    ("The organizing committee moved a lot of pieces around in 2019. After Vienna fell "
     "through over a venue dispute, they relocated the summit to Geneva, where the final "
     "sessions were held in late autumn.",
     "Which city did the 2019 summit take place in?", "Geneva",
     "The 2019 summit was held in Geneva.", "The 2019 summit was held in Vienna."),
    ("Pharmacist updated the chart today. The label says do not exceed 200 mg per day, and "
     "she underlined that going above it risks liver strain. The patient was on 150 mg.",
     "What is the maximum daily dose?", "200 mg per day",
     "The maximum dose is 200 mg per day.", "The maximum dose is 500 mg per day."),
    ("Standup ran long. Tom presented the QA timeline, but the architecture call is owned "
     "by Priya Anand, who's the lead engineer on the platform team and signs off on the "
     "design docs.",
     "Who is the project's lead engineer?", "Priya Anand",
     "The lead engineer is Priya Anand.", "The lead engineer is Tom Becker."),
    ("The heritage society put up a plaque on the river walk. It notes the original 1888 "
     "design competition, the funding delays, and that the bridge was finally completed in "
     "1998 after a decade of work.",
     "What year was the bridge completed?", "1998",
     "The bridge was completed in 1998.", "The bridge was completed in 1888."),
    ("Hardware review went fine. The spec sheet confirms the device operates at 12 volts; "
     "the team briefly considered a 24-volt variant last year but dropped it for cost.",
     "What is the device's operating voltage?", "12 volts",
     "The device operates at 12 volts.", "The device operates at 24 volts."),
    ("Catering form for the offsite. Daniel noted he cannot eat shellfish because of a "
     "serious allergy; he's otherwise easy, eats most things, no other restrictions.",
     "What is Daniel's dietary restriction?", "no shellfish",
     "Daniel cannot eat shellfish.", "Daniel is vegan."),
    ("Migration retro. We moved off the old store last quarter; the service now uses "
     "PostgreSQL for the primary datastore, with Redis only as a cache layer.",
     "Which database does the service use as its primary store?", "PostgreSQL",
     "The service uses PostgreSQL.", "The service uses MongoDB."),
    ("Customer read the fine print. The warranty card states a 3-year warranty on parts "
     "and labor, registration required within 30 days of purchase.",
     "What is the warranty period?", "3 years",
     "The warranty period is 3 years.", "The warranty period is 1 year."),
    ("Investor deck, company overview slide. Founded in 2015, the company is headquartered "
     "in Lisbon, with satellite offices in Madrid and Berlin for sales.",
     "What is the company's headquarters city?", "Lisbon",
     "The company is headquartered in Lisbon.", "The company is headquartered in Madrid."),
    ("Onboarding notes for the new account. The user asked us to reach them by email only — "
     "they don't answer unknown phone numbers and prefer everything in writing.",
     "What is the user's preferred contact method?", "email",
     "The user prefers to be contacted by email.", "The user prefers phone calls."),
    ("Mission briefing. The satellite sits in low Earth orbit with an orbital period of "
     "about 90 minutes, so it passes over the ground station roughly every hour and a half.",
     "What is the satellite's orbital period?", "90 minutes",
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


def roc_auc(pos, neg):
    """ROC-AUC of true (pos) vs distractor (neg) grounding scores — Mann-Whitney."""
    if not pos or not neg:
        return None
    wins = ties = 0
    for p in pos:
        for q in neg:
            if p > q:
                wins += 1
            elif p == q:
                ties += 1
    return round((wins + 0.5 * ties) / (len(pos) * len(neg)), 4)


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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--limit", type=int, default=0, help="run only first N cases (0=all)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    from benchmark.qa_runner import LeanClaudeCLILLM
    from engram.grounding_gate import fact_grounding_score

    llm = LeanClaudeCLILLM(model=a.model, timeout_s=90)
    cases = CASES[: a.limit] if a.limit else CASES
    rng = random.Random(a.seed)

    # Phase 1 — COMPUTE grounding via the real gate (source ⊢ fact).
    scored = []
    true_scores, distractor_scores = [], []
    for src, q, gold, true_f, distractor in cases:
        s_true = fact_grounding_score(llm, src, true_f)
        s_dist = fact_grounding_score(llm, src, distractor)
        true_scores.append(s_true)
        distractor_scores.append(s_dist)
        scored.append((src, q, gold, true_f, distractor, s_true, s_dist))

    sep = {
        "true_mean": round(sum(true_scores) / len(true_scores), 2),
        "distractor_mean": round(sum(distractor_scores) / len(distractor_scores), 2),
        "roc_auc": roc_auc(true_scores, distractor_scores),
        "true_scores": true_scores,
        "distractor_scores": distractor_scores,
    }

    # Phase 2 — answer flat vs grounded using the COMPUTED scores.
    def run_arm(grounded):
        cho = {"CORRECT": 0, "HALLUCINATION": 0, "OMISSION": 0, "ERROR": 0}
        for _src, q, gold, true_f, distractor, s_true, s_dist in scored:
            if grounded:
                lines = [f"[grounding {int(round(s_true))}/100] {true_f}",
                         f"[grounding {int(round(s_dist))}/100] {distractor}"]
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

    res = {
        "n_cases": len(cases),
        "gate_separation": sep,
        "flat": run_arm(False),
        "grounded": run_arm(True),
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
