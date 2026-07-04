"""LLMJudge — the concrete Tier-2 judge (was missing; only stubs existed). Maps a one-word
verdict to a JudgeAction, fail-safe to KEEP. Hermetic — a capturing stub LLM, no claude -p.
Upholds the module invariant: the judge only DECLASSes (noise) or flags PROMOTE (durable),
never on an error."""
from __future__ import annotations

import types

import pytest

from engram.tier2_judge import JudgeAction, LLMJudge


class _StubLLM:
    def __init__(self, text):
        self._text = text
        self.last_system = None
        self.last_user = None

    def complete(self, system, messages, *, model=None, max_tokens=None):
        self.last_system = system
        self.last_user = messages[-1]["content"]
        return types.SimpleNamespace(text=self._text)


@pytest.mark.parametrize("reply,expect", [
    ("NOISE", JudgeAction.DECLASS),
    ("noise — a one-off latency", JudgeAction.DECLASS),
    ("DURABLE", JudgeAction.PROMOTE_CANDIDATE),
    ("Durable fact", JudgeAction.PROMOTE_CANDIDATE),
    ("NEUTRAL", JudgeAction.KEEP),
    ("something unparseable", JudgeAction.KEEP),
])
def test_verdict_mapping(reply, expect):
    v = LLMJudge(_StubLLM(reply)).judge("the loop ran 3 steps", topic="diary")
    assert v.action is expect


def test_error_is_failsafe_keep():
    class _Boom:
        def complete(self, *a, **k):
            raise RuntimeError("offline")

    v = LLMJudge(_Boom()).judge("x")
    assert v.action is JudgeAction.KEEP and "fail-safe" in v.reason


def test_prompt_includes_claim_topic_context():
    llm = _StubLLM("NEUTRAL")
    LLMJudge(llm).judge("the cache holds 1024 entries", topic="infra", context="config note")
    assert "the cache holds 1024 entries" in llm.last_user
    assert "infra" in llm.last_user and "config note" in llm.last_user


def test_implements_judge_protocol():
    from engram.tier2_judge import Judge
    assert isinstance(LLMJudge(_StubLLM("NEUTRAL")), Judge)
