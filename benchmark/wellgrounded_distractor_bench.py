"""CASE-B bench — the WELL-GROUNDED distractor (the pinned limit of Memory.answer).

Case A (mal-extracted distractor, grounding ~0) is already covered twice: the
write-gate quarantines it at write time and grounding-conditioning catches it at
answer time (grounding_conditioned_qa_real: 0.42 -> 0.00). The OPEN gap — pinned
honestly in ``Memory.answer``'s docstring — is CASE B: a distractor that is
WELL-grounded in its own source (someone really said it) but wrong for the user
NOW (superseded, hearsay, unverified). Grounding cannot separate it; only the
metadata the product already stores can: ``asserted_at`` (recency), ``source``,
``status`` (verified > unverified).

Each case has TWO realistic dialogues: one grounds the TRUE fact, one grounds the
DISTRACTOR. Phase 1 PROVES both facts are well-grounded (real gate, source⊢fact —
if the distractor scores low the case is mislabeled and reported as such). Then:

  arm FLAT    — both facts, bare. Baseline: how often the wrong one is served.
  arm CURRENT — Memory.answer() today = FLAT + local-CE post-verify. Costs no
                LLM call: we verify with the LOCAL CE that the flat answer is
                entailed by the fact it came from (score >= threshold ⇒ the CE
                would NOT have blocked it). Expected ≈ FLAT — measured, not assumed.
  arm TRUST   — both facts tagged with the REAL per-fact metadata the store has
                ([when | source | status]) + resolution rule in the prompt:
                verified > unverified, recent > old; unresolvable ⇒ NO ANSWER.

12 resolvable cases (gold = the true value) + 2 UNRESOLVABLE (same status, same
day, opposing claims — gold behavior = abstain; measures that TRUST does not
fabricate confidence). ~6 LLM calls/case (2 grounding + 2 answer + 2 judge).

    python -m benchmark.wellgrounded_distractor_bench --model claude-sonnet-5 \
        --out benchmark/results/wellgrounded_distractor_2026-07-16.json
"""
from __future__ import annotations

import argparse
import json

from benchmark.grounding_conditioned_qa_real import _answer, _judge, wilson

_FLAT_SYSTEM = (
    "Answer the question using ONLY the provided facts. Be concise: just the "
    "answer, no preamble. If the facts do not contain the answer, reply exactly: NO ANSWER."
)

_TRUST_SYSTEM = (
    "Answer the question using ONLY the provided facts. Each fact is tagged "
    "[when | source | status]. If facts conflict, resolve by metadata: a "
    "'verified' fact beats an unverified one; a more recent fact beats an older "
    "one; a first-hand source beats hearsay. If the conflict cannot be resolved "
    "by the metadata, reply exactly: NO ANSWER. Be concise: just the answer."
)
# NB misurato 2026-07-16: la versione VERBOSA della tie-rule ("you MUST reply…
# never pick one") produce descrizioni del conflitto invece del secco NO ANSWER;
# questa formulazione asciutta ha astenuto 2/2 sui conflitti irrisolvibili.

# (case_id, kind, src_true, src_false, question, gold,
#  fact_true, meta_true, fact_false, meta_false)
# kind: B1 recency (true is newer) · B2 source trust · B3 status (verified beats claim)
# Every fact IS stated by its own dialogue — phase 1 proves it with the real gate.
CASES = [
    # ---- B1: superseded by a newer statement (recency resolves) ----
    ("b1_office", "B1",
     "Quick update from the all-hands this morning: the move is complete. As of "
     "this week our main office is in Turin, on Via Roma 41. Badge access works "
     "from Monday.",
     "Welcome aboard! A few practical things: our main office is in Milan, Via "
     "Dante 12, third floor. The kitchen is next to the elevators and Friday "
     "demos happen in the big room.",
     "In which city is the main office?", "Turin",
     "The main office is in Turin.", {"when": "2026-07-10", "source": "all-hands meeting", "status": "verified"},
     "The main office is in Milan.", {"when": "2025-03-02", "source": "onboarding chat", "status": "model_claim"}),

    ("b1_manager", "B1",
     "Org update: starting today Priya leads the data platform team. Marco moved "
     "to the infra group as principal engineer — please route approvals to Priya.",
     "For anything about the data platform you should ping Marco, he's been the "
     "team lead there for two years and knows every pipeline.",
     "Who leads the data platform team?", "Priya",
     "Priya leads the data platform team.", {"when": "2026-06-28", "source": "org announcement", "status": "verified"},
     "Marco leads the data platform team.", {"when": "2024-11-15", "source": "hallway chat", "status": "model_claim"}),

    ("b1_deadline", "B1",
     "Heads up: the submission deadline moved. The committee confirmed the new "
     "date is October 3rd — the portal closes at midnight CET that day.",
     "Planning note: the submission deadline is September 12th, so let's have "
     "the draft ready two weeks before.",
     "What is the submission deadline?", "October 3rd",
     "The submission deadline is October 3rd.", {"when": "2026-07-01", "source": "committee email", "status": "verified"},
     "The submission deadline is September 12th.", {"when": "2026-05-20", "source": "planning meeting", "status": "model_claim"}),

    ("b1_price", "B1",
     "Pricing page shipped: the Pro plan is now 49 euros a month, annual billing "
     "drops it to 41. The old grandfathered accounts keep their rate one more year.",
     "When we launched, we set the Pro plan at 29 euros a month and honestly it "
     "was underpriced from day one.",
     "How much is the Pro plan per month?", "49 euros",
     "The Pro plan costs 49 euros a month.", {"when": "2026-07-05", "source": "pricing page release", "status": "verified"},
     "The Pro plan costs 29 euros a month.", {"when": "2024-02-10", "source": "launch retrospective", "status": "model_claim"}),

    ("b1_venue", "B1",
     "Final logistics: the workshop was moved out of the university — we "
     "confirmed the civic library's main hall instead, same dates, bigger room.",
     "The workshop will be at the university's engineering building, room E7 — "
     "I booked it this afternoon.",
     "Where is the workshop held?", "the civic library (main hall)",
     "The workshop is held at the civic library's main hall.", {"when": "2026-07-08", "source": "logistics update", "status": "verified"},
     "The workshop is held at the university engineering building.", {"when": "2026-04-14", "source": "early booking note", "status": "model_claim"}),

    # ---- B2: trusted first-hand source vs hearsay ----
    ("b2_birthday", "B2",
     "Ana here — quick correction for the team calendar: my birthday is March "
     "9th, not in April. See you all tomorrow!",
     "I think Ana's birthday is April 2nd, at least that's what someone from her "
     "old team told me last year.",
     "When is Ana's birthday?", "March 9th",
     "Ana's birthday is March 9th.", {"when": "2026-06-30", "source": "Ana (first-hand)", "status": "verified"},
     "Ana's birthday is April 2nd.", {"when": "2026-06-29", "source": "hearsay via former colleague", "status": "model_claim"}),

    ("b2_allergy", "B2",
     "Catering form, from Jonah directly: I'm allergic to peanuts — tree nuts "
     "are fine, just no peanuts anywhere in the dish please.",
     "For the team dinner someone mentioned Jonah can't eat shellfish, so maybe "
     "we should skip the seafood place.",
     "What is Jonah allergic to?", "peanuts",
     "Jonah is allergic to peanuts.", {"when": "2026-07-02", "source": "Jonah (catering form)", "status": "verified"},
     "Jonah is allergic to shellfish.", {"when": "2026-07-01", "source": "secondhand dinner chat", "status": "model_claim"}),

    ("b2_repo", "B2",
     "From the platform team's runbook page: the canonical deployment repo is "
     "'deploy-core' — everything else is a mirror and must not receive pushes.",
     "Pretty sure deployments live in the 'infra-scripts' repo, that's where I "
     "saw the pipeline files once.",
     "Which repo is the canonical deployment repo?", "deploy-core",
     "The canonical deployment repo is 'deploy-core'.", {"when": "2026-06-20", "source": "platform runbook", "status": "verified"},
     "The canonical deployment repo is 'infra-scripts'.", {"when": "2026-06-18", "source": "vague recollection", "status": "model_claim"}),

    ("b2_train", "B2",
     "Official confirmation from the operator's booking system: your train to "
     "the conference departs at 07:42 from platform 6.",
     "A colleague who took the same route last month says the morning train "
     "usually leaves around 08:15.",
     "At what time does the train depart?", "07:42",
     "The train departs at 07:42.", {"when": "2026-07-12", "source": "operator booking system", "status": "verified"},
     "The train departs around 08:15.", {"when": "2026-07-11", "source": "colleague's memory", "status": "model_claim"}),

    # ---- B3: verified record vs unverified claim (status resolves, dates close) ----
    ("b3_dbport", "B3",
     "Checked the running config myself just now: the analytics database listens "
     "on port 5433 — confirmed with a live connection test.",
     "I believe the analytics database is on the default port 5432, that's what "
     "we usually do.",
     "On which port does the analytics database listen?", "5433",
     "The analytics database listens on port 5433.", {"when": "2026-07-14", "source": "live config check", "status": "verified"},
     "The analytics database listens on port 5432.", {"when": "2026-07-13", "source": "assumption in standup", "status": "model_claim"}),

    ("b3_capacity", "B3",
     "Counted at the venue walkthrough with the fire officer: the hall's "
     "certified capacity is 180 seated — it's on the safety certificate.",
     "The event hall should fit about 250 people if I remember the brochure "
     "correctly.",
     "What is the hall's certified seated capacity?", "180",
     "The hall's certified seated capacity is 180.", {"when": "2026-07-09", "source": "safety certificate walkthrough", "status": "verified"},
     "The hall fits about 250 people.", {"when": "2026-07-08", "source": "brochure memory", "status": "model_claim"}),

    ("b3_version", "B3",
     "Release engineer here: production runs framework version 3.8.2 — verified "
     "on the version endpoint of all six nodes this morning.",
     "Production should be on framework 4.0 by now, the upgrade was planned for "
     "last quarter.",
     "Which framework version runs in production?", "3.8.2",
     "Production runs framework version 3.8.2.", {"when": "2026-07-15", "source": "version endpoint check", "status": "verified"},
     "Production runs framework version 4.0.", {"when": "2026-07-14", "source": "planning assumption", "status": "model_claim"}),

    # ---- UNRESOLVABLE: same status, same day, opposing first-hand claims.
    #      Honest behavior = abstain (gold_behavior = OMISSION). ----
    ("u1_room", "U",
     "Sam: the retro is in room Alpha tomorrow, I booked it myself.",
     "Lena: the retro is in room Delta tomorrow, I booked it myself.",
     "In which room is the retro tomorrow?", "NO ANSWER",
     "The retro is in room Alpha.", {"when": "2026-07-15", "source": "Sam (first-hand)", "status": "model_claim"},
     "The retro is in room Delta.", {"when": "2026-07-15", "source": "Lena (first-hand)", "status": "model_claim"}),

    ("u2_owner", "U",
     "Nadia: I'm the on-call owner for the payments service this week.",
     "Tom: I'm the on-call owner for the payments service this week.",
     "Who owns on-call for the payments service this week?", "NO ANSWER",
     "Nadia owns on-call for payments this week.", {"when": "2026-07-14", "source": "Nadia (first-hand)", "status": "model_claim"},
     "Tom owns on-call for payments this week.", {"when": "2026-07-14", "source": "Tom (first-hand)", "status": "model_claim"}),
]


def _meta_line(fact: str, meta: dict) -> str:
    return f"[{meta['when']} | {meta['source']} | {meta['status']}] {fact}"


def _bucket(counts: dict, verdict: str) -> None:
    counts[verdict] = counts.get(verdict, 0) + 1


def _rates(c: dict) -> dict:
    n = sum(v for k, v in c.items() if k != "ERROR")
    h = c.get("HALLUCINATION", 0)
    return {"counts": c, "n": n,
            "correct": round(c.get("CORRECT", 0) / n, 4) if n else 0.0,
            "hallucination": round(h / n, 4) if n else 0.0,
            "omission": round(c.get("OMISSION", 0) / n, 4) if n else 0.0,
            "hallucination_ci95": wilson(h, n)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--limit", type=int, default=0, help="first N cases only (0=all)")
    ap.add_argument("--only", default=None,
                    help="comma-separated case ids (cheap re-measure of a prompt tweak)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    from benchmark.qa_runner import LeanClaudeCLILLM
    from engram.grounding_gate import fact_grounding_score
    from engram.local_grounding import try_local_score

    llm = LeanClaudeCLILLM(model=a.model, timeout_s=90)
    cases = CASES[: a.limit] if a.limit else CASES
    if a.only:
        wanted = {c.strip() for c in a.only.split(",")}
        cases = [c for c in cases if c[0] in wanted]

    grounding = {"true_scores": [], "false_scores": [], "mislabeled": []}
    arms = {"flat": {}, "current": {}, "trust": {}}
    unresolvable = {"n": 0, "abstained": 0, "fabricated": 0}
    per_case = []

    for (cid, kind, src_true, src_false, question, gold,
         fact_true, meta_true, fact_false, meta_false) in cases:
        # Phase 1 — PROVE case B: BOTH facts well-grounded in their own source
        # (real gate). A low distractor score = mislabeled case (A, not B) —
        # reported, and the case still runs (honesty over tidiness).
        s_true = fact_grounding_score(llm, src_true, fact_true)
        s_false = fact_grounding_score(llm, src_false, fact_false)
        grounding["true_scores"].append(s_true)
        grounding["false_scores"].append(s_false)
        if s_false < 40:
            grounding["mislabeled"].append({"case": cid, "false_score": s_false})

        # arm FLAT — bare facts (order: false first = worst case for recency bias)
        flat_lines = [f"- {fact_false}", f"- {fact_true}"]
        pred_flat = _answer(llm, _FLAT_SYSTEM, flat_lines, question)
        v_flat = _judge(llm, question, gold, pred_flat)

        # arm CURRENT — answer() today = flat + local-CE post-verify. No extra
        # LLM call: the CE (local, free) tells us whether the flat answer would
        # have been BLOCKED (no fact entails it) or SERVED (some fact does).
        v_current = v_flat
        ce_note = None
        if v_flat != "ERROR" and not pred_flat.startswith("__ERR__"):
            best = -1.0
            for fact in (fact_false, fact_true):
                r = try_local_score(fact, pred_flat)
                if r is None:          # CE unavailable → answer() fails open
                    ce_note = "ce_unavailable_failopen"
                    break
                best = max(best, r[0])
            else:
                if best < 40.0:        # answer() would have abstained
                    v_current = "OMISSION"
                    ce_note = f"ce_blocked({best:.0f})"
                else:
                    ce_note = f"ce_served({best:.0f})"

        # arm TRUST — real per-fact metadata + resolution rule
        trust_lines = [_meta_line(fact_false, meta_false),
                       _meta_line(fact_true, meta_true)]
        pred_trust = _answer(llm, _TRUST_SYSTEM, trust_lines, question)
        v_trust = _judge(llm, question, gold, pred_trust)

        if kind == "U":
            # gold behavior is ABSTENTION. The C/H/O judge is AMBIGUOUS here
            # (gold text IS "NO ANSWER", so an abstention can come back as
            # CORRECT) — first counter version miscounted exactly that way.
            # Measure the pick DIRECTLY: fabricated ⇔ the reply mentions the
            # distinctive tokens of exactly ONE side (it chose).
            import re as _re
            tok = lambda s: set(_re.findall(r"[A-Za-z0-9']+", s.lower()))  # noqa: E731
            only_t = tok(fact_true) - tok(fact_false)
            only_f = tok(fact_false) - tok(fact_true)
            p = pred_trust.lower()
            picked_t = any(w in p for w in only_t)
            picked_f = any(w in p for w in only_f)
            unresolvable["n"] += 1
            if picked_t != picked_f:      # exactly one side named = it chose
                unresolvable["fabricated"] += 1
            else:
                unresolvable["abstained"] += 1
        else:
            _bucket(arms["flat"], v_flat)
            _bucket(arms["current"], v_current)
            _bucket(arms["trust"], v_trust)

        per_case.append({"case": cid, "kind": kind, "s_true": s_true,
                         "s_false": s_false, "flat": v_flat,
                         "current": v_current, "ce": ce_note,
                         "trust": v_trust, "pred_flat": pred_flat[:80],
                         "pred_trust": pred_trust[:80]})
        print(f"[{cid}] gate(true/false)={s_true:.0f}/{s_false:.0f} "
              f"flat={v_flat} current={v_current}({ce_note}) trust={v_trust}")

    n_t = len(grounding["true_scores"])
    res = {
        "model": a.model, "n_cases": len(cases),
        "gate_wellgroundedness": {
            "true_mean": round(sum(grounding["true_scores"]) / n_t, 2) if n_t else None,
            "false_mean": round(sum(grounding["false_scores"]) / n_t, 2) if n_t else None,
            "mislabeled_cases": grounding["mislabeled"],
            "note": "CASE B requires the DISTRACTOR to be well-grounded too; "
                    "mislabeled = the case degenerated to case A (already covered).",
        },
        "flat": _rates(arms["flat"]),
        "current_answer": _rates(arms["current"]),
        "trust_conditioned": _rates(arms["trust"]),
        "unresolvable_conflicts": unresolvable,
        "per_case": per_case,
    }
    out = a.out or "benchmark/results/wellgrounded_distractor.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: res[k] for k in
                      ("gate_wellgroundedness", "flat", "current_answer",
                       "trust_conditioned", "unresolvable_conflicts")}, indent=2))
    print(f"saved -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
