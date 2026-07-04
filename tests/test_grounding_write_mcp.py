"""Integration: the SEMANTIC write-path grounding (L4) is reachable from the
hippo_remember MCP handler — closes the built-vs-live gap.

Unit tests (test_grounding_write_gate.py) prove run_validation_gate(source=...,
grounding_llm=...) behaves. THESE prove the MCP wiring: the hippo_remember tool exposes
`source`, the handler threads it + the agent's (deferred) LLM into the gate, and a
proposition the source does not entail is rejected/downgraded — but only when
ENGRAM_GROUNDING_WRITE is set. Stub LLM → deterministic, no claude -p.
"""
from __future__ import annotations

import json
import types
from pathlib import Path
from typing import Any

import pytest

from engram import mcp_server
from engram.semantic import SemanticMemory


class _StubLLM:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
        self.calls += 1
        return types.SimpleNamespace(text=self.text)


@pytest.fixture
def wired(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    stub = _StubLLM("SCORE: 12")  # source does NOT entail -> low grounding

    class _Wake:
        def __init__(self) -> None:
            self.llm = stub

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = sm
            self.wake = _Wake()

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    monkeypatch.delenv("ENGRAM_VALIDATE_DEFAULT", raising=False)
    return sm, stub


async def _invoke(name: str, arguments: dict | None = None) -> dict[str, Any]:
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(method="tools/call",
                          params=CallToolRequestParams(name=name, arguments=arguments or {}))
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    text = next(c.text for c in payload.content if hasattr(c, "text"))
    return json.loads(text)


_CLEAN = "The internal widget allocation for unit Q is 42 units."  # lexically benign
_SRC = "An unrelated note about the cafeteria menu and parking schedule."


@pytest.mark.asyncio
async def test_source_in_schema(wired) -> None:  # noqa: ANN001
    tools = await mcp_server.list_tools()
    remember = next(t for t in tools if t.name == "hippo_remember")
    assert "source" in remember.inputSchema["properties"]


@pytest.mark.asyncio
async def test_rejects_when_source_does_not_entail(wired, monkeypatch) -> None:  # noqa: ANN001
    _sm, stub = wired
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    out = await _invoke("hippo_remember", {
        "proposition": _CLEAN, "topic": "notes/grounding-test",
        "source": _SRC, "gate_mode": "reject",
    })
    assert out.get("rejected") is True
    assert stub.calls == 1  # the semantic verifier WAS consulted
    warns = out.get("anti_confab_warnings") or []
    assert any(w.get("layer") == "L4-grounding" for w in warns)


@pytest.mark.asyncio
async def test_off_does_not_consult_verifier(wired, monkeypatch) -> None:  # noqa: ANN001
    _sm, stub = wired
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    out = await _invoke("hippo_remember", {
        "proposition": _CLEAN, "topic": "notes/grounding-test", "source": _SRC,
    })
    assert out.get("ok") is True
    assert out.get("rejected") in (None, False)
    assert stub.calls == 0  # feature off → no semantic call, fast path intact


# R27 step2: env-gated derivation auto-detect (id-mention only) in hippo_remember
def _stored_by_prop(sm, prop):  # noqa: ANN001, ANN202
    return next(f for f in sm.list_facts(limit=200, include_superseded=True)
               if f.proposition == prop)


@pytest.mark.asyncio
async def test_derivation_autodetect_on_id_mention(wired, monkeypatch) -> None:  # noqa: ANN001
    from engram.semantic import Fact
    sm, _stub = wired
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    monkeypatch.setenv("ENGRAM_DERIVATION_AUTODETECT", "1")
    sm.store(Fact(id="abc123abc123", proposition="parent belief", topic="t/d",
                  source_episodes=["e"]))
    out = await _invoke("hippo_remember", {
        "proposition": "a newly derived belief", "topic": "t/d",
        "source": "Concluded from prior finding abc123abc123 in the store.",
    })
    assert out.get("ok") is True
    assert _stored_by_prop(sm, "a newly derived belief").derives_from == ["abc123abc123"]


@pytest.mark.asyncio
async def test_derivation_autodetect_off_by_default(wired, monkeypatch) -> None:  # noqa: ANN001
    from engram.semantic import Fact
    sm, _stub = wired
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    monkeypatch.delenv("ENGRAM_DERIVATION_AUTODETECT", raising=False)
    sm.store(Fact(id="def456def456", proposition="another parent", topic="t/d",
                  source_episodes=["e"]))
    await _invoke("hippo_remember", {
        "proposition": "derived without autodetect", "topic": "t/d",
        "source": "Concluded from prior finding def456def456 in the store.",
    })
    assert _stored_by_prop(sm, "derived without autodetect").derives_from == []  # gate off
