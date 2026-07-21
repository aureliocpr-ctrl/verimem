"""F4 (kimi audit 2026-07-21, verified at grounding_gate.py:106): the
abstention regex uses .search(), so an output that DECLINES one part and
ASSERTS another — "The budget is not mentioned, but the offsite is likely in
June" — was filed as a clean abstention. The invented "June" skipped every
verifier and still shipped in raw_answer under an abstention verdict.

Cure: a short-circuit is earned only by a CLEAN abstention (every clause
declines). A hybrid one keeps its assertion and must face verification like
any other answer.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.client import Memory
from verimem.grounding_gate import GateResult, _abstention_kind, gate_answer
from verimem.llm import LLMResponse

# ------------------------------------------------------------- classifier unit

CLEAN = [
    "",
    "NO ANSWER",
    "no answer",
    "The answer cannot be determined from the facts.",
    "Not mentioned in the provided facts.",
    "This is unanswerable from the given context.",
    "The catering budget is not stated.",
    # glm review D4/D5 (2026-07-21): common refusals the old regex missed —
    # they were classified as ANSWERS and mislabelled unsupported_by_facts
    "I don't know.",
    "I do not know the answer to this question.",
    "Not mentioned. I do not know the answer to this question.",
    "Unknown.",
    "No information available.",
    # comma-split safety: a trivial residue must not flip a pure refusal
    "No, that is not stated.",
]

HYBRID = [
    "The catering budget is not mentioned, but the offsite is likely in June.",
    "Not stated in the facts. However, it is probably Marco who decided.",
    "The desk count for Rome is not provided; the Milan office has 40 desks "
    "though.",
    # self-attack 2026-07-21: a terse assertion after the refusal must not
    # slip under a word-count threshold
    "Not stated. June 12.",
    # kimi review finding 1 (2026-07-21): bare comma, no coordinator — the
    # decline-marker must not bless the invented date sharing its clause
    "Not mentioned, the offsite is likely June 5.",
    "Not stated. Probably June.",
]

NONE = [
    "Marco",
    "The offsite is in Lisbon.",
    # overreach guard: 'unknown' as a WORD inside a real answer must not
    # trigger the refusal free pass (that would kill a true answer)
    "The unknown attacker used a rootkit.",
]


@pytest.mark.parametrize("text", CLEAN)
def test_clean_abstentions_classify_clean(text: str):
    assert _abstention_kind(text) == "clean"


@pytest.mark.parametrize("text", HYBRID)
def test_hybrid_abstentions_classify_hybrid(text: str):
    assert _abstention_kind(text) == "hybrid"


@pytest.mark.parametrize("text", NONE)
def test_plain_answers_classify_none(text: str):
    assert _abstention_kind(text) == "none"


# ------------------------------------------------------------ answer() wiring

class QueueLLM:
    """Replies from a queue: first call = generation, later calls = judge.
    The judge QUALITY was measured live (6/8 escapes blocked, 6/6 trues kept,
    2026-07-21); these tests pin the WIRING, not the judge."""

    def __init__(self, *texts: str) -> None:
        self._texts = list(texts)
        self.calls = 0

    def complete(self, system, messages, **kw):  # noqa: ANN001
        self.calls += 1
        text = self._texts.pop(0) if self._texts else ""
        return LLMResponse(text=text, input_tokens=10, output_tokens=9,
                           model="fake", latency_s=0.1, finish_reason="stop")


@pytest.fixture
def store(tmp_path: Path) -> Memory:
    m = Memory(path=tmp_path / "m.db")
    m.add("The team offsite is in Lisbon.", topic="t/x",
          source="The team offsite is in Lisbon.", verified_by=["source-doc:f4:0"])
    return m


HYBRID_REPLY = ("The catering budget is not mentioned, but the offsite is "
                "likely in June.")


def test_hybrid_abstention_is_verified_not_shortcircuited(store: Memory):
    """The asserted half ("likely in June") is unsupported: it must reach the
    verifier chain and be caught — never certified as a model abstention while
    the assertion ships in the payload. (The topical CE alone serves this text
    — measured — so the question-aware judge is the stage that catches it.)"""
    llm = QueueLLM(HYBRID_REPLY, "Score: 5")
    res = store.answer("When is the offsite and what is the catering budget?",
                       llm=llm)
    assert llm.calls == 2                          # verification actually ran
    assert res["reason"] == "judge_rejected"       # no free pass
    assert res["answer"] == "NO ANSWER"
    assert res["grounded"] is False
    assert "June" in (res["raw_answer"] or "")     # caught, not hidden


def test_hybrid_with_unreadable_judge_returns_to_its_refusal(store: Memory):
    """A hybrid already declined once; serving its asserted half with NO
    readable judge verdict would be a free pass through the back door."""
    llm = QueueLLM(HYBRID_REPLY, "the verdict is unclear")
    res = store.answer("When is the offsite and what is the catering budget?",
                       llm=llm)
    assert res["answer"] == "NO ANSWER"
    assert res["reason"] == "judge_unreadable_hybrid"
    assert res["judge_score"] is None
    assert "June" in (res["raw_answer"] or "")


def test_clean_abstention_keeps_model_abstained_contract(store: Memory):
    llm = QueueLLM("Not mentioned in the provided facts.")
    res = store.answer("What is the catering budget?", llm=llm)
    assert res["reason"] == "model_abstained"
    assert res["answer"] == "NO ANSWER"
    assert llm.calls == 1                          # no judge call spent


# ---------------------------------------------------------- gate_answer wiring

class ScoringLLM:
    """Judge returning a fixed grounding score."""

    def __init__(self, score: int) -> None:
        self._score = score
        self.calls = 0

    def complete(self, system, messages, **kw):  # noqa: ANN001
        self.calls += 1
        return LLMResponse(text=f"Score: {self._score}", input_tokens=5,
                           output_tokens=2, model="fake", latency_s=0.1)


def test_gate_answer_hybrid_spends_a_verifier_call():
    """gate_answer gave any abstention-phrased text a free GateResult with
    score=100. A hybrid must be judged; with a low score it is blocked."""
    judge = ScoringLLM(10)
    r: GateResult = gate_answer(
        judge, "When is the offsite?",
        "The team offsite is in Lisbon.",
        "The date is not mentioned, but it is likely 12 June.")
    assert judge.calls == 1                      # verification actually ran
    assert r.grounded is False
    assert r.answer == "NO ANSWER"
    assert "June" in r.raw_answer                # payload preserved for audit


def test_gate_answer_clean_abstention_still_free():
    judge = ScoringLLM(10)
    r = gate_answer(judge, "When is the offsite?",
                    "The team offsite is in Lisbon.",
                    "Cannot be determined from the facts.")
    assert judge.calls == 0                      # no verifier call spent
    assert r.answer == "NO ANSWER"
    assert r.grounded is True
