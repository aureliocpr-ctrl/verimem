"""T3 — which fail-or-abstain SIGNAL actually works? (the engineering core)

T2 proved the model's verbalized confidence is useless for separating sound answers
from fabrications (AUROC ~0.31 — it is ~97% confident even when fabricating). So the
industry-standard "answer + threshold the confidence" gate is broken at the root. This
asks the consequential question: is there a groundedness signal, computable, that DOES
separate sound from pathological where confidence fails?

We take SQuAD-v2 (answerable + impossible) and, for every output where the model
PROPOSES an answer (not an abstention — the case a gate must judge), we compute three
candidate "trust this answer" signals and compare their AUROC + AURC (risk-coverage,
Geifman & El-Yaniv 2017) for separating SOUND (answerable & gold-correct) from
PATHOLOGICAL (impossible-answered = fabrication, or answerable-wrong):

  S1 conf_self    — the model's own verbalized confidence (the T2 baseline; introspective)
  S2 entail_ext   — an EXTERNAL judge call: graded 0-100 logical support of the context
                    for the proposed answer (model-as-verifier, NOT generator; semantic,
                    "judge meaning not word overlap, a superficial distractor scores 0")
  S3 consistency  — (opt-in) self-consistency: k resamples, fraction agreeing with the
                    committed answer (semantic-entropy family, Farquhar et al. 2024)

Falsifiable: if entail_ext does NOT beat conf_self on AUROC/AURC, the structural-grounding
gate is dead and we say so. If it wins, it becomes the implemented grounding gate.
Deterministic soundness labels; claude -p lean; O5 (subscription only).
"""
from __future__ import annotations

import argparse
import json
import re
from typing import Any

import numpy as np

from benchmark.calibration_bench import _auroc, _parse
from benchmark.hallucination_bench import contains_gold, is_abstention, sample_squad

_ANS_SYSTEM = ("You answer a question from the context. If the context does not contain "
               "the answer, reply 'NO ANSWER'. After your answer, on a new line write "
               "'CONFIDENCE: N' (N 0-100 = how sure the answer is correct and supported "
               "by the context). Respond in English.")

_ENTAIL_SYSTEM = (
    "You judge GROUNDING. Given a context, a question, and a proposed answer, rate from "
    "0 to 100 how strongly the context LOGICALLY SUPPORTS that the proposed answer is "
    "the correct answer to the question. 100 = the context entails it unambiguously. "
    "50 = the context mentions related material but does not establish this specific "
    "answer. 0 = the context does not support it at all (irrelevant, contradicted, or "
    "only a superficially-similar distractor). Judge MEANING, not word overlap. Reply "
    "with exactly 'SCORE: N'.")

# Structural / span-copy variant (the "cite-or-abstain" grounding): force the verifier
# to first COMMIT to an exact supporting span (or NONE) before scoring — chain-of-thought
# grounding that resists the surface-plausibility capture the basic judge fell for
# (smoke: basic judge gave 80.8/100 even to fabrications).
_ENTAIL_SPAN_SYSTEM = (
    "You verify GROUNDING by quotation. Given a context, a question, and a proposed "
    "answer: FIRST, on line 1, quote the EXACT span from the context that states the "
    "proposed answer is the answer to the question — or write NONE if no span states it "
    "(a span about a related but different thing is NONE). THEN, on line 2, write "
    "'SCORE: N': N=100 only if your quoted span explicitly states the answer; N=0 if you "
    "wrote NONE; N in 1–60 if the span is only related/partial. Judge meaning, not word "
    "overlap.")

_SCORE_RE = re.compile(r"score[:=]?\s*(\d{1,3})", re.I)


def _entail_score(llm: Any, q: str, ctx: str, ans: str, *, span: bool = False) -> float:
    system = _ENTAIL_SPAN_SYSTEM if span else _ENTAIL_SYSTEM
    raw = llm.complete(system,
                       [{"role": "user", "content": f"Context: {ctx}\n\nQuestion: {q}\n"
                                                     f"Proposed answer: {ans}\n\nScore:"}],
                       max_tokens=120 if span else 12)
    m = _SCORE_RE.search(getattr(raw, "text", "") or "")
    return min(100.0, max(0.0, float(m.group(1)))) if m else 50.0


def _consistency(llm: Any, q: str, ctx: str, committed: str, k: int) -> float:
    """Fraction of k resamples whose answer semantically matches the committed one
    (cheap proxy: normalized-substring overlap either direction)."""
    from benchmark.hallucination_bench import _norm
    cn = _norm(committed)
    agree = 0
    for _ in range(k):
        raw = llm.complete(_ANS_SYSTEM,
                           [{"role": "user",
                             "content": f"Context: {ctx}\n\nQuestion: {q}\nAnswer:"}],
                           max_tokens=60)
        a, _c = _parse(getattr(raw, "text", "") or "")
        an = _norm(a)
        if cn and an and (cn in an or an in cn):
            agree += 1
    return agree / k if k else 0.0


def _aurc(scores: np.ndarray, sound: np.ndarray) -> float:
    """Area under the risk-coverage curve: accept highest-score first; risk at each
    coverage = error rate among accepted. Lower = better selective predictor."""
    order = np.argsort(-scores, kind="mergesort")
    c = sound[order].astype(float)
    cum = np.cumsum(c)
    n = np.arange(1, len(c) + 1)
    risk = 1.0 - cum / n
    return float(np.mean(risk))


def _signal_metrics(scores: list[float], sound: list[int]) -> dict[str, Any]:
    from verimem.grounding_gate import optimal_threshold
    s = np.asarray(scores, float)
    y = np.asarray(sound, int)
    return {"auroc": round(_auroc(scores, sound), 3), "aurc": round(_aurc(s, y), 3),
            "opt_threshold": round(optimal_threshold(scores, sound), 1),
            "mean_on_sound": round(float(s[y == 1].mean()), 1) if (y == 1).any() else None,
            "mean_on_patho": round(float(s[y == 0].mean()), 1) if (y == 0).any() else None}


def run(llm: Any, *, per_class: int = 50, seed: int = 0,
        consistency_k: int = 0, judge: str = "basic") -> dict[str, Any]:
    want_basic = judge in ("basic", "both")
    want_span = judge in ("span", "both")
    rows: list[dict[str, Any]] = []
    n_abstained = 0
    for ex in sample_squad(per_class, seed):
        raw = llm.complete(_ANS_SYSTEM,
                           [{"role": "user",
                             "content": f"Context: {ex['context']}\n\nQuestion: "
                                        f"{ex['question']}\nAnswer:"}], max_tokens=60)
        ans, conf = _parse(getattr(raw, "text", "") or "")
        if is_abstention(ans):
            n_abstained += 1
            continue  # a gate only judges PROPOSED answers
        sound = int((not ex["impossible"]) and contains_gold(ans, ex["golds"]))
        q, ctx = ex["question"], ex["context"]
        rows.append({
            "impossible": ex["impossible"], "sound": sound, "conf": conf,
            "entail": _entail_score(llm, q, ctx, ans) if want_basic else None,
            "entail_span": _entail_score(llm, q, ctx, ans, span=True) if want_span else None,
            "cons": (_consistency(llm, q, ctx, ans, consistency_k) * 100.0
                     if consistency_k else None),
            "ans": ans[:50]})
    if not rows:
        return {"error": "no proposed answers", "n_abstained": n_abstained}
    sound = [r["sound"] for r in rows]
    out = {
        "n_judged": len(rows), "n_abstained": n_abstained, "judge": judge,
        "n_sound": sum(sound), "n_pathological": len(rows) - sum(sound),
        "S1_conf_self": _signal_metrics([r["conf"] for r in rows], sound),
    }
    if want_basic:
        out["S2_entail_ext"] = _signal_metrics([r["entail"] for r in rows], sound)
    if want_span:
        out["S2b_entail_span"] = _signal_metrics([r["entail_span"] for r in rows], sound)
    if consistency_k:
        out["S3_consistency"] = _signal_metrics([r["cons"] for r in rows], sound)
    out["rows"] = [{k: r[k] for k in
                    ("impossible", "sound", "conf", "entail", "entail_span", "cons")}
                   for r in rows]
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Grounding-signal comparison (T3).")
    p.add_argument("--per-class", type=int, default=50)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--consistency-k", type=int, default=0,
                   help="if >0, also measure self-consistency with k resamples")
    p.add_argument("--judge", choices=["basic", "span", "both"], default="basic",
                   help="external entailment judge: basic graded, span-copy, or both")
    p.add_argument("--model", type=str, default="claude-sonnet-4-6")
    p.add_argument("--out", type=argparse.FileType("w"), default=None)
    args = p.parse_args(argv)
    from benchmark.qa_runner import LeanClaudeCLILLM
    res = run(LeanClaudeCLILLM(model=args.model, timeout_s=60),
              per_class=args.per_class, seed=args.seed,
              consistency_k=args.consistency_k, judge=args.judge)
    res["model"] = args.model
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2))
    if args.out:
        json.dump(res, args.out, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["run", "main", "_entail_score", "_aurc"]
