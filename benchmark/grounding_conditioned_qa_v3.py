"""Study 3c — the FIXED provenance-conditioning experiment (answers the adversarial
review of Study 3, which was found `inflated`). Every valid critique is addressed:

* HARD distractor class: each case has an INFERENCE distractor (50-band) — a real entity
  or number FROM the source placed in the WRONG role (e.g. source says "Redis as cache"
  -> distractor "Redis is the primary store"). NOT a trivial 0-band contradiction. A
  CONTRADICTION distractor is kept only as an easy control.
* FAIR baseline: the `source` arm answers from the real SOURCE passage (which CAN
  disambiguate), so we measure the grounding TAG's lift over honest evidence — not over
  an unwinnable two-contradictions task.
* The KEY ablation: the `wrongtag` arm SWAPS the tags (high grounding on the distractor,
  low on the true fact). If the model follows the tag into error, conditioning genuinely
  drives behavior; if it ignores the wrong tag and still answers correctly, the tag adds
  nothing and the model was self-detecting all along.
* Bigger n + Wilson CIs + gate separation reported per distractor class.

Arms (all on the INFERENCE distractor unless noted):
  source     — answer from the SOURCE passage (no facts, no tags)            [fair baseline]
  factsflat  — [true, distractor], no tags                                   [old unfair ref]
  grounded   — [true(score), distractor(score)] tagged                       [the claim]
  wrongtag   — [true(LOW), distractor(HIGH)] tags swapped                    [obedience test]
  contra_grounded / contra_source — same on the CONTRADICTION distractor     [easy control]

Serial claude -p. ~195 calls @ n=15.
    python -m benchmark.grounding_conditioned_qa_v3 --out benchmark/results/grounding_conditioned_qa_v3.json
"""
from __future__ import annotations

import argparse
import json
import math
import random

# (source, question, gold, true_fact, contradiction_distractor, inference_distractor)
# inference_distractor = a real token from the source in the WRONG role (the 50-band).
CASES = [
    ("We moved off the old store last quarter; the service now uses PostgreSQL for the "
     "primary datastore, with Redis only as a cache layer.",
     "Which database is the service's primary store?", "PostgreSQL",
     "The primary store is PostgreSQL.", "The primary store is MongoDB.",
     "The primary store is Redis."),
    ("The team shipped v2.1 to staging on Friday; production is still on v1.9 pending the "
     "security sign-off.",
     "Which version is running in production?", "v1.9",
     "Production runs v1.9.", "Production runs v3.0.", "Production runs v2.1."),
    ("Maria leads the backend guild; she delegated the auth rewrite to Sofia, who finished "
     "it last sprint.",
     "Who actually did the auth rewrite?", "Sofia",
     "Sofia did the auth rewrite.", "Tom did the auth rewrite.",
     "Maria did the auth rewrite."),
    ("The conference is in Berlin this year; the gala dinner, though, is hosted at a venue "
     "in Potsdam just outside the city.",
     "Which city is the conference held in?", "Berlin",
     "The conference is in Berlin.", "The conference is in Munich.",
     "The conference is in Potsdam."),
    ("The drug is taken 200 mg twice daily with food; the loading dose on day one is 400 mg.",
     "What is the maintenance dose?", "200 mg twice daily",
     "The maintenance dose is 200 mg twice daily.", "The maintenance dose is 50 mg.",
     "The maintenance dose is 400 mg."),
    ("Our HQ is in Lisbon; the largest office by headcount is actually the Madrid sales hub.",
     "Where is the company headquartered?", "Lisbon",
     "The company is headquartered in Lisbon.", "The company is headquartered in Paris.",
     "The company is headquartered in Madrid."),
    ("The satellite's design life is 7 years, though the mission was extended and it "
     "actually operated for 12.",
     "What was the satellite's design life?", "7 years",
     "The design life is 7 years.", "The design life is 2 years.",
     "The design life is 12 years."),
    ("Payment is net-30 for established clients; new clients pay net-15 for their first "
     "three invoices.",
     "What are the payment terms for established clients?", "net-30",
     "Established clients pay net-30.", "Established clients pay net-60.",
     "Established clients pay net-15."),
    ("The car comes standard with the 2.0L engine; the 3.0L is a paid upgrade few buyers "
     "choose.",
     "What is the standard engine?", "2.0L",
     "The standard engine is 2.0L.", "The standard engine is 1.4L.",
     "The standard engine is 3.0L."),
    ("Daniel is allergic to shellfish; his brother Marco is the vegan in the family.",
     "What is Daniel's dietary restriction?", "no shellfish",
     "Daniel cannot eat shellfish.", "Daniel cannot eat nuts.",
     "Daniel is vegan."),
    ("The warranty covers parts for 3 years and labor for 1 year.",
     "How long is the labor warranty?", "1 year",
     "The labor warranty is 1 year.", "The labor warranty is 5 years.",
     "The labor warranty is 3 years."),
    ("The API rate limit is 100 req/min on the free tier; paid tiers get 1000 req/min.",
     "What is the free-tier rate limit?", "100 req/min",
     "The free tier allows 100 req/min.", "The free tier allows 10 req/min.",
     "The free tier allows 1000 req/min."),
    ("The bridge was designed in 1985 but, after funding delays, only completed in 1998.",
     "What year was the bridge completed?", "1998",
     "The bridge was completed in 1998.", "The bridge was completed in 2010.",
     "The bridge was completed in 1985."),
    ("Priya is the lead engineer; Tom, the PM, owns the roadmap.",
     "Who is the lead engineer?", "Priya",
     "The lead engineer is Priya.", "The lead engineer is Raj.",
     "The lead engineer is Tom."),
    ("The device runs on 12V DC; the wall adapter converts from 240V AC mains.",
     "What is the device's operating voltage?", "12V",
     "The device runs on 12 volts.", "The device runs on 5 volts.",
     "The device runs on 240 volts."),
]

_SOURCE_SYSTEM = (
    "Answer the question using ONLY the passage. Be concise: just the answer. "
    "If the passage does not state the answer, reply exactly: NO ANSWER."
)
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


def _answer(llm, system, lines, question):
    body = "\n".join(lines)
    label = "Passage" if system is _SOURCE_SYSTEM else "Facts"
    user = f"{label}:\n{body}\n\nQuestion: {question}"
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


def _cho(counts):
    n = sum(counts.values()) - counts["ERROR"]
    return {"counts": counts, "n": n,
            "correct": round(counts["CORRECT"] / n, 4) if n else 0.0,
            "hallucination": round(counts["HALLUCINATION"] / n, 4) if n else 0.0,
            "omission": round(counts["OMISSION"] / n, 4) if n else 0.0,
            "hallucination_ci95": wilson(counts["HALLUCINATION"], n),
            "correct_ci95": wilson(counts["CORRECT"], n)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    from benchmark.qa_runner import LeanClaudeCLILLM
    from verimem.grounding_gate import fact_grounding_score

    llm = LeanClaudeCLILLM(model=a.model, timeout_s=90)
    cases = CASES[: a.limit] if a.limit else CASES
    rng = random.Random(a.seed)

    # Phase 1 — gate scores (source ⊢ fact) for true / contradiction / inference.
    scored = []
    s_true, s_contra, s_infer = [], [], []
    for src, q, gold, true_f, contra, infer in cases:
        st = fact_grounding_score(llm, src, true_f)
        sc = fact_grounding_score(llm, src, contra)
        si = fact_grounding_score(llm, src, infer)
        s_true.append(st); s_contra.append(sc); s_infer.append(si)
        scored.append((src, q, gold, true_f, contra, infer, st, sc, si))

    sep = {
        "true_mean": round(sum(s_true) / len(s_true), 2),
        "contradiction_mean": round(sum(s_contra) / len(s_contra), 2),
        "inference_mean": round(sum(s_infer) / len(s_infer), 2),
        "roc_auc_true_vs_contradiction": roc_auc(s_true, s_contra),
        "roc_auc_true_vs_inference": roc_auc(s_true, s_infer),
        "true_scores": s_true, "contradiction_scores": s_contra, "inference_scores": s_infer,
    }

    def tag(fact, score):
        return f"[grounding {int(round(score))}/100] {fact}"

    arms = {k: {"CORRECT": 0, "HALLUCINATION": 0, "OMISSION": 0, "ERROR": 0}
            for k in ("source", "factsflat", "grounded", "wrongtag",
                      "contra_source", "contra_grounded")}
    # obedience: in wrongtag, did the model pick the HIGH-tagged (false) distractor?
    obey = {"followed_wrong_tag": 0, "resisted": 0, "abstained": 0, "n": 0}

    for src, q, gold, true_f, contra, infer, st, sc, si in scored:
        # --- INFERENCE distractor (the hard, real class) ---
        arms["source"][_judge(llm, q, gold, _answer(llm, _SOURCE_SYSTEM, [src], q))] += 1

        ff = [true_f, infer]; rng.shuffle(ff)
        arms["factsflat"][_judge(llm, q, gold, _answer(llm, _FLAT_SYSTEM, ff, q))] += 1

        gl = [tag(true_f, st), tag(infer, si)]; rng.shuffle(gl)
        arms["grounded"][_judge(llm, q, gold, _answer(llm, _GROUNDED_SYSTEM, gl, q))] += 1

        # wrong-tag: swap — true gets the distractor's (low) score, distractor gets true's (high)
        wl = [tag(true_f, si), tag(infer, st)]; rng.shuffle(wl)
        wpred = _answer(llm, _GROUNDED_SYSTEM, wl, q)
        wv = _judge(llm, q, gold, wpred)
        arms["wrongtag"][wv] += 1
        if wv != "ERROR":
            obey["n"] += 1
            if wv == "CORRECT":
                obey["resisted"] += 1
            elif wv == "OMISSION":
                obey["abstained"] += 1
            else:
                obey["followed_wrong_tag"] += 1

        # --- CONTRADICTION distractor (easy control) ---
        arms["contra_source"][_judge(llm, q, gold, _answer(llm, _SOURCE_SYSTEM, [src], q))] += 1
        cg = [tag(true_f, st), tag(contra, sc)]; rng.shuffle(cg)
        arms["contra_grounded"][_judge(llm, q, gold, _answer(llm, _GROUNDED_SYSTEM, cg, q))] += 1

    res = {
        "n_cases": len(cases),
        "gate_separation": sep,
        "arms": {k: _cho(v) for k, v in arms.items()},
        "wrongtag_obedience": obey,
    }
    # the honest headline: grounded vs the FAIR source baseline, on inference distractors
    res["grounded_vs_source_hallucination_delta"] = round(
        res["arms"]["source"]["hallucination"] - res["arms"]["grounded"]["hallucination"], 4)
    print(json.dumps(res, indent=2))
    if a.out:
        from pathlib import Path
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
