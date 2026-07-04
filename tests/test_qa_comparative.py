"""Hermetic TDD for the end-to-end QA-comparative pipeline (no claude -p, stub LLM)."""
from __future__ import annotations

import types

from benchmark.qa_comparative import run


class _StubLLM:
    """Deterministic answerer+judge. Answer = echo the context; judge = gold token in pred."""

    def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
        user = messages[-1]["content"]
        if "GOLD:" in user and "PREDICTED:" in user:           # judge call
            gold = user.split("GOLD:", 1)[1].split("\n", 1)[0].strip().lower()
            pred = user.split("PREDICTED:", 1)[1].split("\n", 1)[0].strip().lower()
            return types.SimpleNamespace(text="CORRECT" if gold and gold in pred else "INCORRECT")
        ctx = user.split("Memory/context:", 1)[1] if "Memory/context:" in user else ""
        return types.SimpleNamespace(text=(ctx.strip().splitlines() or ["NO ANSWER"])[0][:120]
                                     if ctx.strip() else "NO ANSWER")


def _q(qid, gold_sid, gold_text, distract_sid):
    return {
        "question_id": qid, "question": "what is the value?", "question_type": "single-session-user",
        "answer": gold_text,
        "answer_session_ids": [gold_sid],
        "haystack_session_ids": [distract_sid, gold_sid],
        "haystack_sessions": [
            [{"role": "user", "content": "totally unrelated chatter about the weather"}],
            [{"role": "user", "content": f"the value is {gold_text}"}],
        ],
    }


class _CapturingLLM:
    """Records every user message; answers NO ANSWER, judges INCORRECT (we only
    inspect what context the answerer received)."""

    def __init__(self) -> None:
        self.user_msgs: list[str] = []

    def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
        self.user_msgs.append(messages[-1]["content"])
        return types.SimpleNamespace(text="NO ANSWER")


def _q_dated(qid, gold_sid, gold_text, distract_sid, dates, qdate):
    q = _q(qid, gold_sid, gold_text, distract_sid)
    q["question_type"] = "temporal-reasoning"
    q["haystack_dates"] = dates
    q["question_date"] = qdate
    return q


def test_dates_are_prefixed_into_context_when_present(tmp_path, monkeypatch) -> None:
    """The date-blind harness measured temporal-reasoning 0.0; the answer prompt
    expects [timestamp] prefixes, so haystack_dates MUST reach the context."""
    monkeypatch.setenv("ENGRAM_QA_DATES", "1")
    import json
    ds = tmp_path / "lme.json"
    ds.write_text(json.dumps([
        _q_dated("q1", "s_gold1", "magenta42", "s_dist1",
                 ["2022/12/19 (Mon) 12:04", "2023/01/04 (Wed) 17:04"], "2023/02/01 (Wed) 09:00"),
    ]), encoding="utf-8")
    llm = _CapturingLLM()
    run(ds, llm, k=2, sample=1, arms=("vanilla",))
    blob = "\n".join(llm.user_msgs)
    assert "2023/01/04 (Wed) 17:04" in blob          # a session date reached the context
    assert "Question asked on: 2023/02/01" in blob    # the question_date anchored "now"


def test_dates_off_reproduces_blind_behaviour(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ENGRAM_QA_DATES", "0")
    import json
    ds = tmp_path / "lme.json"
    ds.write_text(json.dumps([
        _q_dated("q1", "s_gold1", "magenta42", "s_dist1",
                 ["2022/12/19 (Mon) 12:04", "2023/01/04 (Wed) 17:04"], "2023/02/01 (Wed) 09:00"),
    ]), encoding="utf-8")
    llm = _CapturingLLM()
    run(ds, llm, k=2, sample=1, arms=("vanilla",))
    blob = "\n".join(llm.user_msgs)
    assert "2023/01/04" not in blob and "Question asked on" not in blob


def test_pipeline_runs_and_scores_each_arm(tmp_path) -> None:
    ds = tmp_path / "lme.json"
    import json
    ds.write_text(json.dumps([
        _q("q1", "s_gold1", "magenta42", "s_dist1"),
        _q("q2", "s_gold2", "ferroseven", "s_dist2"),
    ]), encoding="utf-8")

    res = run(ds, _StubLLM(), k=2, sample=2, arms=("vanilla", "engram"))
    assert res["n_questions"] == 2
    for arm in ("vanilla", "engram"):
        a = res["arms"][arm]
        assert 0.0 <= a["qa_accuracy"] <= 1.0
        assert "abstention_rate" in a
    # the gold session is in a tiny 2-session haystack -> both arms retrieve it -> answerable
    assert res["arms"]["vanilla"]["qa_accuracy"] == 1.0
    assert res["arms"]["engram"]["qa_accuracy"] == 1.0
