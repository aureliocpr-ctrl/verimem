"""F2 / GLM-2 (measured 2026-07-21): answer()'s local CE is question-blind —
a literal fragment of a stored fact ("Marco", "40") scores 96-99 against it
and a parroted fact ~100, whatever the question was. The CE alone stopped 3/10
scripted concise confabulations; the question-aware judge stage (the same
calibrated judge gate_answer already ships) closed that to 8/10 with 0 true
answers lost.

These tests pin the WIRING of that stage into answer(): who gets judged, what
a rejection returns, and what happens when the judge is unreadable or off.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.client import Memory
from verimem.llm import LLMResponse


class QueueLLM:
    def __init__(self, *texts: str) -> None:
        self._texts = list(texts)
        self.calls = 0
        self.seen: list[str] = []

    def complete(self, system, messages, **kw):  # noqa: ANN001
        self.calls += 1
        self.seen.append(messages[-1]["content"])
        text = self._texts.pop(0) if self._texts else ""
        return LLMResponse(text=text, input_tokens=10, output_tokens=9,
                           model="fake", latency_s=0.1, finish_reason="stop")


@pytest.fixture
def store(tmp_path: Path) -> Memory:
    """The measured bridge shape: leader + event, nobody decided anything."""
    m = Memory(path=tmp_path / "m.db")
    m.add("Marco leads the payments team.", topic="t/x",
          source="Marco leads the payments team.", verified_by=["source-doc:j:0"])
    m.add("The payments team migrated to Stripe in 2025.", topic="t/x",
          source="The payments team migrated to Stripe in 2025.",
          verified_by=["source-doc:j:1"])
    return m


def test_ce_passing_fragment_is_rejected_by_low_judge(store: Memory):
    """'Marco' to 'who DECIDED?' passes the CE at 98.6 (measured). The judge
    stage must be the one that blocks it."""
    llm = QueueLLM("Marco", "Score: 20")
    res = store.answer("Who decided to migrate to Stripe?", llm=llm)
    assert llm.calls == 2
    assert res["answer"] == "NO ANSWER"
    assert res["reason"] == "judge_rejected"
    assert res["judge_score"] == 20.0
    assert res["raw_answer"] == "Marco"            # audit trail intact
    # kimi review (2026-07-21): the CE DID find support — the receipt must
    # name the fact so the audit reads "CE passed; the judge rejected"
    assert res["support_fact"] is not None


def test_true_answer_kept_by_high_judge(store: Memory):
    llm = QueueLLM("Marco", "Score: 100")
    res = store.answer("Who leads the payments team?", llm=llm)
    assert res["answer"] == "Marco"
    assert res["grounded"] is True
    assert res["reason"] == "grounded"
    assert res["judge_score"] == 100.0


def test_judge_prompt_carries_the_question(store: Memory):
    """The whole point of the stage: the judge sees the QUESTION the CE never
    saw. Guard against a refactor quietly dropping it."""
    llm = QueueLLM("Marco", "Score: 100")
    store.answer("Who leads the payments team?", llm=llm)
    assert "Who leads the payments team?" in llm.seen[1]
    assert "Marco" in llm.seen[1]


def test_unreadable_judge_serves_plain_answer_but_grounded_false(store: Memory):
    """F1 (deepseek-v4-pro gate 2026-07-21): a judge that was REQUESTED but
    could not be read leaves only the question-blind CE. Utility is preserved
    (the answer is served), but grounded=True would be a lie — only topicality
    was checked. Honest receipt: served, grounded=False, reason names it."""
    llm = QueueLLM("Marco", "no digits here")
    res = store.answer("Who leads the payments team?", llm=llm)
    assert res["answer"] == "Marco"                # utility preserved
    assert res["grounded"] is False               # not question-verified
    assert res["judge_score"] is None
    assert res["reason"] == "judge_unreadable"


def test_judge_off_serves_ce_verdict_grounded_true(store: Memory):
    """judge_verify=False is an explicit OPT-OUT — the CE verdict governs and
    grounded=True is honest (the caller chose single-stage)."""
    llm = QueueLLM("Marco")
    res = store.answer("Who leads the payments team?", llm=llm,
                       judge_verify=False)
    assert res["answer"] == "Marco"
    assert res["grounded"] is True
    assert res["reason"] == "grounded"


def test_judge_exception_keeps_ce_verdict_for_plain_answer(store: Memory):
    class ExplodingJudge(QueueLLM):
        def complete(self, system, messages, **kw):  # noqa: ANN001
            if self.calls >= 1:
                self.calls += 1
                raise RuntimeError("judge network down")
            return super().complete(system, messages, **kw)

    llm = ExplodingJudge("Marco")
    res = store.answer("Who leads the payments team?", llm=llm)
    assert res["answer"] == "Marco"
    assert res["judge_score"] is None


def test_judge_verify_off_restores_single_stage_behaviour(store: Memory):
    llm = QueueLLM("Marco")
    res = store.answer("Who decided to migrate to Stripe?", llm=llm,
                       judge_verify=False)
    assert llm.calls == 1                          # no judge call
    assert res["answer"] == "Marco"                # the measured CE escape
    assert res["judge_score"] is None


def test_ce_blocked_answer_never_reaches_the_judge(tmp_path: Path):
    """An answer the CE already blocks must not spend a judge call.

    Pair chosen from the measured probe (2026-07-21): 'The Q4 revenue was
    1.38M' scores CE 0.30 against the Q3 fact — a real block. (Against an
    UNRELATED fact the same answer scored 63.31: the CE is noisy out of
    distribution, which is exactly why the judge stage exists — but this test
    needs a pair the CE actually blocks.)"""
    m = Memory(path=tmp_path / "q3.db")
    m.add("The Q3 revenue was 1.2 million euros.", topic="t/x",
          source="The Q3 revenue was 1.2 million euros.",
          verified_by=["source-doc:j:2"])
    llm = QueueLLM("The Q4 revenue was 1.38 million euros.")
    res = m.answer("What was the Q4 revenue?", llm=llm)
    assert llm.calls == 1
    assert res["answer"] == "NO ANSWER"
    assert res["reason"] == "unsupported_by_facts"


def test_failopen_receipt_is_honest_when_ce_unavailable(store: Memory, monkeypatch):
    """F1: served-but-unverified must say grounded=False. The old receipt said
    grounded=True with reason='ce_unavailable_failopen' — a verified-memory
    product certifying an answer nothing verified."""
    import verimem.client as client_mod
    monkeypatch.setattr("verimem.local_grounding.try_local_score",
                        lambda *a, **k: None)
    llm = QueueLLM("Marco")
    res = store.answer("Who leads the payments team?", llm=llm)
    assert res["answer"] == "Marco"                # utility preserved
    assert res["grounded"] is False                # honesty restored
    assert res["reason"] == "ce_unavailable_failopen"
    assert client_mod is not None
