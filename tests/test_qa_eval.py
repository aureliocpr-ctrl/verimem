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
from engram.llm import MockLLM


def test_judge_abstention_empty_prediction_is_correct() -> None:
    # said nothing -> fabricated nothing -> a correct abstention (no judge call)
    j = MockLLM(scripted=[])
    assert judge_abstention(j, "Who?", "") is True
    assert j.calls == []


def test_judge_abstention_uses_llm() -> None:
    assert judge_abstention(MockLLM(scripted=["CORRECT"]), "Who?", "I don't know") is True
    assert judge_abstention(MockLLM(scripted=["INCORRECT"]), "Who?", "It was Bob.") is False


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
