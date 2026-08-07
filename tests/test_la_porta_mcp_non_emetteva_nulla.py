"""La porta MCP scriveva senza dirlo: zero eventi su 141 scritture.

ws4, 2026-08-07: «il canale MCP non telemetra NULLA — 141 scritture ad
agosto, ZERO eventi `flow.write`. Il meno osservabile è il meno coperto e
i due fatti sono legati» (copertura del moat: CLI 99,2%, MCP 69,5%).

Verificato sul log vero, 8247 eventi `flow.write`:

    sdk 7953 · unknown 208 · gateway 48 · cli 38 · **mcp 0**

E la causa è strutturale, non un tag mancante: `flow.write` compare **zero
volte** in `mcp_server.py`. Quella porta costruisce il `Fact` e chiama
`SemanticMemory.store()` direttamente, senza passare da `Memory.add()` —
che è dove vive l'emissione.

Conseguenze misurabili: la sala motore non ha mai visto una scrittura MCP,
e i campi aggiunti ieri sera (`judged`, `withheld_despite_judge`) su quella
porta non esistono. Un agente che scrive da MCP è invisibile al governo.

⚠️ La cura NON è una quarta copia dell'emissione: è la classe che questo
ramo cura da tre giorni. Una funzione sola (`flow_events.emit_write`), due
chiamanti — `Memory.add` e la porta MCP.
"""
from __future__ import annotations

import json

import pytest

from verimem import event_jsonl_log, flow_events


@pytest.fixture()
def canale(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    flow_events.reset_flow_context()
    return tmp_path


def _write(tmp_path):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines()
            if json.loads(ln).get("name") == "flow.write"]


@pytest.mark.asyncio
async def test_una_scrittura_da_MCP_esce_sul_canale(canale, monkeypatch,
                                                    tmp_path):
    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server
    from verimem.client import Memory

    m = Memory(tmp_path / "m.db")

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = m.semantic

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    handler = mcp_server.server.request_handlers[CallToolRequest]
    await handler(CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(
            name="hippo_remember",
            arguments={"proposition": "the depot holds 10 crates",
                       "topic": "log/a"})))

    evts = _write(canale)
    assert evts, "la porta MCP ha scritto e non l'ha detto"
    p = evts[-1]["payload"]
    assert p["topic"] == "log/a"
    assert p["stored"] is True


@pytest.mark.asyncio
async def test_l_evento_di_MCP_porta_gli_STESSI_campi_di_governo(
        canale, monkeypatch, tmp_path):
    """Non basta che esca: deve portare quello che porta sull'SDK, o la
    sala motore mostrerebbe una riga monca proprio per la porta degli
    agenti."""
    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server
    from verimem.client import Memory

    m = Memory(tmp_path / "m.db")

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = m.semantic

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    handler = mcp_server.server.request_handlers[CallToolRequest]
    await handler(CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(
            name="hippo_remember",
            arguments={"proposition": "the yard holds 5 pallets",
                       "topic": "log/b"})))

    p = _write(canale)[-1]["payload"]
    for campo in ("status", "judged", "grounding_score",
                  "withheld_despite_judge", "fact_id"):
        assert campo in p, f"manca {campo}: {sorted(p)}"


def test_l_emissione_e_UNA_SOLA_funzione_non_una_copia(canale):
    """La cura non può essere una quarta copia: è la classe che questo
    ramo cura da tre giorni. Un solo emettitore, due chiamanti."""
    import inspect

    from verimem import client, flow_events, mcp_server

    assert hasattr(flow_events, "emit_write"), "manca l'emettitore unico"
    assert "emit_write" in inspect.getsource(client), (
        "l'SDK non usa l'emettitore unico")
    assert "emit_write" in inspect.getsource(mcp_server), (
        "la porta MCP non usa l'emettitore unico")


def test_l_emettitore_dichiara_se_il_verdetto_manca(canale):
    """`judged` deve nascere dal punteggio, non da chi chiama: se una porta
    passasse `judged=True` senza punteggio, il campo mentirebbe."""
    flow_events.emit_write(stored=True, status="model_claim", fact_id="f1",
                           topic="t", layers=[], grounding_score=None)
    p = _write(canale)[-1]["payload"]
    assert p["judged"] is False
    assert p["withheld_despite_judge"] is False
