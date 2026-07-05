"""HaluMem Extraction-F1 — the official protocol's extraction slice, with the moat A/B.

For each session: the LLM extracts memory facts from the dialogue; we score them against
the gold memory_points (precision / recall / F1). Matching is EMBEDDING-based (e5 cosine
>= --match-thr) so the SCORING is local and deterministic — only the extraction step
needs claude -p. The moat angle: OFF keeps every extracted fact (what mem0/Zep do); ON
admits only those the write-gate grounds (fact_grounding_score(dialogue, fact) >= --gate-thr).
Prediction: ON trades a little recall for higher precision (fewer spurious extractions
stored) — the anti-confab trade, now on the extraction axis.

Local sanity (no LLM): `--self-test` scores gold-vs-gold (recall must be ~1.0), proving
the embedding matcher. Full run: serial claude -p.

    python -m benchmark.halumem_extraction_f1 --users 3 --sessions 4 --out ...json
"""
from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

import numpy as np


def _session_text(session: dict, cap: int = 6000) -> str:
    out = []
    for t in session.get("dialogue", []) or []:
        c = (t.get("content") or "").strip()
        if c:
            out.append(f"{t.get('role', '?')}: {c}")
    return "\n".join(out)[:cap]


def _gold_facts(session: dict) -> list[str]:
    return [(mp.get("memory_content") or "").strip()
            for mp in session.get("memory_points", [])
            if (mp.get("memory_content") or "").strip()]


_EXTRACT_SYSTEM = (
    "Extract the durable MEMORY FACTS a personal assistant should store from this "
    "conversation — stable facts about the user (identity, relationships, preferences, "
    "events, plans). One short declarative sentence per fact, one per line, no numbering, "
    "no preamble. Only facts the dialogue actually states.")

# Granularity lever (iter 19): HaluMem gold memory_points are ATOMIC, subject-named
# and exhaustive; the generic prompt yields fewer, compound facts (each matches at
# most one gold at the e5 threshold) and 600 max_tokens truncates dense sessions.
# SINGLE SOURCE OF TRUTH (iter 34): the atomic prompt lives in the PRODUCT module
# (engram.conversation_ingest) and the bench imports it — a bench win IS a product win.
from engram.conversation_ingest import ATOMIC_EXTRACT_SYSTEM as _EXTRACT_SYSTEM_ATOMIC

_PROMPTS = {"v1": _EXTRACT_SYSTEM, "atomic": _EXTRACT_SYSTEM_ATOMIC}


def _extract(llm, dialogue: str, model=None, *, system: str = _EXTRACT_SYSTEM,
             max_tokens: int = 600) -> list[str]:
    try:
        r = llm.complete(system,
                         [{"role": "user", "content": f"Conversation:\n{dialogue}\n\nFacts:"}],
                         model=model, max_tokens=max_tokens)
        text = (getattr(r, "text", "") or "")
    except Exception:  # noqa: BLE001
        return []
    out = []
    for line in text.splitlines():
        s = line.strip().lstrip("-*•0123456789. ").strip()
        if len(s) > 4:
            out.append(s)
    return out


def _embed_matrix(texts: list[str]) -> np.ndarray:
    from engram import embedding
    if not texts:
        return np.zeros((0, 1), dtype=np.float32)
    return np.stack([embedding.encode(t) for t in texts])


def _prf(pred: list[str], gold: list[str], thr: float) -> tuple[float, float, float, int]:
    """Embedding precision/recall/F1: a gold is recalled if some pred matches it (cosine
    >= thr); a pred is precise if it matches some gold. Returns (P, R, F1, n_pred)."""
    if not gold:
        return (0.0, 0.0, 0.0, len(pred))
    if not pred:
        return (0.0, 0.0, 0.0, 0)
    P = _embed_matrix(pred)
    G = _embed_matrix(gold)
    sims = P @ G.T  # (n_pred, n_gold), e5 vectors are unit-norm
    pred_hit = (sims.max(axis=1) >= thr).sum()
    gold_hit = (sims.max(axis=0) >= thr).sum()
    prec = pred_hit / len(pred)
    rec = gold_hit / len(gold)
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return (round(float(prec), 4), round(float(rec), 4), round(float(f1), 4), len(pred))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--users", type=int, default=3)
    ap.add_argument("--sessions", type=int, default=4, help="sessions/user")
    ap.add_argument("--match-thr", type=float, default=0.86, help="e5 cosine match threshold")
    ap.add_argument("--gate-thr", type=float, default=40.0)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--self-test", action="store_true", help="score gold-vs-gold (no LLM)")
    ap.add_argument("--prompt", choices=sorted(_PROMPTS), default="v1",
                    help="extraction prompt variant (atomic = granularity lever)")
    ap.add_argument("--max-out-tokens", type=int, default=600,
                    help="extraction output cap (600 truncates dense sessions)")
    ap.add_argument("--no-gate", action="store_true",
                    help="skip the admission-gate arm (halves LLM calls; "
                         "granularity iterations only need the off arm)")
    ap.add_argument("--consolidate", action="store_true",
                    help="add a 'consolidated' arm: a 2nd LLM pass merges "
                         "near-duplicates + drops trivia to lift PRECISION "
                         "(the F1 bottleneck at ~0.65) — the product ingest "
                         "consolidation, measured")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    rng = random.Random(7)
    users = []
    with open(a.jsonl, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                users.append(json.loads(line))
    rng.shuffle(users)
    users = users[: a.users]

    if a.self_test:
        # gold-vs-gold: recall must be ~1.0 and precision ~1.0 (validates the matcher).
        agg = []
        for u in users:
            for s in u.get("sessions", [])[: a.sessions]:
                gold = _gold_facts(s)
                if gold:
                    agg.append(_prf(gold, gold, a.match_thr))
        if agg:
            P = sum(x[0] for x in agg) / len(agg)
            R = sum(x[1] for x in agg) / len(agg)
            print(json.dumps({"self_test": True, "sessions": len(agg),
                              "precision": round(P, 4), "recall": round(R, 4),
                              "note": "gold-vs-gold; both should be ~1.0"}, indent=2))
        return 0

    from benchmark.qa_runner import LeanClaudeCLILLM
    from engram.grounding_gate import fact_grounding_score
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=a.timeout)

    arms = {"off": [], "on": [], "consolidated": []}
    gate_errors = 0
    for u in users:
        for s in u.get("sessions", [])[: a.sessions]:
            gold = _gold_facts(s)
            if not gold:
                continue
            src = _session_text(s)
            extracted = _extract(llm, src, model=a.model,
                                 system=_PROMPTS[a.prompt],
                                 max_tokens=a.max_out_tokens)
            if not extracted:
                continue
            arms["off"].append(_prf(extracted, gold, a.match_thr))
            if a.consolidate:
                from engram.conversation_ingest import consolidate_facts
                cons = consolidate_facts(extracted, llm=llm,
                                         max_out_tokens=a.max_out_tokens)
                arms["consolidated"].append(_prf(cons, gold, a.match_thr))
            if not a.no_gate:
                # A transient LLM timeout on ONE gate call must not kill a
                # multi-hour run (it did, 2026-07-04: LLMError 120s ~35min in).
                # Fail-safe per fact: an unscorable fact is NOT admitted.
                admitted = []
                for f in extracted:
                    try:
                        if fact_grounding_score(llm, src, f) >= a.gate_thr:
                            admitted.append(f)
                    except Exception:  # noqa: BLE001
                        gate_errors += 1
                arms["on"].append(_prf(admitted, gold, a.match_thr))

    def agg(rows):
        if not rows:
            return {"sessions": 0}
        return {"sessions": len(rows),
                "precision": round(sum(r[0] for r in rows) / len(rows), 4),
                "recall": round(sum(r[1] for r in rows) / len(rows), 4),
                "f1": round(sum(r[2] for r in rows) / len(rows), 4),
                "avg_pred": round(sum(r[3] for r in rows) / len(rows), 2)}

    res = {"users": len(users), "match_thr": a.match_thr, "gate_thr": a.gate_thr,
           # A/B self-proving: the variant actually used by THIS process
           "prompt_variant": a.prompt, "max_out_tokens": a.max_out_tokens,
           "no_gate": bool(a.no_gate), "gate_errors": gate_errors,
           "consolidate": bool(a.consolidate),
           "grounding_backend": os.environ.get("ENGRAM_GROUNDING_BACKEND", "")
                                or "llm",
           "off": agg(arms["off"]), "on": agg(arms["on"]),
           "consolidated": agg(arms["consolidated"])}
    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
