"""A1 diagnostic (the moat-net-positive lever): does feeding the write-gate a BETTER source
window cut the documented ~30-40% clean over-rejection WITHOUT admitting noise?

Two new levers tested against the shipped baseline (prefix-cap + basic judge):
  * span     — pick the dialogue turns most lexically relevant to the candidate fact, up to
               the SAME char budget as prefix (token-efficient: in-window evidence cheaply).
  * full     — score against the WHOLE (uncapped) session = the admission ceiling.
  * full+abs — full window + an ABSTRACTION-crediting judge. DISTINCT from the FALSIFIED V2,
               which credited abstraction on a CAPPED window (BENCHMARKS.md "V2 falsified"):
               here the judge sees the whole session, so a faithful generalization IS
               evidenced. If this beats full+basic at 100% noise-rejection, it is a real
               admission win; if not, the ~70% ceiling is genuinely-abstractive facts.

Want: clean admit UP, foreign/confab reject ~100% (a lever that also admits noise is dead).
Pure-lexical span selector (no embeddings) — a crude floor; a better retriever would be >=.

    python -m benchmark.halumem_gate_source_ab --clean 20 --foreign 10 --confab 8 \
        --budget 2000 --out benchmark/results/halumem_gate_source_ab.json
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

_WORD = re.compile(r"[a-z0-9]+")

_ABSTRACTION_SYSTEM = (
    "You verify whether a SOURCE supports a candidate FACT for storage in a memory. The fact "
    "may be an ABSTRACTIVE SUMMARY of a pattern across the conversation (a preference, habit, "
    "or trait) rather than a verbatim statement. Rate 0-100 how strongly the source — taken "
    "as a whole — SUPPORTS the fact as a FAITHFUL generalization of what was actually said. "
    "100 = clearly supported (stated, or robustly evidenced across turns). 50 = weak/partial. "
    "0 = unsupported, contradicted, or only a superficially-similar distractor. Credit "
    "faithful paraphrase and reasonable generalization; do NOT credit a claim the source "
    "never evidences. Reply with exactly 'SCORE: N'.")


def _turns(session: dict) -> list[str]:
    out = []
    for t in session.get("dialogue", []) or []:
        c = (t.get("content") or "").strip()
        if c:
            out.append(f"{t.get('role', '?')}: {c}")
    return out


def _prefix(turns: list[str], budget: int) -> str:
    return "\n".join(turns)[:budget]


def _full(turns: list[str]) -> str:
    return "\n".join(turns)


def _span(turns: list[str], fact: str, budget: int) -> str:
    """Top turns by lexical overlap with the fact, greedily filled to budget, re-ordered to
    original sequence for readability."""
    ft = set(_WORD.findall(fact.lower()))
    order = {t: i for i, t in enumerate(turns)}
    ranked = sorted(turns, key=lambda t: len(set(_WORD.findall(t.lower())) & ft), reverse=True)
    picked: list[str] = []
    n = 0
    for t in ranked:
        if picked and n + len(t) + 1 > budget:
            break
        picked.append(t)
        n += len(t) + 1
    picked.sort(key=lambda t: order.get(t, 0))
    return "\n".join(picked)[:budget]


def _sessions_with_clean(user: dict, true_src: set[str]) -> list[tuple[str, list[str]]]:
    """(clean_fact_text, session_turns) for the user's grounded memory points."""
    out = []
    for s in user.get("sessions", []):
        tns = _turns(s)
        for mp in s.get("memory_points", []):
            if str(mp.get("memory_source", "")).lower() in true_src:
                txt = (mp.get("memory_content") or "").strip()
                if txt and tns:
                    out.append((txt, tns))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--clean", type=int, default=20)
    ap.add_argument("--foreign", type=int, default=10)
    ap.add_argument("--confab", type=int, default=8)
    ap.add_argument("--budget", type=int, default=2000)
    ap.add_argument("--threshold", type=float, default=40.0)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    from benchmark.halumem_writepath_moat import _TRUE_SRC, _all_facts, _make_confab, _questions
    from benchmark.qa_runner import LeanClaudeCLILLM
    from verimem import grounding_gate as G

    rng = random.Random(a.seed)
    users = []
    with open(a.jsonl, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                users.append(json.loads(line))
    rng.shuffle(users)
    u, others = users[0], users[1:4]
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=a.timeout)

    clean_pairs = _sessions_with_clean(u, _TRUE_SRC)
    rng.shuffle(clean_pairs)
    clean_pairs = clean_pairs[: a.clean]
    # a representative own-session for pairing noise (turns of the first clean session)
    own_turns = clean_pairs[0][1] if clean_pairs else []

    foreign_pool = []
    for o in others:
        foreign_pool.extend(_all_facts(o))
    rng.shuffle(foreign_pool)
    foreign = [(foreign_pool[i], own_turns) for i in range(min(a.foreign, len(foreign_pool)))]

    answerable = [q for q in _questions(u)
                  if "unknown" not in str(q.get("answer", "")).lower()
                  and "not provided" not in str(q.get("answer", "")).lower()]
    rng.shuffle(answerable)
    confab = []
    for q in answerable[: a.confab]:
        c = _make_confab(llm, q.get("question", ""), str(q.get("answer", "")))
        if c and own_turns:
            confab.append((c, own_turns))

    B = a.budget

    def score(fact: str, turns: list[str], cond: str) -> float:
        if cond == "prefix":
            src, sysp = _prefix(turns, B), None
        elif cond == "span":
            src, sysp = _span(turns, fact, B), None
        elif cond == "full":
            src, sysp = _full(turns), None
        elif cond == "full_abs":
            src, sysp = _full(turns), _ABSTRACTION_SYSTEM
        else:
            raise ValueError(cond)
        return G.fact_grounding_score(llm, src, fact, system=sysp)

    def admit_rate(items, cond):
        scores = [score(f, t, cond) for f, t in items]
        n = len(scores)
        return {
            "n": n,
            "admit_rate": round(sum(1 for s in scores if s >= a.threshold) / n, 3) if n else None,
            "mean": round(sum(scores) / n, 1) if n else None,
        }

    # clean: all 4 conditions (admit UP). noise: only the candidate ship conditions (reject ~100%)
    res = {
        "budget_chars": B, "threshold": a.threshold, "seed": a.seed,
        "clean": {c: admit_rate(clean_pairs, c) for c in ("prefix", "span", "full", "full_abs")},
        "foreign": {c: admit_rate(foreign, c) for c in ("span", "full_abs")},
        "confab": {c: admit_rate(confab, c) for c in ("span", "full_abs")},
    }
    # honest verdict helpers
    cl = res["clean"]
    res["verdict"] = {
        "span_vs_prefix_admit_delta": round((cl["span"]["admit_rate"] or 0) - (cl["prefix"]["admit_rate"] or 0), 3),
        "full_abs_vs_full_admit_delta": round((cl["full_abs"]["admit_rate"] or 0) - (cl["full"]["admit_rate"] or 0), 3),
        "span_keeps_rejection": all((res[g]["span"]["admit_rate"] or 0) <= 0.1 for g in ("foreign", "confab")),
        "full_abs_keeps_rejection": all((res[g]["full_abs"]["admit_rate"] or 0) <= 0.1 for g in ("foreign", "confab")),
    }
    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
