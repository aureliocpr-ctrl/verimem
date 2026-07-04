"""FORGIA pezzo #204 — `hippo_health` MCP tool (deep preflight check).

Aurelio said: "imposta tutto sempre che all'avvio deve funzionare ed
essere integrato". The skill activation flow needs a single tool that
returns a green/red verdict on every subsystem so Claude Code can
trust-but-verify on every cold start.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from engram import mcp_server

# ---------- Fakes --------------------------------------------------------


class _FakeMemory:
    def __init__(self, n: int = 5) -> None:
        self._n = n
        self._raise = False

    def count(self, outcome_filter=None) -> int:
        if self._raise:
            raise RuntimeError("episodes.db unreachable")
        return self._n


class _FakeSkillsStore:
    def __init__(self, n: int = 3) -> None:
        self._n = n

    def count(self, status=None) -> int:
        return self._n


class _FakeSemantic:
    def __init__(self, n: int = 7) -> None:
        self._n = n

    def count(self) -> int:
        return self._n


class _FakeAgent:
    def __init__(self) -> None:
        self.memory = _FakeMemory()
        self.skills = _FakeSkillsStore()
        self.semantic = _FakeSemantic()


# ---------- Helpers ------------------------------------------------------


async def _invoke_tool(name: str, arguments: dict[str, Any] | None = None):
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


@pytest.fixture
def fake_agent(monkeypatch: pytest.MonkeyPatch) -> _FakeAgent:
    a = _FakeAgent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


# ---------- listing ------------------------------------------------------


@pytest.mark.asyncio
async def test_health_listed(fake_agent: _FakeAgent) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_health" in names


# ---------- happy path ---------------------------------------------------


@pytest.mark.asyncio
async def test_health_ok(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool("hippo_health", {})
    payload = json.loads(blocks[0])
    assert payload["status"] == "ok"
    assert payload["episodes_db"] == "ok"
    assert payload["skills_store"] == "ok"
    assert payload["semantic_db"] == "ok"
    assert payload["counts"]["episodes"] == 5
    assert payload["counts"]["skills"] == 3
    assert payload["counts"]["facts"] == 7
    # The disabled flag should reflect the env var (False if unset).
    assert "disabled_flag" in payload
    assert "tool_count" in payload
    # >= 38 since Wave 1-8 added 26 + the 12 base + this new one.
    assert payload["tool_count"] >= 38


@pytest.mark.asyncio
async def test_health_episodes_unreachable(
    fake_agent: _FakeAgent,
) -> None:
    """If memory.count() raises, the layer is reported as degraded."""
    fake_agent.memory._raise = True
    blocks = await _invoke_tool("hippo_health", {})
    payload = json.loads(blocks[0])
    assert payload["status"] == "degraded"
    assert payload["episodes_db"].startswith("error:")


@pytest.mark.asyncio
async def test_health_disabled_flag(
    fake_agent: _FakeAgent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HIPPO_DISABLED", "1")
    blocks = await _invoke_tool("hippo_health", {})
    payload = json.loads(blocks[0])
    # Even if the server is running (test contains no disable check),
    # health surfaces the flag so Claude Code can act on it.
    assert payload["disabled_flag"] is True
