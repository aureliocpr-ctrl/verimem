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


class _SpyRemote:
    """A thin-client stand-in whose .search/.add record their calls, so a test
    can assert an op was (or was NOT) delegated to the shared server."""
    def __init__(self, hits):
        self._hits = hits
        self.searched: list[tuple[str, int]] = []
        self.added: list[tuple[str, dict]] = []

    def search(self, q, k=5, **kw):
        self.searched.append((q, k))
        return list(self._hits)

    def add(self, content, **kw):
        self.added.append((content, kw))
        return {"stored": True, "id": "srv-add", "status": "model_claim"}


_HIT = {"id": "srv-9", "text": "The tank holds 500 liters.", "topic": "ops/tank",
        "score": 0.91, "status": "model_claim", "verified_by": [],
        "grounding_score": 88, "created_at": 1784000000.0,
        "confidence_tier": "high"}


@pytest.mark.asyncio
async def test_hippo_facts_recall_delegates_to_server(monkeypatch):
    spy = _SpyRemote([_HIT])
    monkeypatch.setattr(mcp_server, "_remote", lambda: spy)
    monkeypatch.setattr(mcp_server, "_ag",
                        lambda: (_ for _ in ()).throw(
                            AssertionError("local agent built despite server")))
    blocks = await _invoke_tool("hippo_facts_recall",
                                {"query": "tank capacity", "k": 5})
    payload = json.loads(blocks[0])
    assert payload.get("remote") is True
    assert spy.searched == [("tank capacity", 5)]
    row = payload["items"][0]
    assert row["proposition"] == "The tank holds 500 liters."  # text -> proposition
    assert row["id"] == "srv-9" and row["remote"] is True
    assert "confidence" not in row          # honest: REST gives no numeric confidence


@pytest.mark.asyncio
async def test_hippo_facts_search_delegates_to_server(monkeypatch):
    spy = _SpyRemote([_HIT])
    monkeypatch.setattr(mcp_server, "_remote", lambda: spy)
    monkeypatch.setattr(mcp_server, "_ag",
                        lambda: (_ for _ in ()).throw(
                            AssertionError("local agent built despite server")))
    blocks = await _invoke_tool("hippo_facts_search",
                                {"query": "reserve tank", "limit": 10})
    payload = json.loads(blocks[0])
    assert payload.get("remote") is True
    assert spy.searched == [("reserve tank", 10)]      # 'limit' honored for search
    assert payload["items"][0]["proposition"] == "The tank holds 500 liters."


@pytest.mark.asyncio
async def test_scoped_recall_does_not_delegate_to_server(monkeypatch, tmp_data_dir):
    """A scoped read (user_id/agent_id/run_id) must NOT hit the shared server's
    unscoped search - that would drop the isolation filter. It stays local."""
    spy = _SpyRemote([_HIT])
    monkeypatch.setattr(mcp_server, "_remote", lambda: spy)
    blocks = await _invoke_tool("hippo_facts_recall",
                                {"query": "q", "k": 5, "user_id": "u1"})
    payload = json.loads(blocks[0])
    assert payload.get("remote") is not True     # served locally, not by the server
    assert spy.searched == []                     # scope kept the read off the server


@pytest.mark.asyncio
async def test_scoped_remember_does_not_delegate_to_server(monkeypatch, tmp_data_dir):
    """SECURITY: a SCOPED write (user_id/agent_id/run_id) must NOT be delegated
    to the shared server's unscoped add - that would store the fact WITHOUT its
    tenant prefix in the shared corpus, so any unscoped read from another
    session would return it (cross-tenant leak). It stays local, where
    scoped_topic isolates it. Symmetric with the scoped-read guard.
    (Adversarial critic counterexample, job 9166607ae84ad54f.)"""
    spy = _SpyRemote([])
    monkeypatch.setattr(mcp_server, "_remote", lambda: spy)
    blocks = await _invoke_tool("hippo_remember",
                                {"proposition": "alice private note.",
                                 "topic": "notes", "user_id": "alice"})
    payload = json.loads(blocks[0])
    assert payload.get("remote") is not True     # served locally, not by the server
    assert spy.added == []                         # scope kept the write off the shared corpus


@pytest.mark.asyncio
async def test_thin_mode_refuses_a_read_it_cannot_delegate(monkeypatch, tmp_data_dir):
    """Kimi audit F3: only remember/recall/search have a thin-tier path. Every
    OTHER fact-reading tool still hits the LOCAL store — which, for a session
    that lives behind a shared server, is empty. Returning that as a normal
    answer reports "no facts" as if it were the complete corpus: a silent wrong
    answer, strictly worse than an error."""
    class _Healthy:
        def search(self, q, k=5, **kw):
            return []
    monkeypatch.setattr(mcp_server, "_remote", lambda: _Healthy())
    blocks = await _invoke_tool("hippo_facts_recent", {"limit": 5})
    payload = json.loads(blocks[0])
    blob = json.dumps(payload).lower()
    assert not payload.get("items"), "handed back a fake-complete local answer"
    assert ("shared" in blob or "server" in blob or "error" in blob), (
        f"no explicit refusal, just an empty-looking answer: {payload}")


@pytest.mark.asyncio
async def test_same_read_works_normally_without_a_server(monkeypatch, tmp_data_dir):
    """The refusal is narrow: with no server configured nothing changes."""
    monkeypatch.setattr(mcp_server, "_remote", lambda: None)
    blocks = await _invoke_tool("hippo_facts_recent", {"limit": 5})
    payload = json.loads(blocks[0])
    assert "items" in payload or "facts" in payload   # the normal local answer


@pytest.mark.asyncio
async def test_auth_rejection_fails_closed_not_silent_local(monkeypatch, tmp_data_dir):
    """SECURITY (Kimi red-team audit F1): a server that REJECTS our key must NOT
    degrade silently to the local store. That neutralizes central key revocation
    (the agent keeps working locally) and diverges the 'shared' corpus invisibly.
    Server DOWN -> fail-soft local (never strand). Server REJECTS US -> fail-CLOSED
    with an explicit error."""
    class _RejectingRemote:
        def add(self, content, **kw):
            raise PermissionError("verimem server rejected the API key (401)")
        def search(self, q, k=5, **kw):
            raise PermissionError("verimem server rejected the API key (401)")

    monkeypatch.setattr(mcp_server, "_remote", lambda: _RejectingRemote())
    blocks = await _invoke_tool("hippo_remember",
                                {"proposition": "must not land locally.",
                                 "topic": "authtest"})
    payload = json.loads(blocks[0])
    blob = json.dumps(payload).lower()
    assert payload.get("remote") is not True
    assert not payload.get("ok")            # the write did NOT quietly succeed
    assert ("key" in blob or "auth" in blob or "401" in blob)  # explicit, not silent


@pytest.mark.asyncio
async def test_read_with_unsupported_filter_does_not_delegate(monkeypatch, tmp_data_dir):
    """Kimi red-team audit F4: the REST search carries only (query, k). A recall
    asking for topic / as_of / min_status / trust_signals must NOT be served by
    the UNFILTERED server search with the filter silently dropped - and echoed
    back as if it had been applied ("topic": <requested>). Same rule as the scope
    guard: a filter the remote cannot honor keeps the read local."""
    for extra in ({"topic": "project/secret"}, {"as_of": 1784000000.0},
                  {"min_status": "verified"}, {"trust_signals": True}):
        spy = _SpyRemote([_HIT])
        monkeypatch.setattr(mcp_server, "_remote", lambda s=spy: s)
        blocks = await _invoke_tool("hippo_facts_recall",
                                    {"query": "tank", "k": 5, **extra})
        payload = json.loads(blocks[0])
        assert payload.get("remote") is not True, f"delegated despite {extra}"
        assert spy.searched == [], f"remote search called despite {extra}"


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
