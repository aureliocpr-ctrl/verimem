"""QA-accuracy eval for Engram benchmarks — the leaderboard-comparable axis.

Retrieval recall@k (``longmemeval_runner`` / ``locomo_runner``) measures whether
the gold evidence is RETRIEVED. The number competitors actually quote (mem0's
LoCoMo J-score, LongMemEval QA-accuracy) is downstream of that: given the
retrieved context, does the system ANSWER correctly? This module composes that
second stage — answer(LLM) then judge(LLM, vs gold) — with the LLM and judge
INJECTED so:

  * tests run hermetically with ``engram.llm.MockLLM`` (no network, no API key);
  * the live run uses ``engram.llm.ClaudeCLILLM`` (``claude -p``) — subscription
    only, ZERO external API key (CLAUDE.md O5). Honest asterisk: our judge is
    Claude; mem0 / LongMemEval judge with GPT-4, so the absolute number is
    comparable in METHOD but not judge-identical — declared, not hidden.

Discipline mirrored from ``engram.tier2_judge``: the judge only LABELS
correctness, and an AMBIGUOUS / unparseable verdict fails SAFE to INCORRECT — we
never inflate accuracy on a verdict we could not read.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Protocol

_ANSWER_SYSTEM = (
    "You answer a question using ONLY the provided memory/context. "
    "Be concise: reply with just the answer, no explanation. "
    "If the question asks for a LIST or for multiple things, enumerate ALL of "
    "the relevant items you can find across the context, comma-separated. "
    "When the question asks WHEN something happened, give the ABSOLUTE date "
    "(resolve relative references like 'yesterday'/'last week' using the "
    "[timestamp] prefixes in the context), never a relative expression. "
    "If the context does not contain the answer, reply exactly: NO ANSWER."
)
# STRICT anti-hallucination variant (Study A: SQuAD-v2 fabrication 0.42 -> 0.12).
# Env-gated (ENGRAM_ANSWER_STRICT=1) so it can be validated in the QA pipeline
# before becoming default — the move from "lever measured in isolation" to "cure
# deployed", with the over-abstention tradeoff measured on real answerable QA.
_ANSWER_SYSTEM_STRICT = _ANSWER_SYSTEM + (
    " CRITICAL: answer ONLY if the answer is EXPLICITLY present in the context. "
    "Do not infer, guess, or use outside knowledge; a related or plausible-sounding "
    "phrase is NOT the answer. When in doubt, reply exactly: NO ANSWER."
)

# VERIFICATION-AWARE variant (iter 41, 2026-07-05): false-premise questions
# (HaluMem Memory-Conflict style — "did X do Y with his partner?" when he has no
# partner) need a premise-check + explicit correction; the strict minimal-span /
# NO ANSWER style forfeits them at the judge even when retrieval is perfect
# (evidence recall@5 was 40/40 while accuracy sat at 0.15). Measured on the
# reconciled store: Memory-Conflict QA 0.15 -> 0.65 (n=40), overall 0.1591 ->
# 0.5909 (n=44). Still GROUNDED: context-only, no outside knowledge, and the
# NO ANSWER abstention is preserved — the anti-hallucination contract stands.
# Env-gated (ENGRAM_ANSWER_VERIFY=1), default OFF.
_ANSWER_SYSTEM_VERIFY = (
    "Answer from the CONTEXT only. The question may contain a FALSE ASSUMPTION: "
    "first check every claim inside the question against the context. "
    "If a claim contradicts the context, answer 'No' and state the correct fact "
    "from the context in the same sentence. "
    "If the context confirms the claim, answer 'Yes' plus the key fact. "
    "If the context says nothing about it, reply exactly: NO ANSWER. "
    "Never use outside knowledge; one short sentence."
)


# DECLARED-INFERENCE variant (iter 79, exp4 2026-07-06): the e2e Basic
# bottleneck is the ANSWERER — the fact is retrieved (hit 1.0) but the strict
# answerer, faced with the gold fact amid distractors, either abstains or picks
# a neighbour. A THIRD way: infer when the answer FOLLOWS from the context but
# DECLARE the single-step derivation. Measured on read-path u0 (exp4): both
# Generalization 0.581 -> 0.645 AND the abstention canary 0.897 -> 0.974 rose —
# no trade-off, fabrications went DOWN. Opt-in ENGRAM_ANSWER_MODE=declared;
# small-n, not yet the default. Abstention preserved.
_ANSWER_SYSTEM_DECLARED = (
    "Answer from the CONTEXT only. Rules:\n"
    "- If the answer is stated, give it directly (short).\n"
    "- If the answer is NOT stated but clearly FOLLOWS from facts in the "
    "context, you MAY infer it — but you MUST declare the derivation: "
    "'Inferred from: <fact A> + <fact B>'. Only single-step, conservative "
    "inferences; never stack assumptions.\n"
    "- If the question contains a false assumption, answer 'No' and state "
    "the correct fact.\n"
    "- If the context neither states nor supports it, reply exactly: NO ANSWER.\n"
    "Never use outside knowledge; at most two short sentences."
)


def _answer_system() -> str:
    import os
    # Declared-inference mode (opt-in): infer-with-declared-derivation, the
    # answerer lever for the e2e Basic bottleneck (exp4). Highest precedence.
    if os.environ.get("ENGRAM_ANSWER_MODE", "").strip().lower() == "declared":
        return _ANSWER_SYSTEM_DECLARED
    # Verification-aware mode (opt-in): premise-check + correction for
    # false-premise questions. Measured 4.3x on Memory-Conflict (0.15 -> 0.65).
    if os.environ.get("ENGRAM_ANSWER_VERIFY", "").strip().lower() in (
        "1", "on", "true", "yes",
    ):
        return _ANSWER_SYSTEM_VERIFY
    # Strict anti-hallucination is now the DEFAULT — validated net-win: LoCoMo QA
    # 0.813 -> 0.827 (cat5 adversarial 0.88->0.94, cat1 0.53->0.67, cat4 open-domain
    # UNCHANGED = no over-abstention damage; only cat2 temporal -8pp), SQuAD-v2
    # fabrication 0.42 -> 0.12. Opt OUT with ENGRAM_ANSWER_STRICT=0.
    if os.environ.get("ENGRAM_ANSWER_STRICT", "").strip().lower() in (
        "0", "off", "false", "no",
    ):
        return _ANSWER_SYSTEM
    return _ANSWER_SYSTEM_STRICT
_JUDGE_SYSTEM = (
    "You are a strict grader. Decide whether the PREDICTED answer matches the "
    "GOLD answer for the QUESTION. Accept paraphrases and equivalent values "
    "(dates, names, numbers) that mean the same thing; reject answers that add "
    "wrong facts or miss the asked value. Reply with exactly one word: "
    "CORRECT or INCORRECT."
)
# Fair/standard rubric (what the public LoCoMo / LongMemEval LLM-judges use): a
# semantically-correct answer counts even if phrased differently or slightly
# incomplete — but a contradiction or wrong-point answer is still INCORRECT. This
# is NOT a rubber stamp; it just stops penalising correct-meaning paraphrases.
_JUDGE_SYSTEM_FAIR = (
    "You are a fair grader for a conversational-memory QA benchmark. The "
    "PREDICTED answer is CORRECT if it conveys the same core information as the "
    "GOLD answer: accept paraphrases, equivalent values (dates/names/numbers), "
    "extra correct context, and minor missing items as long as the main asked "
    "value is present. Mark INCORRECT only if it contradicts the gold, answers a "
    "different question, or misses the main point. Reply with exactly one word: "
    "CORRECT or INCORRECT."
)

# Adversarial / unanswerable QA (LoCoMo category 5: gold answer is None). The
# correct behaviour is to ABSTAIN, not to fabricate — this is exactly the
# anti-confabulation property Engram exists for, so it must be scored on
# abstention, not string-matched against a missing gold.
_JUDGE_ADVERSARIAL = (
    "The QUESTION is likely UNANSWERABLE from the conversation (a trick / "
    "false-premise question). The PREDICTED answer is CORRECT if it ABSTAINS — "
    "states the information is not available / not mentioned / unknown, or "
    "rejects the false premise. It is INCORRECT only if it fabricates a specific "
    "answer as if it were a known fact. Reply with exactly one word: CORRECT or "
    "INCORRECT."
)

_POS_FIRST = frozenset({"correct", "yes", "true", "right"})
_NEG_FIRST = frozenset({"incorrect", "no", "false", "wrong"})


class _LLM(Protocol):
    def complete(  # noqa: D401, ANN101
        self, system: str, messages: list[dict[str, str]],
        *args: Any, **kwargs: Any,
    ) -> Any: ...


def parse_judge_label(text: str) -> bool:
    """True iff the judge said CORRECT.

    Fail-safe: an empty or ambiguous verdict returns False — accuracy is never
    inflated on a verdict we cannot read. Handles the compliant one-word case,
    prose ("the answer is correct."), and explicit negation ("not correct").
    """
    t = (text or "").strip().lower()
    if not t:
        return False
    first = re.split(r"[^a-z]+", t, maxsplit=1)[0]
    if first in _NEG_FIRST:
        return False
    if first in _POS_FIRST:
        return True
    # 'incorrect' contains 'correct', and "not correct" negates a positive —
    # resolve negatives BEFORE the positive substring check.
    if re.search(r"\bnot\b[^.]*\b(correct|right|true)\b", t):
        return False
    if "incorrect" in t or "wrong" in t or re.search(r"\bno\b", t):
        return False
    if "correct" in t or re.search(r"\byes\b", t):
        return True
    return False


def _context_block(context: list[str]) -> str:
    return "\n".join(f"- {c}" for c in context if c)


def build_answer_prompt(
    question: str, context: list[str],
) -> tuple[str, list[dict[str, str]]]:
    """Build the (system, messages) for the answering LLM. Pure."""
    user = (f"Memory/context:\n{_context_block(context)}\n\n"
            f"Question: {question}\nAnswer:")
    return _answer_system(), [{"role": "user", "content": user}]


def build_judge_prompt(
    question: str, gold: str, predicted: str, *, fair: bool = False,
) -> tuple[str, list[dict[str, str]]]:
    """Build the (system, messages) for the grading LLM. Pure.

    ``fair=True`` uses the standard semantic rubric (paraphrase / minor-omission
    tolerant, the one public LoCoMo/LongMemEval judges use); default is the
    stricter exact-value rubric.
    """
    system = _JUDGE_SYSTEM_FAIR if fair else _JUDGE_SYSTEM
    user = (f"QUESTION: {question}\nGOLD: {gold}\nPREDICTED: {predicted}\n\n"
            f"Is the PREDICTED answer correct? Reply CORRECT or INCORRECT.")
    return system, [{"role": "user", "content": user}]


def _grounding_gate_on() -> bool:
    import os
    return os.environ.get("ENGRAM_GROUNDING_GATE", "").strip().lower() in (
        "1", "on", "true", "yes")


def answer_question(
    llm: _LLM, question: str, context: list[str], *,
    model: str | None = None, max_tokens: int = 256,
) -> str:
    """Ask ``llm`` to answer ``question`` from ``context``; return its text.

    When ``ENGRAM_GROUNDING_GATE`` is set, the answer is verified against the context by
    an EXTERNAL grounding check (R6/R7: the model's own confidence is at chance for
    flagging fabrication, so verification is externalized) and replaced with 'NO ANSWER'
    if the evidence does not support it. Opt-in: it spends one extra verifier call per
    answered question, and is validated in the pipeline before becoming default."""
    system, messages = build_answer_prompt(question, context)
    resp = llm.complete(system, messages, model=model, max_tokens=max_tokens)
    ans = (getattr(resp, "text", "") or "").strip()
    if ans and _grounding_gate_on():
        from engram.grounding_gate import gate_answer
        ans = gate_answer(llm, question, context, ans, model=model).answer
    return ans


_GROUNDED_ANSWER_SYSTEM = (
    "Answer the question using the provided facts. Each fact may be tagged [grounding N/100] = how "
    "strongly its SOURCE was verified to entail it at write time (higher = more trustworthy). PREFER "
    "high-grounding facts. Treat a fact whose grounding is below the reliability floor as UNRELIABLE: "
    "do not assert it; if only low-grounding facts are relevant, reply exactly: NO ANSWER. Untagged "
    "facts have no trust signal — use normal judgement. Be concise: reply with just the answer."
)


def answer_question_grounded(
    llm: _LLM, question: str, facts: list[tuple[str, float | None]], *,
    model: str | None = None, max_tokens: int = 256, floor: float = 40.0,
) -> str:
    """Provenance-conditioned answering — the moonshot's validated mechanism (controlled A/B
    2026-06-20: hallucination 0.33->0.00, correct 0.00->1.00 when a true fact's write-time
    grounding score lets the answerer reject a plausible low-grounding distractor).

    ``facts`` = ``[(text, grounding_score | None), ...]``. Facts WITH a score are tagged
    ``[grounding N/100]`` and the answerer prefers high / refuses below ``floor``; ``None``-scored
    facts are shown plain (no signal). This is the read-path use of the write-time grounding score
    now persisted on the Fact (schema v12) and surfaced by hippo_facts_recall — a trust coordinate
    no competitor (mem0/Zep/Letta) computes. Falls back to flat behaviour when no fact is scored.
    """
    lines: list[str] = []
    for text, gs in facts:
        lines.append(text if gs is None else f"[grounding {float(gs):.0f}/100] {text}")
    system = _GROUNDED_ANSWER_SYSTEM.replace("reliability floor", f"reliability floor of {floor:.0f}")
    user = "Facts:\n" + "\n".join(lines) + f"\n\nQuestion: {question}"
    resp = llm.complete(system, [{"role": "user", "content": user}],
                        model=model, max_tokens=max_tokens)
    return (getattr(resp, "text", "") or "").strip()


def judge_correct(
    judge_llm: _LLM, question: str, gold: str, predicted: str, *,
    model: str | None = None, fair: bool = False,
) -> bool:
    """Grade ``predicted`` against ``gold``. An empty prediction is INCORRECT by
    construction — no judge call is spent on it (fail-safe + frugal)."""
    if not (predicted or "").strip():
        return False
    system, messages = build_judge_prompt(question, gold, predicted, fair=fair)
    resp = judge_llm.complete(system, messages, model=model, max_tokens=8)
    return parse_judge_label(getattr(resp, "text", "") or "")


def judge_abstention(
    judge_llm: _LLM, question: str, predicted: str, *, model: str | None = None,
) -> bool:
    """Grade an UNANSWERABLE (adversarial) question: CORRECT iff the prediction
    abstains / rejects the false premise rather than fabricating. An empty
    prediction counts as abstention (it asserts nothing false)."""
    if not (predicted or "").strip():
        return True  # said nothing -> fabricated nothing -> correct abstention
    resp = judge_llm.complete(
        _JUDGE_ADVERSARIAL,
        [{"role": "user",
          "content": f"QUESTION: {question}\nPREDICTED: {predicted}\n\n"
                     f"Reply CORRECT or INCORRECT."}],
        model=model, max_tokens=8)
    return parse_judge_label(getattr(resp, "text", "") or "")


def score_qa(
    records: list[dict[str, Any]], *, answer_llm: _LLM, judge_llm: _LLM,
    answer_model: str | None = None, judge_model: str | None = None,
    on_progress: Any = None, fair_judge: bool = False,
) -> dict[str, Any]:
    """Score QA-accuracy over ``records`` ``[{id, question, gold, context,
    category}]``.

    Per record: answer(LLM) -> judge(LLM vs gold) -> ``correct`` bool. An LLM
    error on either call marks the record INCORRECT + errored (fail-safe) and the
    run continues — one flaky call must not abort a long sweep. Returns overall
    accuracy + per-category breakdown + per-record details.
    """
    per_cat: dict[str, list[bool]] = defaultdict(list)
    n_correct = 0
    n_errors = 0
    details: list[dict[str, Any]] = []
    total = len(records)
    for i, rec in enumerate(records):
        question = str(rec.get("question", ""))
        gold = str(rec.get("gold", ""))
        category = str(rec.get("category", "?"))
        context = rec.get("context") or []
        predicted = ""
        errored = False
        try:
            predicted = answer_question(
                answer_llm, question, context, model=answer_model)
            if rec.get("adversarial"):
                correct = judge_abstention(
                    judge_llm, question, predicted, model=judge_model)
            else:
                correct = judge_correct(
                    judge_llm, question, gold, predicted, model=judge_model,
                    fair=fair_judge)
        except Exception:  # noqa: BLE001 — one bad call must not abort the run
            errored = True
            correct = False
        if errored:
            n_errors += 1
        if correct:
            n_correct += 1
        per_cat[category].append(correct)
        details.append({
            "id": rec.get("id"), "category": category,
            "predicted": predicted, "correct": correct, "errored": errored,
        })
        if on_progress is not None:
            on_progress(i + 1, total)
    per_category = {
        c: {"n": len(v), "accuracy": round(sum(v) / len(v), 4) if v else 0.0}
        for c, v in sorted(per_cat.items())
    }
    return {
        "n": total,
        "n_correct": n_correct,
        "n_errors": n_errors,
        "accuracy": round(n_correct / total, 4) if total else 0.0,
        "per_category": per_category,
        "details": details,
    }


__all__ = [
    "parse_judge_label",
    "build_answer_prompt",
    "build_judge_prompt",
    "answer_question",
    "judge_correct",
    "judge_abstention",
    "score_qa",
]
