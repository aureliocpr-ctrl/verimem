"""Tests for FallbackLLM provider chain."""
from __future__ import annotations

from engram.llm import FallbackLLM, LLMResponse, LLMToolResponse, ToolCall


class FakeLLM:
    """Configurable fake LLM. `fail_n` = how many times complete() raises."""
    def __init__(self, name: str, fail_n: int = 0, error: Exception | None = None,
                 supports: bool = True) -> None:
        self.name = name
        self._remaining = fail_n
        self._error = error or RuntimeError(f"{name}: 429 rate limit")
        self._supports = supports
        self.calls = 0

    def supports_tools(self) -> bool:
        return self._supports

    def complete(self, system, messages, model=None, temperature=0.0,
                 max_tokens=None, stop_sequences=None) -> LLMResponse:
        self.calls += 1
        if self._remaining > 0:
            self._remaining -= 1
            raise self._error
        return LLMResponse(text=f"hello from {self.name}",
                           input_tokens=1, output_tokens=1,
                           model=self.name, latency_s=0.0)

    def complete_with_tools(self, system, messages, tools, model=None,
                            temperature=0.0, max_tokens=None) -> LLMToolResponse:
        self.calls += 1
        if self._remaining > 0:
            self._remaining -= 1
            raise self._error
        return LLMToolResponse(
            text=f"tool from {self.name}",
            tool_calls=[ToolCall(id="t1", name="echo", input={"x": "1"})],
            input_tokens=1, output_tokens=1, model=self.name,
            latency_s=0.0, raw_content=[],
        )


def test_fallback_uses_primary_when_healthy():
    primary = FakeLLM("primary", fail_n=0)
    fb = FakeLLM("fallback", fail_n=0)
    chain = FallbackLLM(primary, [fb])
    resp = chain.complete(system="x", messages=[{"role": "user", "content": "hi"}])
    assert resp.model == "primary"
    assert primary.calls == 1
    assert fb.calls == 0


def test_fallback_recovers_on_rate_limit():
    primary = FakeLLM("primary", fail_n=1, error=RuntimeError("429 rate limit"))
    fb = FakeLLM("fallback", fail_n=0)
    chain = FallbackLLM(primary, [fb])
    resp = chain.complete(system="x", messages=[{"role": "user", "content": "hi"}])
    # Primary failed once, fallback succeeded
    assert resp.model == "fallback"
    assert primary.calls == 1
    assert fb.calls == 1


def test_fallback_does_not_swallow_non_recoverable_errors():
    primary = FakeLLM("primary", fail_n=1, error=ValueError("bad input"))
    fb = FakeLLM("fallback", fail_n=0)
    chain = FallbackLLM(primary, [fb])
    try:
        chain.complete(system="x", messages=[{"role": "user", "content": "hi"}])
        assert False, "expected re-raise"
    except ValueError:
        pass
    # Fallback NOT tried (the error was not recoverable)
    assert fb.calls == 0


def test_fallback_walks_full_chain_on_repeated_quota_errors():
    a = FakeLLM("a", fail_n=1, error=RuntimeError("503 service unavailable"))
    b = FakeLLM("b", fail_n=1, error=RuntimeError("quota exceeded"))
    c = FakeLLM("c", fail_n=0)
    chain = FallbackLLM(a, [b, c])
    resp = chain.complete(system="x", messages=[{"role": "user", "content": "hi"}])
    assert resp.model == "c"


def test_fallback_tools_skips_clients_without_support():
    primary = FakeLLM("primary", fail_n=1, supports=True,
                      error=RuntimeError("rate limit"))
    no_tools = FakeLLM("no-tools", supports=False)
    backup = FakeLLM("backup", fail_n=0, supports=True)
    chain = FallbackLLM(primary, [no_tools, backup])
    resp = chain.complete_with_tools(
        system="x",
        messages=[{"role": "user", "content": "hi"}],
        tools=[{"name": "echo", "input_schema": {"type": "object"}}],
    )
    assert resp.model == "backup"
    assert no_tools.calls == 0  # never tried (no tool support)
    assert backup.calls == 1
