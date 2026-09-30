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

from verimem import mcp_server
from verimem.contradiction import Contradiction, ContradictionStore
from verimem.semantic import Fact, SemanticMemory


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


async def test_mcp_heal_lascia_aperto_uno_scontro_booleano_e_lo_conta(
        tmp_path, monkeypatch):
    """Dal 29/09 anche gli scontri ``boolean_clash`` restano aperti e contati:
    su una copia dello store il heal ne ritirava 172, fra cui di nuovo i 41
    fatti appena ripristinati. Fino al 29/09 qui si provava il ritiro del lato
    debole; la regola dei ranghi si prova in test_heal_contradictions_scan68.py
    chiedendo i tipi esplicitamente."""
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    store = ContradictionStore(sm.db_path)
    sm.store(Fact(id="weak", proposition="The NEXUS cache is not enabled",
                  topic="project/nexus/cache", status="legacy_unverified"))
    sm.store(Fact(id="strong", proposition="The NEXUS cache is enabled",
                  topic="project/nexus/cache", status="model_claim"))
    store.add(Contradiction(fact_a_id="weak", fact_b_id="strong",
                            kind="boolean_clash", similarity=0.95))
    agent = _FakeAgent(sm)
    monkeypatch.setattr(mcp_server, "_ag", lambda: agent)

    payload = _payload(await _invoke_tool("hippo_heal_contradictions", {}))

    assert payload["healed_superseded"] == [], payload
    assert sm.get("weak").superseded_by is None
    assert sm.get("strong").superseded_by is None
    assert payload["left_open_kinds"] == {"numeric_clash": 0, "boolean_clash": 1}, payload
    assert payload["total_unresolved"] == 1


async def test_mcp_heal_lascia_aperto_uno_scontro_numerico_e_lo_conta(
        tmp_path, monkeypatch):
    """La promessa alla porta MCP: lo strumento non ritira un fatto per uno
    scontro ``numeric_clash`` (T222: 41 fatti veri ritirati il 23-24/09) e
    dice quanti ne ha lasciati aperti, con un conteggio e non con gli id."""
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

    assert payload["healed_superseded"] == [], payload
    assert sm.get("weak").superseded_by is None
    assert payload["left_open_kinds"] == {"numeric_clash": 1, "boolean_clash": 0}, payload
    assert payload["total_unresolved"] == 1


async def test_mcp_heal_contradictions_empty_is_noop(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    ContradictionStore(sm.db_path)  # crea la tabella, nessuna contraddizione
    agent = _FakeAgent(sm)
    monkeypatch.setattr(mcp_server, "_ag", lambda: agent)

    payload = _payload(await _invoke_tool("hippo_heal_contradictions", {}))

    assert payload["healed_superseded"] == []
    assert payload["total_unresolved"] == 0
