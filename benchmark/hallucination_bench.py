"""Study A-clean: hallucination / abstention on SQuAD v2 (human ANSWERABLE vs
IMPOSSIBLE labels, DETERMINISTIC scoring — no shared LLM judge).

For each (context, question) the answerer (the SAME prompt the QA pipeline uses,
which has an explicit abstention path) replies. We then score deterministically:
  * abstention by lexical marker ("NO ANSWER", "not in the context", ...);
  * answer-correctness by SQuAD-style normalized gold-span containment.
fabrication-rate (hallucination) = on IMPOSSIBLE questions, the fraction where the
model asserted an answer instead of abstaining. answer-rate = on ANSWERABLE, the
fraction answered correctly (control against uselessly over-abstaining).

Run: `python -m benchmark.hallucination_bench --per-class 50`.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any

from benchmark.qa_eval import answer_question

_ABSTAIN_RE = re.compile(
    r"\bno answer\b|not (mentioned|in the|stated|provided|available|specified|given|present|sure)"
    r"|cannot (be )?(answer|determin)|unanswerable|no information|no info\b"
    r"|does(n'?t| not) (say|mention|contain|specif|state|provid|include|indicate)"
    r"|do(n'?t| not) (know|have|mention|contain|see|find|say|specify|include|indicate)"
    r"|not enough (information|info|context)|isn'?t (mentioned|stated|specified|in the|provided)"
    r"|the (context|passage|text|notes?) (does(n'?t| not)|do(n'?t| not))"
    # Italian fallback (the model sometimes replies in Italian despite the instruction)
    r"|non (ho|c'?è|contengon|menzion|riport|specific|indic|fornisc|dicon|sono present)"
    r"|nessun[ao] (informazion|menzion|indicazion|dato)|non (e'|è) (present|disponibil|nelle note)",
    re.I)
_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT = re.compile(r"[^a-z0-9 ]")


def is_abstention(pred: str) -> bool:
    t = (pred or "").strip()
    return t.upper() == "NO ANSWER" or bool(_ABSTAIN_RE.search(t))


def _norm(s: str) -> str:
    s = _PUNCT.sub(" ", (s or "").lower())
    s = _ARTICLES.sub(" ", s)
    return " ".join(s.split())


def contains_gold(pred: str, golds: list[str]) -> bool:
    np = _norm(pred)
    return any(_norm(g) and _norm(g) in np for g in golds)


_STRICT_SYSTEM = (
    "Answer the question using ONLY facts EXPLICITLY stated in the context. Do NOT "
    "infer, guess, combine facts, or use any outside knowledge. If the exact answer "
    "is not explicitly present in the context — even if a related or "
    "plausible-sounding phrase appears — reply with exactly: NO ANSWER."
)


def strict_answer(llm: Any, question: str, context: str, *,
                  model: str | None = None) -> str:
    """Answer with the STRICT explicit-only abstention prompt (the before/after
    improvement against fabrication on adversarial unanswerables)."""
    resp = llm.complete(
        _STRICT_SYSTEM,
        [{"role": "user",
          "content": f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"}],
        model=model, max_tokens=64)
    return (getattr(resp, "text", "") or "").strip()


_VERIFY_SYSTEM = (
    "You are a strict verifier. Given a context, a question, and a PROPOSED answer, "
    "decide if the context EXPLICITLY and DIRECTLY states that proposed answer as the "
    "answer to the question. A merely related or plausible-sounding phrase does NOT "
    "count. Reply with exactly one word: YES or NO."
)


def verified_answer(llm: Any, question: str, context: str, *,
                    model: str | None = None) -> str:
    """SOTA secondary-verifier (2-pass): answer normally, then a second LLM call
    checks whether that answer is EXPLICITLY supported by the context; if not,
    abstain. Targets 'plausible distractor capture' — the verifier rejects a
    present-but-wrong phrase the first pass grabbed."""
    a = answer_question(llm, question, [context], model=model)
    if is_abstention(a):
        return a
    resp = llm.complete(
        _VERIFY_SYSTEM,
        [{"role": "user",
          "content": f"Context:\n{context}\n\nQuestion: {question}\n"
                     f"Proposed answer: {a}\n\nIs the proposed answer explicitly "
                     f"stated by the context? YES or NO."}],
        model=model, max_tokens=8)
    v = (getattr(resp, "text", "") or "").strip().lower()
    return a if v.startswith("y") else "NO ANSWER"


def sample_squad(per_class: int, seed: int) -> list[dict[str, Any]]:
    from datasets import load_dataset
    ds = load_dataset("squad_v2", split="validation")
    idx = list(range(len(ds)))
    random.Random(seed).shuffle(idx)
    ans: list[dict[str, Any]] = []
    imp: list[dict[str, Any]] = []
    for i in idx:
        r = ds[i]
        impossible = r["answers"]["text"] == []
        bucket = imp if impossible else ans
        if len(bucket) < per_class:
            bucket.append({"context": r["context"], "question": r["question"],
                           "golds": list(r["answers"]["text"]), "impossible": impossible})
        if len(ans) >= per_class and len(imp) >= per_class:
            break
    return ans + imp


def run(llm: Any, *, per_class: int = 50, seed: int = 0,
        strict: bool = False, verify: bool = False) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for ex in sample_squad(per_class, seed):
        if verify:
            pred = verified_answer(llm, ex["question"], ex["context"])
        elif strict:
            pred = strict_answer(llm, ex["question"], ex["context"])
        else:
            pred = answer_question(llm, ex["question"], [ex["context"]])
        rows.append({
            "impossible": ex["impossible"],
            "abstained": is_abstention(pred),
            "correct": (not ex["impossible"]) and contains_gold(pred, ex["golds"]),
            "predicted": pred[:200], "golds": ex["golds"],
            "question": ex["question"][:120],
        })
    imp = [r for r in rows if r["impossible"]]
    ans = [r for r in rows if not r["impossible"]]
    fabricated = [r for r in imp if not r["abstained"]]
    return {
        "n": len(rows), "per_class": per_class, "seed": seed,
        "n_impossible": len(imp), "n_answerable": len(ans),
        "fabrication_rate": round(len(fabricated) / len(imp), 3) if imp else 0.0,
        "abstention_rate_on_impossible": round(sum(r["abstained"] for r in imp) / len(imp), 3) if imp else 0.0,
        "answer_correct_rate_on_answerable": round(sum(r["correct"] for r in ans) / len(ans), 3) if ans else 0.0,
        "over_abstention_on_answerable": round(sum(r["abstained"] for r in ans) / len(ans), 3) if ans else 0.0,
        "fabrications_for_audit": [
            {"q": r["question"], "pred": r["predicted"]} for r in fabricated],
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SQuAD-v2 hallucination/abstention bench.")
    p.add_argument("--per-class", type=int, default=50)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--strict", action="store_true",
                   help="use the strict explicit-only abstention prompt")
    p.add_argument("--verify", action="store_true",
                   help="SOTA secondary-verifier 2-pass (answer then verify-explicit)")
    p.add_argument("--model", type=str, default="claude-sonnet-4-6")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    from benchmark.qa_runner import LeanClaudeCLILLM

    llm = LeanClaudeCLILLM(model=args.model, timeout_s=60)
    res = run(llm, per_class=args.per_class, seed=args.seed,
              strict=args.strict, verify=args.verify)
    res["model"] = args.model
    res["mode"] = "verify" if args.verify else ("strict" if args.strict else "normal")
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("rows", "fabrications_for_audit")}, indent=2))
    if args.out:
        args.out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["is_abstention", "contains_gold", "sample_squad", "run", "main"]
