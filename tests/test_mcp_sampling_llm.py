"""Cycle #71 RED — MCPSamplingLLM + hosted_mode consolidate routing.

Spec: docs/specs/c71-mcp-sampling-llm.md.

L'obiettivo è sbloccare `hippo_consolidate` (full sleep cycle) in HOSTED
MODE senza API key esterna, instradando le chiamate LLM via MCP sampling
(`sampling/createMessage` allo client Claude Code). Costo per HippoAgent:
ZERO — usa la subscription del host.

4 RED minimi:
1. MCPSamplingLLM.complete con FakeSession sync-bridge funziona
2. MCPSamplingLLM chiamato da thread separato (asyncio.to_thread) ok
3. hippo_consolidate in hosted mode con sampling fake NON è refused
4. MCPSamplingLLM.supports_tools() = False (P0 no tools)
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

# ---------- FakeSession helper ---------------------------------------


class _FakeContent:
    """Mimics mcp.types.TextContent."""

    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeResult:
    """Mimics mcp.types.CreateMessageResult."""

    def __init__(self, text: str, model: str = "claude-fake-test") -> None:
        self.role = "assistant"
        self.content = _FakeContent(text)
        self.model = model
        self.stopReason = "endTurn"


class _FakeSession:
    """Async fake of mcp.server.session.ServerSession.

    The `responder` callable is invoked with (messages, kwargs) and
    must return a str — the text the host LLM would have generated.
    Defaults to a constant.
    """

    def __init__(self, responder=None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responder = responder or (lambda messages, kw: "OK")

    async def create_message(
        self, messages, *, max_tokens, system_prompt=None,
        temperature=None, stop_sequences=None,
        include_context=None, metadata=None,
        model_preferences=None, tools=None, tool_choice=None,
        related_request_id=None,
    ):
        kw = {
            "max_tokens": max_tokens,
            "system_prompt": system_prompt,
            "temperature": temperature,
            "stop_sequences": stop_sequences,
        }
        self.calls.append({"messages": messages, "kw": kw})
        text = self.responder(messages, kw)
        return _FakeResult(text)


# ---------- RED #1: basic complete returns LLMResponse ---------------


def test_mcp_sampling_llm_complete_basic() -> None:
    """RED #1: complete() chiama session.create_message via bridge
    e ritorna LLMResponse con text from result."""
    from verimem.llm import MCPSamplingLLM

    async def _run() -> None:
        loop = asyncio.get_running_loop()
        sess = _FakeSession(
            responder=lambda msgs, kw: "hello world from sampling",
        )
        llm = MCPSamplingLLM(loop=loop, session=sess)

        # complete() is SYNC — needs to be called from non-loop thread
        # to test the bridge path. We use to_thread for realism.
        resp = await asyncio.to_thread(
            llm.complete,
            "system prompt here",
            [{"role": "user", "content": "ciao"}],
        )
        assert resp.text == "hello world from sampling"
        assert resp.model == "claude-fake-test"
        # Verify session was called correctly
        assert len(sess.calls) == 1
        call = sess.calls[0]
        assert call["kw"]["system_prompt"] == "system prompt here"
        # max_tokens has default
        assert call["kw"]["max_tokens"] > 0
        # 1 message converted to SamplingMessage
        assert len(call["messages"]) == 1

    asyncio.run(_run())


# ---------- RED #2: thread bridge round-trip --------------------------


def test_mcp_sampling_llm_from_thread_no_deadlock() -> None:
    """RED #2: complete() chiamato da thread separato (simula
    asyncio.to_thread che SleepEngine.cycle usa indirettamente)
    completa senza deadlock entro 5s."""
    from verimem.llm import MCPSamplingLLM

    async def _run() -> None:
        loop = asyncio.get_running_loop()
        sess = _FakeSession(
            responder=lambda msgs, kw: "thread-safe",
        )
        llm = MCPSamplingLLM(loop=loop, session=sess)

        # Issue 3 consecutive calls from worker thread — emulates
        # SleepEngine doing dreamer NREM + REM + critic sequenza.
        async def worker_task():
            return await asyncio.to_thread(
                lambda: [
                    llm.complete("s", [{"role": "user", "content": f"q{i}"}])
                    for i in range(3)
                ],
            )

        results = await asyncio.wait_for(worker_task(), timeout=5.0)
        assert len(results) == 3
        for r in results:
            assert r.text == "thread-safe"
        assert len(sess.calls) == 3

    asyncio.run(_run())


# ---------- RED #3: hosted consolidate via sampling not refused ------


@pytest.mark.asyncio
async def test_hippo_consolidate_hosted_with_sampling_not_refused(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """RED #3: in HOSTED MODE, `hippo_consolidate` deve provare a
    instradare via MCP sampling (NON refuse hard). Test fake-faithful:
    forza hosted=True, inietta fake session via monkey-patch sul
    request_context, verifica che il handler non ritorni 'rejected_hosted'.

    Nota: il test minimo verifica che la GATE sia stata rimossa /
    sostituita con sampling path. Anche se il consolidate poi fallisce
    su corpus vuoto (RED su engine — fuori scope qui), il punto
    chiave è che NON deve essere 'rejected_hosted'.
    """
    import os

    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server

    monkeypatch.setenv("HIPPO_HOSTED", "1")

    # Minimal fake agent: must have .sleep.llm + .consolidate()
    class _FakeSleep:
        def __init__(self) -> None:
            self.llm = object()  # placeholder, swapped by handler

        def cycle(self):
            class _R:
                n_episodes_replayed = 0
                n_clusters = 0
                n_nrem_skills = 0
                n_rem_skills = 0
                n_facts = 0
                promoted: list = []
                retired: list = []
                merged: list = []
                duration_s = 0.0
                tokens_used = 0
            return _R()

    class _FakeAgent:
        def __init__(self) -> None:
            self.sleep = _FakeSleep()

        def consolidate(self):
            return self.sleep.cycle()

    fake = _FakeAgent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: fake)

    # Patch request_context property on the server to return a stub
    # whose .session is a FakeSession.
    class _StubCtx:
        def __init__(self) -> None:
            self.session = _FakeSession(
                responder=lambda msgs, kw: "{}",
            )

    monkeypatch.setattr(
        type(mcp_server.server), "request_context",
        property(lambda self: _StubCtx()),
        raising=False,
    )

    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(
            name="hippo_consolidate", arguments={},
        ),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    text = payload.content[0].text
    data = json.loads(text)

    # Acceptance: NON deve essere il vecchio refuse "hosted mode active"
    err = data.get("error", "")
    assert "hosted mode active (HIPPO_HOSTED=1) — use" not in err, (
        f"sampling routing not active, still refused: {err}"
    )


# ---------- RED #4: supports_tools = False ---------------------------


def test_mcp_sampling_llm_no_tools_support() -> None:
    """RED #4: P0 no tools — supports_tools() ritorna False per
    evitare che SleepEngine prenda il path complete_with_tools."""
    from verimem.llm import MCPSamplingLLM

    async def _run() -> None:
        loop = asyncio.get_running_loop()
        sess = _FakeSession()
        llm = MCPSamplingLLM(loop=loop, session=sess)
        assert llm.supports_tools() is False

    asyncio.run(_run())
