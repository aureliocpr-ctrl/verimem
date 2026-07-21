"""F6 (measured 2026-07-21): moonshot's kimi-k3 / kimi-k2.6 reject any
temperature other than 1 with a 400 ('invalid temperature: only 1 is
allowed'), while OpenAICompatLLM sends temperature=0.0 on every call — so a
customer pointing verimem at Moonshot got an LLMError on every answer/ingest.

Cure: on a 400 that names temperature, retry ONCE without the parameter (the
provider then applies its own default). Any other error keeps today's retry
path untouched.
"""
from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from verimem.llm import OpenAICompatLLM


class _FakeCompletions:
    def __init__(self, owner: _FakeClient) -> None:
        self._owner = owner

    def create(self, **kw: Any):
        self._owner.calls.append(kw)
        if "temperature" in kw and kw["temperature"] != 1:
            raise RuntimeError(
                "Error code: 400 - {'error': {'message': 'invalid temperature: "
                "only 1 is allowed for this model', 'type': "
                "'invalid_request_error'}}")
        msg = types.SimpleNamespace(content="Marco")
        choice = types.SimpleNamespace(message=msg, finish_reason="stop")
        usage = types.SimpleNamespace(prompt_tokens=5, completion_tokens=2)
        return types.SimpleNamespace(choices=[choice], usage=usage)


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.chat = types.SimpleNamespace(completions=_FakeCompletions(self))


@pytest.fixture
def llm(monkeypatch) -> OpenAICompatLLM:
    fake_openai = types.SimpleNamespace(OpenAI=lambda **kw: _FakeClient())
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    return OpenAICompatLLM(api_key="k", base_url="https://api.example.test",
                           default_model="m", provider_label="test")


def test_temperature_400_retries_once_without_temperature(llm: OpenAICompatLLM):
    resp = llm.complete("sys", [{"role": "user", "content": "q"}])
    assert resp.text == "Marco"
    calls = llm.client.calls
    assert len(calls) == 2                      # failed once, retried once
    assert "temperature" in calls[0]            # the normal attempt
    assert "temperature" not in calls[1]        # the provider-default retry


def test_non_temperature_errors_keep_normal_retry_path(llm: OpenAICompatLLM, monkeypatch):
    def _always_500(**kw: Any):
        llm.client.calls.append(kw)
        raise RuntimeError("Error code: 500 - upstream exploded")

    monkeypatch.setattr(llm.client.chat.completions, "create", _always_500)
    monkeypatch.setattr("verimem.llm._retry_sleep", lambda *a, **k: None)
    from verimem.llm import LLMError
    with pytest.raises(LLMError):
        llm.complete("sys", [{"role": "user", "content": "q"}])
    # every attempt kept the temperature parameter: no silent contract drift
    assert all("temperature" in c for c in llm.client.calls)
