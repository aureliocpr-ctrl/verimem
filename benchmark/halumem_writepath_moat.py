"""HaluMem write-path moat A/B — does admitting only GROUNDED facts cut downstream
hallucination? The proof that targets the moat where it lives (the write gate), on a
real public corpus.

Setup per user (HaluMem-Medium): the user's own memory_points are CLEAN (grounded by
that user's dialogue). We inject NOISE = memory_points sampled from OTHER users —
plausible, well-formed facts that THIS user's dialogue does NOT entail (cross-persona
contamination, the realistic failure: an extractor/LLM attributing someone else's fact
to this user). Two arms:

  OFF (no gate): store clean + noise (what mem0/Zep do — store whatever is emitted).
  ON  (gate):   admit a candidate only if engram.grounding_gate.fact_grounding_score
                (its paired dialogue ⊢ the fact) >= threshold. Clean → admitted;
                foreign noise → rejected (the dialogue doesn't ground it).

Then answer the user's questions from each arm's memory and LLM-judge C/H/O. The moat
prediction: ON rejects the foreign noise → fewer hallucinations from contaminated recall,
at little recall cost on the clean facts. Reports hallucination ON vs OFF AND the gate's
noise-rejection / clean-admission rates (the admission precision/recall).

Serial claude -p. Heavy: ~ (clean+noise) gate calls + q*2 arms *(answer+judge). Use
--smoke for a tiny end-to-end validation.

    python -m benchmark.halumem_writepath_moat --users 3 --clean 20 --noise 20 --q 12 \
        --out benchmark/results/halumem_writepath_moat.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
import tempfile
from pathlib import Path

_TRUE_SRC = ("system", "secondary", "primary")
_SRC_CAP = 8000  # cap dialogue chars fed to the gate (override via --src-cap). Raised
# from 3000: the decisive same-topic run showed the 3000 cap truncated evidence and
# drove clean-admission down to 55% (over-rejecting valid facts), offsetting the moat.


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (round(max(0.0, c - h), 4), round(min(1.0, c + h), 4))


def _session_text(session: dict) -> str:
    turns = session.get("dialogue", []) or []
    out = []
    for t in turns:
        c = (t.get("content") or "").strip()
        if c:
            out.append(f"{t.get('role', '?')}: {c}")
    return "\n".join(out)[:_SRC_CAP]


def _clean_facts(user: dict) -> list[tuple[str, str]]:
    """(fact_text, paired_source_dialogue) for the user's own grounded memory points."""
    out = []
    for s in user.get("sessions", []):
        src = _session_text(s)
        for mp in s.get("memory_points", []):
            if str(mp.get("memory_source", "")).lower() in _TRUE_SRC:
                txt = (mp.get("memory_content") or "").strip()
                if txt:
                    out.append((txt, src))
    return out


def _all_facts(user: dict) -> list[str]:
    out = []
    for s in user.get("sessions", []):
        for mp in s.get("memory_points", []):
            txt = (mp.get("memory_content") or "").strip()
            if txt:
                out.append(txt)
    return out


def _questions(user: dict) -> list[dict]:
    out = []
    for s in user.get("sessions", []):
        out.extend(s.get("questions", []) or [])
    return out


def _questions_with_source(user: dict) -> list[tuple[dict, str]]:
    """(question, ITS session's dialogue text) — so a same-topic confab is gated against the
    conversation that actually grounds the TRUE answer (the realistic write-poisoning threat),
    not a random unrelated dialogue. Fixes the adversarial-review 'rigged pairing' hole."""
    out = []
    for s in user.get("sessions", []):
        src = _session_text(s)
        for q in (s.get("questions", []) or []):
            out.append((q, src))
    return out


_CONFAB_SYSTEM = (
    "You generate a single FALSE memory note for a robustness test. Given a question and "
    "its TRUE answer, write ONE short declarative memory sentence that states a PLAUSIBLE "
    "but WRONG answer to that question (a different specific value, same topic). No hedging, "
    "no 'incorrectly' — write it as if it were a real stored fact. One sentence only."
)


def _make_confab(llm, question: str, gold: str) -> str | None:
    """LLM-generate a same-topic confabulation: a plausible-wrong answer stated as a
    memory. Unlike foreign noise, this IS retrieved for `question` (same topic), so it
    actually competes at answer time — the threat the write-gate is meant to catch."""
    try:
        r = llm.complete(_CONFAB_SYSTEM,
                         [{"role": "user", "content": f"Question: {question}\nTrue answer: "
                                                      f"{gold}\nFalse memory note:"}],
                         max_tokens=40)
        t = (getattr(r, "text", "") or "").strip().strip('"')
        return t or None
    except Exception:  # noqa: BLE001
        return None


def main(argv=None) -> int:
    global _SRC_CAP
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--users", type=int, default=3)
    ap.add_argument("--clean", type=int, default=20, help="clean facts/user")
    ap.add_argument("--noise", type=int, default=20, help="injected noise facts/user")
    ap.add_argument("--noise-mode", choices=["foreign", "same-topic"], default="foreign",
                    help="foreign=cross-persona facts (not retrieved); same-topic=plausible-"
                         "wrong answers to the user's own questions (ARE retrieved)")
    ap.add_argument("--q", type=int, default=12, help="questions/user")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--threshold", type=float, default=50.0, help="gate admit threshold")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--src-cap", type=int, default=_SRC_CAP,
                    help="max dialogue chars fed to the gate (raise to reduce over-rejection)")
    ap.add_argument("--gate-span-budget", type=int, default=0,
                    help="A1: if >0, gate scores against the fact-relevant SPAN of the source "
                         "(this many chars) instead of a raw prefix — cuts over-rejection")
    ap.add_argument("--timeout", type=int, default=90,
                    help="per-call claude -p timeout (s); raise under machine load so big "
                         "prompts complete instead of timing out (the cap=8000 error cause)")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    _SRC_CAP = a.src_cap
    if a.smoke:
        a.users, a.clean, a.noise, a.q = 1, 3, 3, 2
    import os as _os
    _os.environ.setdefault("ENGRAM_QA_DATES", "1")

    from benchmark.halumem_qa_bench import _classify
    from benchmark.qa_eval import answer_question
    from benchmark.qa_runner import LeanClaudeCLILLM
    from engram.grounding_gate import fact_grounding_score
    from engram.semantic import Fact, SemanticMemory

    rng = random.Random(a.seed)
    users = []
    with open(a.jsonl, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                users.append(json.loads(line))
    rng.shuffle(users)
    pool = users[: max(a.users + 1, a.users)]  # need others for noise
    users = pool[: a.users]
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=a.timeout)

    def fresh_mem(tag):
        tmp = Path(tempfile.mkdtemp(prefix=f"halu_wp_{tag}_"))
        return SemanticMemory(db_path=tmp / "semantic" / "semantic.db")

    arms = {arm: {"CORRECT": 0, "HALLUCINATION": 0, "OMISSION": 0, "ERROR": 0}
            for arm in ("off", "on")}
    gate = {"noise_rejected": 0, "noise_total": 0, "clean_admitted": 0, "clean_total": 0}
    mcnemar = {"off_only_hall": 0, "on_only_hall": 0, "both_hall": 0, "neither_hall": 0}

    for ui, u in enumerate(users):
        clean = _clean_facts(u)
        rng.shuffle(clean)
        clean = clean[: a.clean]
        own_dialogues = [src for _, src in clean] or [""]
        u_questions = _questions(u)
        rng.shuffle(u_questions)
        confab_questions: list[dict] = []  # same-topic: the questions whose confab we inject
        if a.noise_mode == "same-topic":
            # same-topic confabs: a plausible-WRONG answer to an ANSWERABLE question, paired
            # with THAT QUESTION'S OWN session dialogue — the conversation that grounds the
            # TRUE answer. So the gate must discriminate a wrong-but-on-topic claim from the
            # context that supports the right one (the realistic write-poisoning threat), NOT
            # score it against a random unrelated dialogue (the prior 'rigged' setup).
            qsrc = _questions_with_source(u)
            rng.shuffle(qsrc)
            answerable = [(q, src) for q, src in qsrc
                          if "unknown" not in str(q.get("answer", "")).lower()
                          and "not provided" not in str(q.get("answer", "")).lower()]
            noise = []
            for q, src in answerable[: a.noise]:
                c = _make_confab(llm, q.get("question", ""), str(q.get("answer", "")))
                if c:
                    noise.append((c, src))  # confab gated against ITS grounding dialogue
                    confab_questions.append(q)  # test EXACTLY these (un-diluted measure)
        else:
            # foreign: facts from OTHER users (cross-persona contamination)
            others = [x for j, x in enumerate(pool) if x is not u]
            foreign_pool = []
            for o in others:
                foreign_pool.extend(_all_facts(o))
            rng.shuffle(foreign_pool)
            noise = [(foreign_pool[i], rng.choice(own_dialogues))
                     for i in range(min(a.noise, len(foreign_pool)))]

        # gate each candidate; record admission stats
        admitted_on: list[str] = []
        all_candidates = [(t, s, "clean") for t, s in clean] + \
                         [(t, s, "noise") for t, s in noise]
        for txt, src, kind in all_candidates:
            score = fact_grounding_score(llm, src, txt,
                                         focus_budget=(a.gate_span_budget or None))
            admit = score >= a.threshold
            if kind == "noise":
                gate["noise_total"] += 1
                if not admit:
                    gate["noise_rejected"] += 1
            else:
                gate["clean_total"] += 1
                if admit:
                    gate["clean_admitted"] += 1
            if admit:
                admitted_on.append(txt)

        all_texts = [t for t, _, _ in all_candidates]
        sm_off, sm_on = fresh_mem(f"{ui}off"), fresh_mem(f"{ui}on")
        for txt in all_texts:
            try:
                sm_off.store(Fact(proposition=txt, topic=f"halu/{ui}", confidence=0.8),
                             embed="sync")
            except Exception:  # noqa: BLE001
                pass
        for txt in admitted_on:
            try:
                sm_on.store(Fact(proposition=txt, topic=f"halu/{ui}", confidence=0.8),
                            embed="sync")
            except Exception:  # noqa: BLE001
                pass

        # In same-topic mode test EXACTLY the questions whose confab we injected (each has
        # a competing wrong-answer in OFF memory) — the clean, un-diluted measure of the
        # gate's protection. Otherwise (foreign) test a random sample of the user's Qs.
        if a.noise_mode == "same-topic":
            qs = confab_questions[: a.q]
        else:
            qs = _questions(u)
            rng.shuffle(qs)
            qs = qs[: a.q]
        for q in qs:
            question = q.get("question", "")
            gold = str(q.get("answer", "") or "")
            key = str(q.get("evidence", "") or "")
            pair = {}
            for arm, sm in (("off", sm_off), ("on", sm_on)):
                try:
                    hits = sm.recall(question, k=a.k)
                    ctx = [getattr(fo, "proposition", "") for fo, _ in hits]
                    pred = answer_question(llm, question, ctx)
                    verdict = _classify(llm, question, gold, key, pred)
                except Exception as exc:  # noqa: BLE001
                    verdict = f"ERROR:{str(exc)[:50]}"
                bucket = "ERROR" if verdict.startswith("ERROR") else verdict
                arms[arm][bucket] = arms[arm].get(bucket, 0) + 1
                pair[arm] = bucket
            # PAIRED record (same question, both arms) → McNemar power on the
            # hallucination axis: count questions OFF fabricated but ON did not, vs
            # the reverse. Far more sensitive than the independent-arm rates at low n.
            if pair.get("off") != "ERROR" and pair.get("on") != "ERROR":
                off_h = pair["off"] == "HALLUCINATION"
                on_h = pair["on"] == "HALLUCINATION"
                if off_h and not on_h:
                    mcnemar["off_only_hall"] += 1
                elif on_h and not off_h:
                    mcnemar["on_only_hall"] += 1
                elif off_h and on_h:
                    mcnemar["both_hall"] += 1
                else:
                    mcnemar["neither_hall"] += 1

    def rates(c):
        n = c["CORRECT"] + c["HALLUCINATION"] + c["OMISSION"]
        return {"counts": c, "n": n,
                "correct": round(c["CORRECT"] / n, 4) if n else 0.0,
                "hallucination": round(c["HALLUCINATION"] / n, 4) if n else 0.0,
                "omission": round(c["OMISSION"] / n, 4) if n else 0.0,
                "hallucination_ci95": wilson(c["HALLUCINATION"], n)}

    def mcnemar_exact(b, c):
        """Two-sided exact McNemar p on discordant pairs b,c (binomial, n small-safe)."""
        n = b + c
        if n == 0:
            return None
        k = min(b, c)
        tail = sum(math.comb(n, i) for i in range(0, k + 1)) * (0.5 ** n)
        return round(min(1.0, 2.0 * tail), 4)

    b, c = mcnemar["off_only_hall"], mcnemar["on_only_hall"]

    res = {
        "users": len(users), "threshold": a.threshold,
        "src_cap": _SRC_CAP, "seed": a.seed, "noise_mode": a.noise_mode,
        "gate_span_budget": a.gate_span_budget,
        "mcnemar": {
            **mcnemar,
            "discordant": b + c,
            "p_value_exact": mcnemar_exact(b, c),
            "note": "b=off_only_hall (gate FIXED a fabrication), c=on_only_hall "
                    "(gate CAUSED one); p tests if the moat's net effect on hallucination "
                    "is real. Paired test — far more powerful than the independent rates.",
        },
        "gate_admission": {
            **gate,
            "noise_rejection_rate": round(gate["noise_rejected"] / gate["noise_total"], 4)
            if gate["noise_total"] else None,
            "clean_admission_rate": round(gate["clean_admitted"] / gate["clean_total"], 4)
            if gate["clean_total"] else None,
        },
        "off": rates(arms["off"]),
        "on": rates(arms["on"]),
    }
    res["hallucination_drop_on_vs_off"] = round(
        res["off"]["hallucination"] - res["on"]["hallucination"], 4)
    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
