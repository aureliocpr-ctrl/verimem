"""F5 (measured 2026-07-21 on glm-4.6, kimi-k3, kimi-k2.6): a reasoning model
at answer()'s default max_tokens spends the whole budget on reasoning_content
and returns content='' with finish_reason='length'. Today that empty string is
classified 'model_abstained' — the product goes silently mute on every
question, including trivially answerable ones, and telemetry reports virtue.

Truncation is a delivery failure, not an epistemic judgement. The receipt must
say so.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.client import Memory
from verimem.llm import LLMResponse


class TruncatedReasoningLLM:
    """What glm-4.6 / kimi-k2.6 actually returned through OpenAICompatLLM:
    empty text, finish_reason='length' (budget consumed by reasoning)."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def complete(self, system, messages, **kw):  # noqa: ANN001
        self.calls.append(kw)
        return LLMResponse(text="", input_tokens=100, output_tokens=64,
                           model="fake-reasoner", latency_s=0.1,
                           finish_reason="length")


class AbstainingLLM:
    """A model that GENUINELY abstains (empty text, clean stop)."""

    def complete(self, system, messages, **kw):  # noqa: ANN001
        return LLMResponse(text="", input_tokens=100, output_tokens=2,
                           model="fake", latency_s=0.1, finish_reason="stop")


class EchoLLM:
    """Answers with a fixed text; records the max_tokens it was given."""

    def __init__(self, text: str = "Marco") -> None:
        self.text = text
        self.seen_max_tokens: list[int | None] = []

    def complete(self, system, messages, **kw):  # noqa: ANN001
        self.seen_max_tokens.append(kw.get("max_tokens"))
        return LLMResponse(text=self.text, input_tokens=10, output_tokens=3,
                           model="fake", latency_s=0.1, finish_reason="stop")


@pytest.fixture
def store(tmp_path: Path) -> Memory:
    m = Memory(path=tmp_path / "m.db")
    m.add("Marco leads the payments team.", topic="t/x",
          source="Marco leads the payments team.",
          verified_by=["source-doc:f5:0"])
    return m


def test_truncated_empty_is_not_reported_as_model_abstention(store: Memory):
    """content='' + finish_reason='length' → the model NEVER judged the
    question. Reporting 'model_abstained' is a false receipt."""
    res = store.answer("Who leads the payments team?",
                       llm=TruncatedReasoningLLM())
    assert res["answer"] == "NO ANSWER"          # nothing to serve, correct
    assert res["reason"] == "llm_truncated"      # ...but the WHY is truncation
    assert res["grounded"] is False              # no grounding happened


def test_genuine_empty_abstention_still_reports_model_abstained(store: Memory):
    """A clean empty reply (finish_reason='stop') keeps today's contract."""
    res = store.answer("Who leads the payments team?", llm=AbstainingLLM())
    assert res["answer"] == "NO ANSWER"
    assert res["reason"] == "model_abstained"


def test_answer_exposes_max_tokens_and_passes_it_to_the_llm(store: Memory):
    """The 64-token budget was hardcoded; reasoning models need the caller to
    raise it. answer(max_tokens=...) must reach llm.complete verbatim."""
    llm = EchoLLM()
    store.answer("Who leads the payments team?", llm=llm, max_tokens=512)
    assert llm.seen_max_tokens == [512]


def test_answer_default_max_tokens_unchanged(store: Memory):
    """No caller change → byte-identical budget (64), so existing behaviour
    and cost do not silently drift."""
    llm = EchoLLM()
    store.answer("Who leads the payments team?", llm=llm)
    assert llm.seen_max_tokens == [64]
