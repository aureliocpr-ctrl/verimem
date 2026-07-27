"""QA-accuracy eval — the leaderboard-comparable axis (answer -> LLM judge).

Retrieval recall@k says whether the gold evidence is FOUND; this says whether the
system ANSWERS correctly given the retrieved context — the J-score axis mem0 /
LongMemEval report. The LLM and judge are INJECTED, so these tests run hermetic
with MockLLM (no network, no API key); the live run uses claude -p (O5).
"""
from __future__ import annotations

from benchmark.qa_eval import (
    answer_question,
    build_answer_prompt,
    build_judge_prompt,
    judge_abstention,
    judge_correct,
    parse_judge_label,
    score_qa,
)
from verimem.llm import MockLLM


def test_judge_abstention_empty_prediction_is_correct() -> None:
    # said nothing -> fabricated nothing -> a correct abstention (no judge call)
    j = MockLLM(scripted=[])
    assert judge_abstention(j, "Who?", "") is True
    assert j.calls == []


def test_judge_abstention_uses_llm() -> None:
    # the normal path carries the context (the grounded rubric); the blind one
    # is reachable only by saying so — see
    # test_adversarial_judging_without_context_must_be_explicit
    ctx = ["Ann: it was me who filed it."]
    assert judge_abstention(MockLLM(scripted=["CORRECT"]), "Who?",
                            "I don't know", context=ctx) is True
    assert judge_abstention(MockLLM(scripted=["INCORRECT"]), "Who?",
                            "It was Bob.", context=ctx) is False


def test_score_qa_adversarial_record_scored_on_abstention() -> None:
    rec = [{"id": "a", "question": "q", "gold": "", "context": ["c"],
            "category": "5", "adversarial": True}]
    # fabricates -> abstention judge says INCORRECT
    r1 = score_qa(rec, answer_llm=MockLLM(scripted=["It was definitely Bob."]),
                  judge_llm=MockLLM(scripted=["INCORRECT"]))
    assert r1["n_correct"] == 0
    # abstains -> CORRECT
    r2 = score_qa(rec, answer_llm=MockLLM(scripted=["NO ANSWER"]),
                  judge_llm=MockLLM(scripted=["CORRECT"]))
    assert r2["n_correct"] == 1


def test_parse_judge_label_compliant() -> None:
    assert parse_judge_label("CORRECT") is True
    assert parse_judge_label("INCORRECT") is False
    assert parse_judge_label("yes") is True
    assert parse_judge_label("no") is False


def test_parse_judge_label_prose_and_negation() -> None:
    assert parse_judge_label("The answer is correct.") is True
    assert parse_judge_label("The answer is incorrect.") is False
    # negation must NOT be read as positive just because 'correct' appears
    assert parse_judge_label("This is not correct") is False


def test_parse_judge_label_ambiguous_is_failsafe_false() -> None:
    # anti-confab: a verdict we cannot read must never inflate accuracy
    assert parse_judge_label("") is False
    assert parse_judge_label("maybe") is False


def test_build_answer_prompt_contains_context_and_question() -> None:
    system, messages = build_answer_prompt("What is X?", ["fact one", "fact two"])
    blob = system + " " + " ".join(m["content"] for m in messages)
    assert "fact one" in blob and "fact two" in blob
    assert "What is X?" in blob


def test_build_judge_prompt_contains_gold_and_predicted() -> None:
    system, messages = build_judge_prompt("Q?", "GOLD", "PRED")
    blob = system + " " + " ".join(m["content"] for m in messages)
    assert "GOLD" in blob and "PRED" in blob and "Q?" in blob


def test_build_judge_prompt_fair_vs_strict() -> None:
    s_strict, _ = build_judge_prompt("q", "g", "p", fair=False)
    s_fair, _ = build_judge_prompt("q", "g", "p", fair=True)
    assert "strict grader" in s_strict.lower()
    assert "fair grader" in s_fair.lower()


def test_answer_question_uses_llm() -> None:
    llm = MockLLM(scripted=["Business Administration"])
    out = answer_question(llm, "What degree?", ["...context..."])
    assert out == "Business Administration"


def test_judge_correct_true_false() -> None:
    assert judge_correct(MockLLM(scripted=["CORRECT"]), "Q", "g", "p") is True
    assert judge_correct(MockLLM(scripted=["INCORRECT"]), "Q", "g", "p") is False


def test_judge_correct_empty_prediction_is_false_without_calling_judge() -> None:
    # an empty answer is incorrect by construction — don't even spend a judge call
    judge = MockLLM(scripted=["CORRECT"])
    assert judge_correct(judge, "Q", "gold", "") is False
    assert judge.calls == []  # judge never consulted


def test_score_qa_accuracy_and_per_category() -> None:
    records = [
        {"id": "1", "question": "q1", "gold": "a", "context": ["c"], "category": "single"},
        {"id": "2", "question": "q2", "gold": "b", "context": ["c"], "category": "single"},
        {"id": "3", "question": "q3", "gold": "c", "context": ["c"], "category": "multi"},
    ]
    answer_llm = MockLLM(scripted=["a", "wrong", "c"])
    judge_llm = MockLLM(scripted=["CORRECT", "INCORRECT", "CORRECT"])
    res = score_qa(records, answer_llm=answer_llm, judge_llm=judge_llm)
    assert res["n"] == 3
    assert res["n_correct"] == 2
    assert res["accuracy"] == round(2 / 3, 4)
    assert res["per_category"]["single"]["accuracy"] == 0.5
    assert res["per_category"]["multi"]["accuracy"] == 1.0


def test_score_qa_empty() -> None:
    res = score_qa([], answer_llm=MockLLM(), judge_llm=MockLLM())
    assert res["n"] == 0 and res["accuracy"] == 0.0


def test_score_qa_survives_llm_error() -> None:
    class BoomLLM:
        def complete(self, *a, **k):  # noqa: ANN002, ANN003
            raise RuntimeError("boom")

        def supports_tools(self) -> bool:
            return False

    records = [{"id": "1", "question": "q", "gold": "a", "context": ["c"], "category": "x"}]
    res = score_qa(records, answer_llm=BoomLLM(), judge_llm=MockLLM(scripted=["CORRECT"]))
    assert res["n"] == 1 and res["n_correct"] == 0 and res["n_errors"] == 1


def test_answer_system_verify_env(monkeypatch) -> None:
    """ENGRAM_ANSWER_VERIFY=1 -> the verification-aware answerer (premise-check +
    correction from context; measured Memory-Conflict QA 0.15 -> 0.65 on the
    reconciled store). Must stay GROUNDED (context-only + NO ANSWER) so the
    anti-hallucination property is preserved. Default OFF -> strict unchanged."""
    from benchmark.qa_eval import _answer_system

    monkeypatch.setenv("ENGRAM_ANSWER_VERIFY", "1")
    verify = _answer_system()
    assert "FALSE ASSUMPTION" in verify, "premise-check instruction present"
    assert "NO ANSWER" in verify, "grounded abstention preserved"

    monkeypatch.delenv("ENGRAM_ANSWER_VERIFY")
    default = _answer_system()
    assert "FALSE ASSUMPTION" not in default, "default unchanged (strict)"
    assert "EXPLICITLY present" in default


def test_answer_mode_declared_inference_opt_in(monkeypatch) -> None:
    """Iter 79: the e2e Basic bottleneck is the ANSWERER (retrieval-hit 1.0).
    exp4 validated a declared-inference answer mode (Generalization+Boundary
    both up). Ship it as an opt-in answer mode; default behaviour unchanged."""
    import benchmark.qa_eval as qa

    monkeypatch.delenv("ENGRAM_ANSWER_MODE", raising=False)
    monkeypatch.delenv("ENGRAM_ANSWER_VERIFY", raising=False)
    monkeypatch.delenv("ENGRAM_ANSWER_STRICT", raising=False)
    default = qa._answer_system()
    assert "Inferred from" not in default, "default is unchanged (strict)"

    monkeypatch.setenv("ENGRAM_ANSWER_MODE", "declared")
    declared = qa._answer_system()
    assert "Inferred from" in declared, "declared mode exposes the derivation rule"
    assert "NO ANSWER" in declared, "abstention preserved (anti-confab contract)"


def test_answer_mode_adaptive_opt_in(monkeypatch) -> None:
    """Production A/B (abtest_prod_v2 n=111, abtest_adaptive_v3 n=90): declared
    lifts Generalization (+22.5pp) but BREAKS Boundary abstention (1.0 -> 0.71) =
    the moat. The ADAPTIVE mode GATES inference on whether the context supports an
    answer -> keeps Boundary at 1.0 AND still lifts Generalization (strict 0.394 ->
    adaptive 0.455, with 0 answers lost to over-caution). Opt-in; default strict
    unchanged. Sacred criterion (abstention) preserved."""
    import benchmark.qa_eval as qa

    monkeypatch.delenv("ENGRAM_ANSWER_MODE", raising=False)
    monkeypatch.delenv("ENGRAM_ANSWER_VERIFY", raising=False)
    monkeypatch.delenv("ENGRAM_ANSWER_STRICT", raising=False)
    default = qa._answer_system()
    assert "supports an answer" not in default.lower(), "default is unchanged (strict)"

    monkeypatch.setenv("ENGRAM_ANSWER_MODE", "adaptive")
    adaptive = qa._answer_system()
    assert "supports an answer" in adaptive.lower(), "adaptive gates inference on context support"
    assert "NO ANSWER" in adaptive, "abstention preserved (moat: Boundary stays 1.0)"


def test_answer_mode_adaptive_fp_opt_in(monkeypatch) -> None:
    """adaptive_fp = adaptive + false-premise handling. The e2e overall (n=173)
    showed declared crushes Memory Conflict (0.775 vs adaptive 0.55) via its
    false-assumption rule, which adaptive lacks. adaptive_fp grafts that rule onto
    adaptive to lift Conflict WHILE keeping the context-gate + Boundary abstention
    (the moat). Opt-in; default strict unchanged."""
    import benchmark.qa_eval as qa

    monkeypatch.setenv("ENGRAM_ANSWER_MODE", "adaptive_fp")
    fp = qa._answer_system()
    assert "supports an answer" in fp.lower(), "keeps the adaptive context-gate"
    assert "false assumption" in fp.lower(), "adds false-premise correction"
    assert "NO ANSWER" in fp, "abstention preserved (moat)"


def test_every_answer_prompt_declares_the_response_language() -> None:
    """LoCoMo strict (n=150, 2026-07-25): two answers came back IN ITALIAN on an
    English bench — 5:41 (graded CORRECT despite the language flip) and 9:200 (a
    cat5 fabrication, in Italian). No answer prompt constrained the response
    language, so the CLI answerer inherits whatever locale the host environment
    carries. The contract: EVERY answer-system prompt pins the response to the
    question's language — a new prompt variant cannot silently drop it."""
    import benchmark.qa_eval as qa

    prompts = {
        name: val for name, val in vars(qa).items()
        if (name.startswith("_ANSWER_SYSTEM") or name == "_GROUNDED_ANSWER_SYSTEM")
        and isinstance(val, str)
    }
    assert len(prompts) >= 6, f"expected the full prompt family, got {sorted(prompts)}"
    for name, prompt in prompts.items():
        assert "language of the question" in prompt, (
            f"{name} does not pin the response language")


def test_the_adversarial_judge_is_given_the_context_it_needs() -> None:
    """It graded blind, and that is why it was wrong three times out of three.

    An adversarial (unanswerable) question has gold=None, so the only evidence
    for whether a rejection is FOUNDED is the retrieved context — and
    judge_abstention never received it. Its own rubric calls a rejection of the
    false premise CORRECT, but with question+prediction alone 'No, it is Jon
    not Gina' is indistinguishable from an invention, so the judge defaulted to
    INCORRECT. Measured on LoCoMo 2026-07-27: all three cat5 cases declared
    'lost' (1:86, 5:132, 9:195) were corrections verified word for word in the
    dataset — Jon says 'I'm after Marley flooring', Audrey says 'I set up a
    doggy play area', Calvin says 'I usually watch music videos, concerts and
    documentaries'. The moat had not cracked; the ruler was blind.
    """
    import benchmark.qa_eval as qa

    system, messages = qa.build_adversarial_judge_prompt(
        "What flooring is Gina looking for?",
        "No. It is Jon, not Gina, who wants Marley flooring.",
        context=["Jon: I'm after Marley flooring, which dance studios use."],
    )
    corpo = messages[0]["content"]
    assert "Marley flooring, which dance studios use" in corpo, (
        "the judge must see the CONTEXT: it is the only evidence that separates "
        "a founded correction from a fabrication")
    assert "supported by the CONTEXT" in system or "supports" in system, (
        "the rubric must name the criterion the context makes decidable")


def test_score_qa_passes_the_context_to_the_adversarial_judge() -> None:
    """The cure only counts at the CALL SITE (the 26/07 lesson): score_qa must
    hand the context over, or the fixed judge grades blind anyway."""
    import benchmark.qa_eval as qa

    visti: list[dict] = []

    class _Spia:
        def complete(self, system, messages, **kw):
            visti.append({"system": system, "user": messages[0]["content"]})
            class R:
                text = "CORRECT"
            return R()

    rec = [{"id": "1:86", "question": "What flooring is Gina looking for?",
            "gold": "", "category": "5", "adversarial": True,
            "context": ["Jon: I'm after Marley flooring."]}]
    spia = _Spia()
    qa.score_qa(rec, answer_llm=spia, judge_llm=spia)
    giudizi = [v for v in visti if "PREDICTED" in v["user"]]
    assert giudizi, "nessuna chiamata al giudice"
    assert "Marley flooring" in giudizi[-1]["user"], (
        "score_qa non passa il contesto al giudice adversarial")


def test_the_grounded_rubric_judges_the_whole_answer_not_just_the_abstention() -> None:
    """Two independent adversarial reviews (deepseek-v4-pro, glm-5.2) found the
    same hole in the grounded rubric I shipped hours earlier: 'CORRECT if it
    ABSTAINS ... OR if it rejects the premise with supported facts' is satisfied
    by the abstention ALONE, so whatever is appended after it is never examined.

    Their counterexample: 'The context does not mention techlash syndrome.
    However, teenagers who overuse technology experience anxiety and
    irritability.' Every fact IS in the context, the answer DOES abstain — and
    it still fabricates, because the appended facts are presented as if they
    answered the question. The blind judge caught these crudely (it rejected any
    specific assertion); the grounded one let them through. Fabrication by
    adjacency."""
    import benchmark.qa_eval as qa

    system, _ = qa.build_adversarial_judge_prompt(
        "q", "p", context=["some chunk"])
    basso = system.lower()
    assert "as a whole" in basso, (
        "the rubric must bind the verdict to the ENTIRE answer: an abstention "
        "followed by volunteered facts is what slips through otherwise")
    assert "implies" in basso or "as if" in basso or "suggest" in basso, (
        "the rubric must name the failure mode — facts offered so that they "
        "read as the answer — not merely require each fact to be supported")


def test_adversarial_judging_without_context_must_be_explicit() -> None:
    """The dual-ruler defect, the one both reviews said documentation cannot
    fix: a function that picks its rubric from whether a context happened to be
    passed lets a single reported number mix items graded by a permissive
    rubric with items graded by a strict one — 'documented' only moves the
    blame to the reader. So the blind rubric is no longer a silent fallback:
    asking for an adversarial verdict without context raises unless the caller
    states, in the call itself, that it wants the OLD ruler."""
    import pytest as _pytest

    import benchmark.qa_eval as qa
    from verimem.llm import MockLLM

    with _pytest.raises(ValueError, match="rubric"):
        qa.judge_abstention(MockLLM(scripted=["CORRECT"]), "Who?", "It was Bob.")

    # explicit opt-in still works, for callers that genuinely have no context
    assert qa.judge_abstention(
        MockLLM(scripted=["CORRECT"]), "Who?", "I don't know",
        allow_blind=True) is True
    # and the normal path — with context — needs no ceremony
    assert qa.judge_abstention(
        MockLLM(scripted=["CORRECT"]), "Who?", "I don't know",
        context=["a chunk"]) is True


def test_the_rubric_protects_a_pure_abstention_and_a_plain_rejection() -> None:
    """Measured regression from my own anti-adjacency clause (WS2.6, 27/07).

    Giving the judge the context made it start reasoning 'you could have
    answered', and the clause 'INCORRECT when it abstains but then volunteers
    facts' was wide enough to swallow legitimate rejections. Two real cases:

      0:186 'Who is Caroline a fan of in terms of modern music?' — it is
      MELANIE who names Ed Sheeran. strict answered exactly 'NO ANSWER' and was
      graded INCORRECT. A pure abstention on an item that is unanswerable BY
      CONSTRUCTION must always be correct, whatever the context happens to hold.

      3:227 'What impact does Joanna hope to have with her painting?' — the
      context has zero occurrences of 'paint' and shows Joanna WRITES. declared
      answered 'No. Joanna is a writer, not a painter. The context contains no
      mention of her painting' — a textbook rejection — and was graded
      INCORRECT.

    So the rubric must say both things explicitly: a bare abstention is always
    correct, and naming what the context DOES say while rejecting the premise
    is a rejection, not an adjacency fabrication."""
    import benchmark.qa_eval as qa

    system, _ = qa.build_adversarial_judge_prompt("q", "p", context=["chunk"])
    basso = system.lower()
    assert "always correct" in basso, (
        "a pure abstention must be unconditionally correct: these items are "
        "unanswerable by construction, so 'the context looked answerable' is "
        "never a reason to reject one")
    assert "instead of" in basso or "rather than" in basso, (
        "the rubric must distinguish 'X did it, not Y — here is what the "
        "context says instead' (a rejection) from facts offered AS the answer")
