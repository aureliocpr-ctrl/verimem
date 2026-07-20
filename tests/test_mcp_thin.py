"""MCP thin path — the ORIGINAL problem: N Claude sessions each spawn an
engram MCP server, each loads its own models and fights the one SQLite file.

Fix (architecture A, MCP tier): when VERIMEM_SERVER_URL is set, the hot MCP
write tool (hippo_remember) delegates to the shared server via RemoteMemory
instead of the process-local agent — so a session behind a memory server never
builds the heavy local agent for a write. Default (no env): unchanged local
path. Fail-soft: a remote error falls back to local, never strands the write.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from verimem import mcp_server


async def _invoke_tool(name: str, arguments: dict[str, Any]):
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


def test_remote_helper_none_without_env(monkeypatch):
    monkeypatch.delenv("VERIMEM_SERVER_URL", raising=False)
    mcp_server._reset_remote_cache()
    assert mcp_server._remote() is None


def test_remote_helper_returns_client_when_healthy(monkeypatch):
    monkeypatch.setenv("VERIMEM_SERVER_URL", "http://memhost:8077")
    monkeypatch.setenv("VERIMEM_SERVER_KEY", "vm_k")

    class _FakeRemote:
        def __init__(self, url, key, **kw):
            self.url = url
        def health(self, raise_on_down=False):
            return True
    monkeypatch.setattr(mcp_server, "_remote_cls", lambda: _FakeRemote)
    mcp_server._reset_remote_cache()
    rm = mcp_server._remote()
    assert isinstance(rm, _FakeRemote) and rm.url == "http://memhost:8077"


@pytest.mark.asyncio
async def test_hippo_remember_delegates_to_server(monkeypatch):
    calls = {"add": 0, "built_agent": 0}

    class _FakeRemote:
        def add(self, content, **kw):
            calls["add"] += 1
            return {"stored": True, "id": "srv-1", "status": "model_claim"}
    monkeypatch.setattr(mcp_server, "_remote", lambda: _FakeRemote())
    # if the local heavy agent is built, the delegation FAILED to short-circuit
    monkeypatch.setattr(mcp_server, "_ag",
                        lambda: calls.__setitem__("built_agent", 1) or (_ for _ in ()).throw(
                            AssertionError("local agent built despite server")))
    blocks = await _invoke_tool("hippo_remember",
                                {"proposition": "The tank holds 500 liters.",
                                 "topic": "ops/tank"})
    payload = json.loads(blocks[0])
    assert calls["add"] == 1 and calls["built_agent"] == 0
    assert payload.get("remote") is True and payload.get("id") == "srv-1"


@pytest.mark.asyncio
async def test_hippo_remember_falls_back_local_on_remote_error(monkeypatch, tmp_data_dir):
    """A remote failure must NOT strand the write — it falls through to the
    local agent path (which stores it), never raises to the caller."""
    class _DeadRemote:
        def add(self, content, **kw):
            raise ConnectionError("server down mid-write")
    monkeypatch.setattr(mcp_server, "_remote", lambda: _DeadRemote())
    blocks = await _invoke_tool("hippo_remember",
                                {"proposition": "Fallback fact about widgets.",
                                 "topic": "tmp/fb"})
    payload = json.loads(blocks[0])
    # local path ran: a real receipt (ok/rejected/id), not a crash, not remote
    assert payload.get("remote") is not True
    assert "ok" in payload or "id" in payload or "rejected" in payload
