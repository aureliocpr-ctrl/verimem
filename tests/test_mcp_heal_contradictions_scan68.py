"""TDD — MCP tool hippo_heal_contradictions (P0a/4, 2026-06-02).

Espone heal_contradictions come tool MCP attivabile (da Aurelio o da un
daemon): processa le contraddizioni non risolte e auto-supersede il fatto
piu debole verso il piu forte. Verifica end-to-end via l'handler MCP reale.
HERMETIC (SemanticMemory + ContradictionStore su tmp_path).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engram import mcp_server
from engram.contradiction import Contradiction, ContradictionStore
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


def _payload(blocks: list[str]) -> dict[str, Any]:
    return json.loads(blocks[0])


async def test_mcp_heal_contradictions_supersedes_weaker(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    store = ContradictionStore(sm.db_path)
    sm.store(Fact(id="weak", proposition="NEXUS has 17280 tests",
                  topic="project/nexus/tests", status="legacy_unverified"))
    sm.store(Fact(id="strong", proposition="NEXUS has 9999 tests",
                  topic="project/nexus/tests", status="model_claim"))
    store.add(Contradiction(fact_a_id="weak", fact_b_id="strong",
                            kind="numeric_clash", similarity=0.95))
    agent = _FakeAgent(sm)
    monkeypatch.setattr(mcp_server, "_ag", lambda: agent)

    payload = _payload(await _invoke_tool("hippo_heal_contradictions", {}))

    assert "weak" in payload["healed_superseded"]
    assert payload["total_unresolved"] == 0
    assert sm.get("weak").superseded_by == "strong"
    assert sm.get("strong").superseded_by is None


async def test_mcp_heal_contradictions_empty_is_noop(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    ContradictionStore(sm.db_path)  # crea la tabella, nessuna contraddizione
    agent = _FakeAgent(sm)
    monkeypatch.setattr(mcp_server, "_ag", lambda: agent)

    payload = _payload(await _invoke_tool("hippo_heal_contradictions", {}))

    assert payload["healed_superseded"] == []
    assert payload["total_unresolved"] == 0
