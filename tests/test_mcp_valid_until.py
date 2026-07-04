"""MCP hippo_remember espone valid_until (v10 valid-time, 2026-06-14).

Lo step 4 (colonna + filtro hard-expire) e' coperto end-to-end da
tests/test_valid_time.py. Qui si verifica SOLO il plumbing MCP: l'handler
``hippo_remember`` legge ``valid_until`` dagli arguments e lo inoltra a
``_build_fact`` (factory), che lo mette nel Fact. Spy sul factory per isolare
l'inoltro dal deferred-store/recall (che e' gia' testato altrove).
"""
from __future__ import annotations

import time
from typing import Any

from engram import mcp_server
from engram.semantic import SemanticMemory


class _Agent:
    def __init__(self, sm: SemanticMemory) -> None:
        self.semantic = sm


async def _invoke(name: str, arguments: dict[str, Any]):
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


def _spy_build_fact(monkeypatch, captured: dict[str, Any]):
    real_build = mcp_server._build_fact

    def _spy(*a, **kw):
        captured.update(kw)
        return real_build(*a, **kw)

    monkeypatch.setattr(mcp_server, "_build_fact", _spy)


def test_build_fact_carries_valid_until():
    """Factory: il param valid_until finisce nel Fact (default None)."""
    vu = 1_234_567.0
    assert mcp_server._build_fact("p", "t", valid_until=vu).valid_until == vu
    assert mcp_server._build_fact("p", "t").valid_until is None


async def test_hippo_remember_forwards_valid_until(tmp_path, monkeypatch):
    """L'handler MCP inoltra valid_until (epoch) a _build_fact."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _Agent(sm))
    captured: dict[str, Any] = {}
    _spy_build_fact(monkeypatch, captured)

    vu = time.time() + 86400.0
    await _invoke("hippo_remember", {
        "proposition": "the deploy alpha is in progress",
        "topic": "t/ops",
        "valid_until": vu,
    })
    assert captured.get("valid_until") == vu, \
        "l'handler MCP deve inoltrare valid_until a _build_fact"


async def test_hippo_remember_absent_valid_until_is_none(tmp_path, monkeypatch):
    """Nessun valid_until negli arguments -> None (nessuna scadenza)."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _Agent(sm))
    captured: dict[str, Any] = {}
    _spy_build_fact(monkeypatch, captured)

    await _invoke("hippo_remember", {"proposition": "stable fact", "topic": "t"})
    assert captured.get("valid_until") is None, \
        "valid_until assente deve diventare None"


async def test_hippo_remember_malformed_valid_until_failsoft(tmp_path, monkeypatch):
    """Un valid_until non numerico non rompe lo store: coercion fail-soft -> None."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _Agent(sm))
    captured: dict[str, Any] = {}
    _spy_build_fact(monkeypatch, captured)

    await _invoke("hippo_remember", {
        "proposition": "x", "topic": "t", "valid_until": "not-a-number",
    })
    assert captured.get("valid_until") is None, \
        "valid_until malformato -> None (fail-soft, nessun crash)"
