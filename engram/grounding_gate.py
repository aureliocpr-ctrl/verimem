"""Grounding gate — external evidence-verification (see docs/EPISTEMIC_FAILURES_STUDY.md).

An external verifier scores how strongly evidence ENTAILS a claim (0–100), used to gate.
Where it actually pays off (the study's corrected, earned result):

* WRITE path — verifying a candidate FACT against its SOURCE before storing it. This is
  the moat: native NLI, no self-confidence baseline to beat. AUROC 0.971 (SNLI, R10) and
  0.992 (realistic wrong-source confabulations, R11). Use ``fact_grounding_score`` /
  ``should_store_fact``; wired as the L4 layer of ``anti_confab_gate.run_validation_gate``.
* ANSWER path — flagging a generated answer. Here the external check only TIES the model's
  own (free) verbalized confidence (R7 corrected: AUROC 0.812 == 0.812) and is DOMINATED by
  a cheap strict prompt end-to-end (R9). ``gate_answer`` / the ``ENGRAM_GROUNDING_GATE``
  hook exist for completeness but are NOT recommended over the strict prompt.

Honest history: earlier drafts claimed "confidence is at chance (R6, 0.494)" and "external
beats introspection (R7, 0.810 vs 0.705)". Both were ARTIFACTS of a tie-biased AUROC in the
bench (now fixed, average-rank Mann-Whitney). Corrected: confidence is over-confident but a
moderate signal (0.66–0.81), and the external verifier's real value is on the WRITE path.

Design: pure functions + a small ``GateResult``. The LLM is injected (anything with
``.complete(system, messages, *, model=, max_tokens=) -> obj.text``), so the gate logic
is unit-tested deterministically with a stub — no claude -p, no network. Threshold and
judge prompt are configurable (``ENGRAM_GROUNDING_THRESHOLD``, ``ENGRAM_GROUNDING_JUDGE``)
with data-derived defaults. Subscription only (O5): the judge is one extra ``claude -p``
call, no external API.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

# Default decision threshold (score >= threshold => grounded). Anchored on R7: the
# external judge scored sound answers ~96 and fabrications ~80; 85 sits between the
# classes. Tune per corpus via ``optimal_threshold`` on held-out labels, or override
# with ENGRAM_GROUNDING_THRESHOLD.
DEFAULT_THRESHOLD = 85.0

# WRITE-path admission threshold (source ⊢ candidate FACT) — DISTINCT from the answer-path
# 85 above, which is anchored on the R7 answer-distribution (sound ~96 / fabrication ~80).
# The fact-vs-source distribution is different and bimodal: measured on HaluMem-Medium
# (benchmark/halumem_admission_sweep.py, n=15 clean + 15 foreign-noise), grounded facts
# scored 42–100 while foreign noise scored a clean 0 — a wide gap at ~0→42. So 85 would
# reject ~⅔ of VALID (often abstractive) facts; a threshold anywhere in the gap admits 80%
# of clean facts and rejects 100% of noise at admission-precision 1.0. 40 sits safely in
# that gap. Override with ENGRAM_GROUNDING_WRITE_THRESHOLD. (n=15 — recalibrate at scale.)
WRITE_DEFAULT_THRESHOLD = 40.0

# Basic graded verifier (semantic, "judge meaning not word overlap, distractor -> 0").
_BASIC_SYSTEM = (
    "You judge GROUNDING. Given a context, a question, and a proposed answer, rate from "
    "0 to 100 how strongly the context LOGICALLY SUPPORTS that the proposed answer is "
    "the correct answer to the question. 100 = the context entails it unambiguously. "
    "50 = the context mentions related material but does not establish this specific "
    "answer. 0 = the context does not support it at all (irrelevant, contradicted, or "
    "only a superficially-similar distractor). Judge MEANING, not word overlap. Reply "
    "with exactly 'SCORE: N'.")

# Structural / span-copy variant: force the verifier to first COMMIT to an exact
# supporting span (or NONE) before scoring — chain-of-thought grounding that resists
# the surface-plausibility capture the basic judge can fall for.
_SPAN_SYSTEM = (
    "You verify GROUNDING by quotation. Given a context, a question, and a proposed "
    "answer: FIRST, on line 1, quote the EXACT span from the context that states the "
    "proposed answer is the answer to the question — or write NONE if no span states it "
    "(a span about a related but different thing is NONE). THEN, on line 2, write "
    "'SCORE: N': N=100 only if your quoted span explicitly states the answer; N=0 if you "
    "wrote NONE; N in 1–60 if the span is only related/partial. Judge meaning, not word "
    "overlap.")

_SCORE_RE = re.compile(r"score[:=]?\s*(\d{1,3})", re.I)
# Minimal abstention sentinels: the QA pipeline emits exactly "NO ANSWER"; we also
# catch the common phrasings so the gate never re-judges an answer that already declines.
_ABSTAIN_RE = re.compile(r"\bno answer\b|not (in the|mentioned|stated|provided)"
                         r"|cannot (be )?(answer|determin)|unanswerable", re.I)


def _is_abstention(text: str) -> bool:
    t = (text or "").strip()
    return not t or t.upper() == "NO ANSWER" or bool(_ABSTAIN_RE.search(t))


def _resolve_threshold(threshold: float | None) -> float:
    if threshold is not None:
        return float(threshold)
    env = os.environ.get("ENGRAM_GROUNDING_THRESHOLD", "").strip()
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    return DEFAULT_THRESHOLD


def _resolve_write_threshold() -> float:
    """Admission threshold for the WRITE path (source ⊢ fact). Calibrated lower than
    the answer-path default (see WRITE_DEFAULT_THRESHOLD). Override with
    ENGRAM_GROUNDING_WRITE_THRESHOLD; falls back to the general ENGRAM_GROUNDING_THRESHOLD
    if a deployment set only that, then to WRITE_DEFAULT_THRESHOLD."""
    env = os.environ.get("ENGRAM_GROUNDING_WRITE_THRESHOLD", "").strip()
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    general = os.environ.get("ENGRAM_GROUNDING_THRESHOLD", "").strip()
    if general:
        try:
            return float(general)
        except ValueError:
            pass
    return WRITE_DEFAULT_THRESHOLD


def _resolve_judge(judge: str | None) -> str:
    j = (judge or os.environ.get("ENGRAM_GROUNDING_JUDGE", "")).strip().lower()
    return j if j in ("basic", "span") else "basic"


def _resolve_backend() -> str:
    """Write-gate judge backend: 'claude' (default, injected llm — unchanged),
    'local' (distilled CE, engram.local_grounding; no llm call), or 'interactive'
    (ghost interactive-CLI sister, engram.interactive_judge; flat subscription,
    no claude -p — same 0-100 claude scale and threshold)."""
    b = os.environ.get("ENGRAM_GROUNDING_BACKEND", "").strip().lower()
    return b if b in ("claude", "local", "interactive") else "claude"


def grounding_score(llm: Any, question: str, evidence: str | list[str], answer: str, *,
                    judge: str | None = None, model: str | None = None) -> float:
    """External grounding score in [0, 100]: how strongly ``evidence`` supports that
    ``answer`` answers ``question``. One verifier call. Unreadable verdict -> 50 (the
    non-committal middle: a gate must not treat a parse failure as either grounded or
    fabricated)."""
    mode = _resolve_judge(judge)
    system = _SPAN_SYSTEM if mode == "span" else _BASIC_SYSTEM
    ev = evidence if isinstance(evidence, str) else "\n".join(e for e in evidence if e)
    resp = llm.complete(
        system,
        [{"role": "user", "content": f"Context: {ev}\n\nQuestion: {question}\n"
                                     f"Proposed answer: {answer}\n\nScore:"}],
        model=model, max_tokens=120 if mode == "span" else 12)
    m = _SCORE_RE.search(getattr(resp, "text", "") or "")
    return min(100.0, max(0.0, float(m.group(1)))) if m else 50.0


def is_grounded(score: float, *, threshold: float | None = None) -> bool:
    return score >= _resolve_threshold(threshold)


@dataclass
class GateResult:
    """Outcome of gating one answer. ``answer`` is the answer to USE (the original if
    grounded, else 'NO ANSWER'); ``raw_answer`` is what the generator produced."""

    answer: str
    score: float
    grounded: bool
    raw_answer: str


def gate_answer(llm: Any, question: str, evidence: str | list[str], answer: str, *,
                threshold: float | None = None, judge: str | None = None,
                model: str | None = None) -> GateResult:
    """Verify ``answer`` against ``evidence``; abstain if below threshold. An answer that
    already abstains (or is empty) passes through WITHOUT spending a verifier call — it
    asserts nothing to fabricate."""
    raw = (answer or "").strip()
    if _is_abstention(raw):
        return GateResult(answer="NO ANSWER", score=100.0, grounded=True, raw_answer=raw)
    thr = _resolve_threshold(threshold)
    score = grounding_score(llm, question, evidence, raw, judge=judge, model=model)
    grounded = score >= thr
    return GateResult(answer=raw if grounded else "NO ANSWER", score=score,
                      grounded=grounded, raw_answer=raw)


def optimal_threshold(scores: list[float], labels: list[int]) -> float:
    """Youden's J optimal cut on labeled scores (label 1 = sound). Returns the score
    value t maximizing TPR(>=t) − FPR(>=t) — the data-driven gate threshold."""
    cands = sorted(set(scores))
    if not cands:
        return DEFAULT_THRESHOLD
    pos = sum(1 for v in labels if v == 1)
    neg = len(labels) - pos
    best_t, best_j = cands[0], -2.0
    for t in cands:
        tp = sum(1 for s, lab in zip(scores, labels, strict=True) if lab == 1 and s >= t)
        fp = sum(1 for s, lab in zip(scores, labels, strict=True) if lab == 0 and s >= t)
        tpr = tp / pos if pos else 0.0
        fpr = fp / neg if neg else 0.0
        if (tpr - fpr) > best_j:
            best_j, best_t = tpr - fpr, t
    return float(best_t)


# ---- WRITE-PATH primitive: verify a candidate fact against its source -------------
# A memory's failure mode is confabulation ON WRITE — promoting a plausible INFERENCE to
# a stored 'fact' the source does not state. Unlike the answer path there is no free
# self-confidence baseline (the model verifies, it does not generate), and the task is
# native NLI (does the source entail the fact?), so the verifier should be strong here.
_FACT_SYSTEM = (
    "You verify whether a SOURCE supports a candidate FACT for storage in a memory. Rate "
    "0-100 how strongly the source LOGICALLY ENTAILS the fact. 100 = the source states or "
    "unambiguously entails the fact. 50 = the source is related but does NOT establish it "
    "(a plausible inference the source does not actually state — a confabulation). 0 = the "
    "source does not support it or contradicts it. Judge MEANING, not word overlap. Reply "
    "with exactly 'SCORE: N'.")


# Calibration note (A/B 2026-06-21, benchmark/halumem_gate_prompt_ab.py): an "abstraction-
# crediting" prompt variant was tested to cut the ~25-40% over-rejection of non-verbatim
# memories. It gave NO improvement (clean-admit 0.75 == 0.75, mean slightly lower) at equal
# 100% noise/confab rejection — FALSIFYING the "strictness artifact" hypothesis: the
# rejected facts genuinely aren't entailed by the source WITHIN the window, so the lever is
# more source context (raise the dialogue cap), not a looser judge. Variant not shipped.
# The ``system=`` override on fact_grounding_score is kept for future calibration A/Bs.


_SPAN_WORD = re.compile(r"\w+", re.UNICODE)
# CJK scripts have no word spaces — \w+ yields one blob per run, so word-set
# overlap carries no signal there; character bigrams do (G10, 2026-07-04:
# the old [a-z0-9]+ produced ZERO tokens on Russian/Chinese and the span
# selection degenerated to a blind prefix for every non-Latin language).
_SPAN_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")


def _span_tokens(text: str) -> set[str]:
    toks = set(_SPAN_WORD.findall(text))
    cjk = _SPAN_CJK.findall(text)
    toks.update(a + b for a, b in zip(cjk, cjk[1:]))
    return toks


def select_relevant_span(source: str, fact: str, *, budget: int) -> str:
    """Return the most fact-relevant portion of ``source``, up to ``budget`` chars, in the
    source's ORIGINAL order. If ``source`` already fits ``budget``, it is returned unchanged.
    Splits on lines (falling back to sentences for a single long line), ranks units by
    token-overlap with ``fact`` (ties → earlier first), greedily fills the budget, then
    restores order. Pure + deterministic — no embeddings.

    Why: the write-gate over-rejects abstractive facts when their supporting evidence falls
    OUTSIDE a truncated PREFIX window. Feeding the gate the relevant span instead lifts
    clean-admission ~0.70 → 0.80 at a FIXED char budget, noise-rejection unchanged ~100%
    (benchmark/halumem_gate_source_ab.py) — token-efficient grounding evidence."""
    if not source or len(source) <= budget:
        return source
    units = [u for u in source.split("\n") if u.strip()]
    if len(units) <= 1:
        units = [u.strip() for u in re.split(r"(?<=[.!?])\s+", source) if u.strip()]
    ft = _span_tokens(fact.lower())
    order = {u: i for i, u in enumerate(units)}

    def _overlap(u: str) -> int:
        return len(_span_tokens(u.lower()) & ft)

    ranked = sorted(units, key=lambda u: (_overlap(u), -order[u]), reverse=True)
    picked: list[str] = []
    n = 0
    for u in ranked:
        add = len(u) + 1
        if picked and n + add > budget:
            break
        picked.append(u)
        n += add
    picked.sort(key=lambda u: order.get(u, 0))
    return "\n".join(picked)[:budget]


def fact_grounding_score(llm: Any, source: str, fact: str, *,
                         model: str | None = None, system: str | None = None,
                         focus_budget: int | None = None) -> float:
    """Entailment of a standalone candidate FACT by its SOURCE, in [0, 100] — the
    write-path grounding primitive. Unreadable verdict -> 50 (non-committal). ``system``
    overrides the judge prompt (for A/B calibration); defaults to ``_FACT_SYSTEM``.
    ``focus_budget``: if set and the source exceeds it, score against the relevant SPAN
    (``select_relevant_span``) instead of the raw source — cuts over-rejection of facts whose
    evidence is outside a prefix window, at fewer tokens. None (default) = unchanged.
    With ``ENGRAM_GROUNDING_BACKEND=local`` the distilled CE judge scores instead and
    ``llm`` is not called (the local judge span-selects with its own trained budget
    when ``focus_budget`` is None); if the local model is unavailable the gate fails
    over to the injected llm (once-warned), never raises."""
    return fact_grounding_score_ex(llm, source, fact, model=model, system=system,
                                   focus_budget=focus_budget)[0]


def fact_grounding_score_ex(llm: Any, source: str, fact: str, *,
                            model: str | None = None, system: str | None = None,
                            focus_budget: int | None = None) -> tuple[float, str]:
    """Like ``fact_grounding_score`` but also returns WHICH judge actually scored
    ('local' or 'claude'). Score scales differ per judge (CE sigmoid vs claude 0-100
    prompt), so the admission cut MUST be resolved for the judge that scored — use
    ``resolve_write_threshold_for(backend_used)`` (the 2026-07-02 critic finding: the
    production L4 gate compared local-scale scores against the claude-scale 40)."""
    backend = _resolve_backend()
    if backend == "local":
        from engram.local_grounding import try_local_score
        r = try_local_score(source, fact, focus_budget=focus_budget)
        if r is not None:
            return r[0], "local"
    elif backend == "interactive":
        from engram.interactive_judge import try_interactive_score
        s = try_interactive_score(source, fact, focus_budget=focus_budget)
        if s is not None:
            # claude scale by construction (same rubric) -> claude-scale threshold
            return min(100.0, max(0.0, float(s))), "interactive"
    if focus_budget and source and len(source) > focus_budget:
        source = select_relevant_span(source, fact, budget=focus_budget)
    resp = llm.complete(
        system or _FACT_SYSTEM,
        [{"role": "user", "content": f"Source: {source}\n\nCandidate fact: {fact}\n\n"
                                     f"Score:"}],
        model=model, max_tokens=12)
    m = _SCORE_RE.search(getattr(resp, "text", "") or "")
    return (min(100.0, max(0.0, float(m.group(1)))) if m else 50.0), "claude"


_warned_uncalibrated = False


def resolve_write_threshold_for(backend_used: str) -> float:
    """The admission cut CONSISTENT with the judge that produced the score. Env
    overrides (`ENGRAM_GROUNDING_WRITE_THRESHOLD` / `ENGRAM_GROUNDING_THRESHOLD`)
    always win. For 'local' the fine-tune's calibrated cut (gate_config.json) applies;
    a local model shipping NO calibrated cut falls to the claude-scale default 40 with
    a once-per-process warning — visible, not silent (admission rates uncalibrated)."""
    env_set = (os.environ.get("ENGRAM_GROUNDING_WRITE_THRESHOLD", "").strip()
               or os.environ.get("ENGRAM_GROUNDING_THRESHOLD", "").strip())
    if env_set or backend_used != "local":
        return _resolve_write_threshold()
    from engram.local_grounding import get_local_threshold
    t = get_local_threshold()
    if t is not None:
        return float(t)
    global _warned_uncalibrated
    if not _warned_uncalibrated:
        _warned_uncalibrated = True
        import warnings
        warnings.warn(
            "local grounding judge scored but its model dir ships no gate_config.json "
            "threshold — admission is uncalibrated (claude-scale default "
            f"{WRITE_DEFAULT_THRESHOLD} applied to a CE-scale score)",
            RuntimeWarning, stacklevel=2)
    return _resolve_write_threshold()


def should_store_fact(llm: Any, source: str, fact: str, *,
                      threshold: float | None = None,
                      model: str | None = None,
                      focus_budget: int | None = None) -> tuple[bool, float]:
    """Write-path gate: store the fact only if the source grounds it above threshold.
    Returns (store?, score). The anti-confabulation guard for the memory. When no explicit
    threshold is given, uses the WRITE-path default (calibrated lower than the answer-path
    85 — see WRITE_DEFAULT_THRESHOLD), consistent with the L4 gate in run_validation_gate.
    ``focus_budget`` (or env ENGRAM_GROUNDING_FOCUS_CHARS) span-selects a long source to the
    fact-relevant window before scoring — cuts over-rejection of abstractive facts."""
    fb = focus_budget
    if fb is None:
        env = os.environ.get("ENGRAM_GROUNDING_FOCUS_CHARS", "").strip()
        fb = int(env) if env.isdigit() else None
    # score AND threshold must come from the same judge: the fine-tune ships its
    # calibrated cut (gate_config.json) on the CE sigmoid scale, where the claude-scale
    # default 40 is meaningless — and vice versa on fail-over to the injected llm.
    score, used = fact_grounding_score_ex(llm, source, fact, model=model,
                                          focus_budget=fb)
    thr = float(threshold) if threshold is not None else resolve_write_threshold_for(used)
    return score >= thr, score


# PROVENANCE-on-write (Ph1 innovation): not just a score, but WHICH span grounds the fact
# (or NONE). Forces the verifier to commit to a quotation before scoring — and gives the
# memory an auditable provenance pointer to store alongside each fact.
_FACT_SPAN_SYSTEM = (
    "Verify a candidate FACT against a SOURCE for storage in a memory. On line 1, quote the "
    "EXACT sentence from the source that STATES the fact — or write NONE if no sentence "
    "states it (a sentence about a related-but-different thing is NONE). On line 2, write "
    "'SCORE: N' (0-100 how strongly the source entails the fact; N=0 if you wrote NONE). "
    "Judge MEANING, not word overlap.")


def fact_grounding_span(llm: Any, source: str, fact: str, *,
                        model: str | None = None) -> dict[str, Any]:
    """Provenance verification: returns ``{"score": float, "span": str|None}`` — the score
    AND the exact source span that grounds the fact (None if unsupported). Unreadable
    verdict -> score 50, span None."""
    resp = llm.complete(
        _FACT_SPAN_SYSTEM,
        [{"role": "user", "content": f"Source: {source}\n\nCandidate fact: {fact}\n\n"
                                     f"Quote then score:"}],
        model=model, max_tokens=200)
    text = (getattr(resp, "text", "") or "").strip()
    m = _SCORE_RE.search(text)
    score = min(100.0, max(0.0, float(m.group(1)))) if m else 50.0
    # the span is the text BEFORE the SCORE line; NONE (any case) -> no span
    head = text[:m.start()].strip() if m else text
    head = head.splitlines()[0].strip() if head else ""
    span = None if (not head or head.strip().upper().rstrip(".") == "NONE") else head
    return {"score": score, "span": span}


__all__ = ["DEFAULT_THRESHOLD", "GateResult", "grounding_score", "is_grounded",
           "gate_answer", "optimal_threshold", "fact_grounding_score",
           "should_store_fact", "fact_grounding_span", "select_relevant_span"]
