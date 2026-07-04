"""hippo_remember wired to embed='auto' — a save never cold-blocks (e2e).

When the encode daemon is down, the handler must persist the fact INSTANTLY
(deferred embedding) instead of cold-loading the model (~22s — the incident).
Proven end-to-end through the real MCP handler: the fact is stored and
keyword-findable immediately, absent from semantic recall until backfilled
(the defer signature), and the daemon is kicked awake (self-heal).
"""
from __future__ import annotations

import json

import pytest

from engram import mcp_server
from engram.semantic import SemanticMemory


@pytest.fixture
def _sm(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = sm

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    monkeypatch.delenv("ENGRAM_VALIDATE_DEFAULT", raising=False)
    return sm


async def _invoke(name: str, arguments: dict) -> dict:
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    text = next(c.text for c in payload.content if hasattr(c, "text"))
    return json.loads(text)


def _ids(results):
    return [(r[0] if isinstance(r, (tuple, list)) else r).id for r in results or []]


@pytest.mark.asyncio
async def test_remember_defers_when_daemon_down(_sm, monkeypatch):
    import engram.encode_service as es
    monkeypatch.setattr(es, "daemon_usable", lambda: False)
    _heal = []
    monkeypatch.setattr(es, "ensure_running", lambda: _heal.append(1) or False)

    out = await _invoke("hippo_remember", {
        "proposition": "The shard rotates after 8192 writes.",
        "topic": "t/nonblock",
        "confidence": 0.9,
    })
    assert out.get("ok") is True
    fid = out["id"]

    # deferred (empty embedding) -> NOT in semantic recall yet ...
    assert fid not in _ids(_sm.recall("shard rotates writes", k=10))
    # ... but immediately keyword-findable, and the daemon was kicked awake.
    assert fid in [f.id for f in _sm.search_facts("shard")]
    assert _heal  # self-heal kicked in

    # backfill makes it recallable
    assert _sm.backfill_pending_embeddings() == 1
    assert fid in _ids(_sm.recall("shard rotates writes", k=10))


@pytest.mark.asyncio
async def test_remember_embeds_when_daemon_warm(_sm, monkeypatch):
    import engram.encode_service as es
    monkeypatch.setattr(es, "daemon_usable", lambda: True)

    out = await _invoke("hippo_remember", {
        "proposition": "The pool warms 16 connections.",
        "topic": "t/nonblock2",
        "confidence": 0.9,
    })
    assert out.get("ok") is True
    fid = out["id"]
    # daemon warm -> embedded now -> immediately recallable, nothing pending
    assert fid in _ids(_sm.recall("pool warms connections", k=10))
    assert _sm.backfill_pending_embeddings() == 0


@pytest.mark.asyncio
async def test_hippo_backfill_embeddings_tool_heals_deferred(_sm, monkeypatch):
    """The hippo_backfill_embeddings MCP tool embeds the deferred rows so an
    agent on the Engram MCP can heal them (symmetric with `engram facts backfill`)."""
    import engram.encode_service as es
    monkeypatch.setattr(es, "daemon_usable", lambda: False)
    monkeypatch.setattr(es, "ensure_running", lambda: False)

    out = await _invoke("hippo_remember", {
        "proposition": "The ring buffer holds 2048 frames.",
        "topic": "t/backfill",
        "confidence": 0.9,
    })
    fid = out["id"]
    assert fid not in _ids(_sm.recall("ring buffer frames", k=10))  # deferred

    bf = await _invoke("hippo_backfill_embeddings", {})
    assert bf.get("backfilled", 0) >= 1
    assert fid in _ids(_sm.recall("ring buffer frames", k=10))  # healed -> recallable
