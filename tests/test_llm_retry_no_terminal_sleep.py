"""Retry loops must NOT sleep after the final attempt (scan low #7).

Every provider's complete()/complete_with_tools() retries N times with
exponential backoff, but slept on EVERY failed attempt — including the
last one, right before raising. On a terminal error (e.g. groq 404
model_not_found, observed live 2026-06-10) that is a pure wasted wait of
``backoff**(N-1)`` seconds before the caller even sees the failure.

Contract: with max_retries=N and a client that always fails, time.sleep
is called exactly N-1 times (between attempts), never after the last.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

import verimem.llm as llm_mod
from verimem.config import CONFIG
from verimem.llm import AnthropicLLM, LLMError


class _AlwaysFails:
    class messages:  # noqa: N801 — mimic anthropic client shape
        @staticmethod
        def create(**_kwargs):
            raise RuntimeError("terminal error (e.g. 404 model_not_found)")


@pytest.fixture
def _fast_retries(monkeypatch):
    monkeypatch.setattr(llm_mod, "CONFIG",
                        replace(CONFIG, llm_max_retries=3, llm_retry_backoff=2.0))


def _count_sleeps(monkeypatch):
    calls: list[float] = []
    monkeypatch.setattr(llm_mod.time, "sleep", lambda s: calls.append(s))
    return calls


def test_complete_does_not_sleep_after_last_attempt(monkeypatch, _fast_retries):
    sleeps = _count_sleeps(monkeypatch)
    llm = AnthropicLLM.__new__(AnthropicLLM)  # bypass __init__ (no api key)
    llm.client = _AlwaysFails()
    llm.default_model = "claude-test"
    with pytest.raises(LLMError):
        llm.complete(system="s", messages=[{"role": "user", "content": "x"}])
    assert len(sleeps) == 2, (
        f"3 attempts must sleep only BETWEEN them (2x), got {len(sleeps)} "
        "— a sleep after the final failure is wasted latency"
    )


def test_complete_with_tools_does_not_sleep_after_last_attempt(
    monkeypatch, _fast_retries,
):
    sleeps = _count_sleeps(monkeypatch)
    llm = AnthropicLLM.__new__(AnthropicLLM)
    llm.client = _AlwaysFails()
    llm.default_model = "claude-test"
    with pytest.raises(LLMError):
        llm.complete_with_tools(
            system="s", messages=[{"role": "user", "content": "x"}], tools=[],
        )
    assert len(sleeps) == 2, (
        f"complete_with_tools must also skip the terminal sleep, got {len(sleeps)}"
    )
