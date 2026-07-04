"""Cycle #110.D — MCP dispatch test for hippo_legacy_audit.

End-to-end via real SemanticMemory + MCP request handler.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from engram import mcp_server
from engram.semantic import Fact, SemanticMemory


class _FakeAgent:
    def __init__(self, sm: SemanticMemory) -> None:
        self.semantic = sm


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
def agent_with_mixed_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> _FakeAgent:
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    now = time.time()
    sm.store(Fact(id="ver", proposition="cycle 110 schema sha256:deadbeef",
                   topic="t", confidence=0.6,
                   created_at=now - 60 * 86400))
    sm.store(Fact(id="forget", proposition="TODO",
                   topic="t", confidence=0.2,
                   created_at=now - 300 * 86400))
    sm.store(Fact(id="rec", proposition="Aurelio prefers Italian conversation",
                   topic="t", confidence=0.7,
                   created_at=now - 20 * 86400))
    agent = _FakeAgent(sm)
    monkeypatch.setattr(mcp_server, "_ag", lambda: agent)
    return agent


def _payload(blocks: list[str]) -> dict[str, Any]:
    return json.loads(blocks[0])


class TestLegacyAuditMCP:

    @pytest.mark.asyncio
    async def test_tool_listed(
        self, agent_with_mixed_facts: _FakeAgent,
    ) -> None:
        from mcp.types import ListToolsRequest, PaginatedRequestParams
        handler = mcp_server.server.request_handlers[ListToolsRequest]
        result = await handler(ListToolsRequest(
            method="tools/list", params=PaginatedRequestParams(),
        ))
        payload = result.root if hasattr(result, "root") else result
        names = {tool.name for tool in payload.tools}
        assert "hippo_legacy_audit" in names

    @pytest.mark.asyncio
    async def test_audit_returns_bucket_counts(
        self, agent_with_mixed_facts: _FakeAgent,
    ) -> None:
        # status_filter='any' because we're on main where Fact has no status
        blocks = await _invoke_tool(
            "hippo_legacy_audit", {"status_filter": "any"},
        )
        payload = _payload(blocks)
        assert payload["total_classified"] == 3
        counts = payload["bucket_counts"]
        assert counts["verified_on_rereading"] == 1
        assert counts["forgettable"] == 1
        assert counts["recoverable"] == 1

    @pytest.mark.asyncio
    async def test_audit_includes_samples(
        self, agent_with_mixed_facts: _FakeAgent,
    ) -> None:
        blocks = await _invoke_tool(
            "hippo_legacy_audit",
            {"status_filter": "any", "sample_per_bucket": 5},
        )
        payload = _payload(blocks)
        assert "samples" in payload
        for bucket in (
            "verified_on_rereading", "forgettable", "recoverable",
        ):
            assert bucket in payload["samples"]

    @pytest.mark.asyncio
    async def test_invalid_status_filter_rejected(
        self, agent_with_mixed_facts: _FakeAgent,
    ) -> None:
        # Skip the schema enum gate by going through the request handler
        # with a value that satisfies the enum (no enum gate at protocol
        # for this property in our schema? Verify dispatch path).
        from mcp.types import CallToolRequest, CallToolRequestParams
        handler = mcp_server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(
                name="hippo_legacy_audit",
                arguments={"status_filter": "totally_bogus"},
            ),
        )
        result = await handler(req)
        payload = result.root if hasattr(result, "root") else result
        text = payload.content[0].text
        # Either protocol-layer rejection or dispatch-layer error,
        # both are acceptable safe paths.
        assert payload.isError or '"error"' in text
