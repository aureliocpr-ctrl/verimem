"""TDD — wiring: hippo_remember auto-invalida i fatti che il gate L3 segnala
come contraddetti dal NUOVO fatto (P0a, 2026-06-02).

Il gate (`run_validation_gate`) gia calcola `contradicting_fact_ids` ma
l'handler non li usava: un fatto smentito restava live nel recall. Qui si
verifica che, dopo lo store, l'handler chiami
`SemanticMemory.auto_supersede_on_contradiction(new_id, contradicting_ids)`.

Robustezza: NON dipendiamo dal verdetto reale di validate_claim — monkeypatch
del gate (import locale risolto a runtime da `verimem.anti_confab_gate`) per
ritornare un contradicting_fact_ids deterministico. Cosi il test isola il
WIRING, non la detection. HERMETIC: SemanticMemory su tmp_path.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from verimem import anti_confab_gate, mcp_server
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


async def test_write_path_supersedes_gate_contradiction(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    # Vecchio claim DEBOLE (legacy=rank0) che il nuovo fatto smentira'.
    sm.store(Fact(id="oldcap",
                  proposition="ai-eye pilota agy via WriteConsoleInputW",
                  topic="lessons/tools/ai-eye", status="legacy_unverified"))
    agent = _FakeAgent(sm)
    monkeypatch.setattr(mcp_server, "_ag", lambda: agent)

    # Forza il gate a segnalare la contraddizione con il vecchio (persist =
    # il nuovo fatto sopravvive a model_claim=rank2 > legacy).
    def _fake_gate(**kw):
        return anti_confab_gate.GateResult(
            action="persist", contradicting_fact_ids=["oldcap"],
        )
    monkeypatch.setattr(anti_confab_gate, "run_validation_gate", _fake_gate)

    blocks = await _invoke_tool("hippo_remember", {
        "proposition": "ai-eye NON pilota agy (ConPTY): timeout verificato 2026-06-02",
        "topic": "lessons/tools/ai-eye",
        "status": "model_claim",
    })
    payload = _payload(blocks)
    assert payload.get("ok") is True

    old = sm.get("oldcap")
    assert old is not None                       # invalidate, NON delete
    assert old.superseded_by is not None         # il nuovo fatto lo ha superseded
    assert old.superseded_by != "oldcap"


async def test_write_path_no_supersede_when_gate_silent(tmp_path, monkeypatch):
    """Nessun contradicting_fact_ids -> nessuna supersession (no-op sicuro)."""
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    sm.store(Fact(id="keep", proposition="fatto indipendente",
                  topic="t/keep", status="model_claim"))
    agent = _FakeAgent(sm)
    monkeypatch.setattr(mcp_server, "_ag", lambda: agent)

    def _fake_gate(**kw):
        return anti_confab_gate.GateResult(action="persist")
    monkeypatch.setattr(anti_confab_gate, "run_validation_gate", _fake_gate)

    blocks = await _invoke_tool("hippo_remember", {
        "proposition": "un altro fatto qualunque",
        "topic": "t/other", "status": "model_claim",
    })
    assert _payload(blocks).get("ok") is True
    assert sm.get("keep").superseded_by is None   # intatto
