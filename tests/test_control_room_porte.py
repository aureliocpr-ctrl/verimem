"""Le QUATTRO porte della sala di controllo — nessun aggancio scollegato.

La classe di difetto misurata il 2026-08-04 (sei istanze in una notte, ws4):
«il meccanismo c'è, l'enum lo prevede, il chiamante non lo alimenta» — e la sua
gemella «una garanzia presente su UNA superficie e assente sulle altre» (ws5:
astensione solo su explain, versioning solo sui documenti, evidence ceiling
solo su MCP). Questo banco impedisce alla sala di controllo di nascere con la
stessa malattia: ogni funzione di governo è verificata su OGNI porta.

- SDK   : Memory.retirement_log / survivability / undo
- CLI   : verimem facts retirement-log (via typer CliRunner)
- MCP   : hippo_retirement_log (dispatcher reale, pattern test_mcp_undo_api)
- HTTP  : GET /v1/retirements · POST /v1/memories/{id}/restore ·
          POST /v1/undo/{op_id} — le rotte che mancavano: prima il cliente
          HTTP vedeva la quarantena senza poterci fare nulla e DELETE era
          l'unica azione esposta (ws4: «mostrare senza permettere di agire
          è peggio che non mostrare»).
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from verimem.client import Memory

_MILAN = "the office headquarters are in Milan"
_ROME = "the office headquarters moved to Rome"


def _ritiro(m: Memory) -> dict[str, str]:
    a = m.add(_MILAN, topic="hq/sedi", verified_by=["hr-doc"])["id"]
    r = m.add(_ROME, topic="hq/sedi", verified_by=["hr-doc"])["id"]
    m.semantic.supersede(a, r, principal="test:porte", reason="sede spostata")
    return {"loser": a, "winner": r}


# ---- porta 1: SDK ------------------------------------------------------------

def test_sdk_retirement_log_survivability_undo(tmp_path):
    m = Memory(tmp_path / "m.db")
    ids = _ritiro(m)
    rows = m.retirement_log()
    assert rows and rows[0]["loser_id"] == ids["loser"]
    q = m.survivability(topic="hq/sedi")
    assert q["retired"] == 1 and "formula" in q
    undo = m.undo(rows[0]["undo_op_id"])
    assert undo["ok"] is True and undo["action"] == "restored"
    assert m.survivability(topic="hq/sedi")["retired"] == 0


# ---- porta 2: CLI ------------------------------------------------------------

def test_cli_facts_retirement_log(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from verimem.cli import app
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    m = Memory(tmp_path / "semantic" / "semantic.db")
    ids = _ritiro(m)

    runner = CliRunner()
    res = runner.invoke(app, ["facts", "retirement-log"])
    assert res.exit_code == 0, res.output
    assert ids["loser"][:8] in res.output.replace("\n", ""), (
        "la CLI deve mostrare la coppia del ritiro")
    res2 = runner.invoke(app, ["facts", "retirement-log", "--counts"])
    assert res2.exit_code == 0, res2.output
    assert "retired=1" in res2.output
    assert "servable =" in res2.output, "la formula viaggia col numero"


# ---- porta 3: MCP ------------------------------------------------------------

@pytest.fixture
def mcp_sm(tmp_path, monkeypatch):
    from verimem import mcp_server
    m = Memory(tmp_path / "m.db")

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = m.semantic

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    return m


async def _invoke(name: str, arguments: dict | None = None) -> dict[str, Any]:
    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    text = next(c.text for c in payload.content if hasattr(c, "text"))
    return json.loads(text)


@pytest.mark.asyncio
async def test_mcp_retirement_log_rows_and_counts(mcp_sm):
    m = mcp_sm
    ids = _ritiro(m)
    out = await _invoke("hippo_retirement_log")
    assert out["ok"] is True
    assert out["items"][0]["loser_id"] == ids["loser"]
    assert out["items"][0]["reversible"] is True
    counts = await _invoke("hippo_retirement_log", {"counts": True})
    assert counts["retired"] == 1 and "formula" in counts


# ---- porta 4: HTTP -----------------------------------------------------------

def test_http_retirements_restore_undo(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from verimem.gateway import GatewayKeys, create_app

    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    key = keys.create(tenant_id="t1", name="ci")
    client = TestClient(create_app(data_dir=tmp_path, keys=keys))
    hdr = {"Authorization": f"Bearer {key}"}

    # due scritture ammesse via HTTP, ritiro sul loro store del tenant
    r1 = client.post("/v1/memories", json={"content": _MILAN,
                                           "topic": "hq/sedi"}, headers=hdr)
    r2 = client.post("/v1/memories", json={"content": _ROME,
                                           "topic": "hq/sedi"}, headers=hdr)
    assert r1.status_code == 200 and r2.status_code == 200
    a, b = r1.json()["id"], r2.json()["id"]
    from verimem.semantic import SemanticMemory
    sm = SemanticMemory(db_path=tmp_path / "tenants" / "t1" / "memory.db")
    sm.supersede(a, b, principal="test:porte", reason="sede spostata")

    # GET /v1/retirements: la coppia, con l'handle
    got = client.get("/v1/retirements", headers=hdr)
    assert got.status_code == 200, got.text
    items = got.json()["items"]
    assert items and items[0]["loser_id"] == a
    assert "loser_text" not in items[0], "il feed HTTP porta metadati, non testi"
    op_id = items[0]["undo_op_id"]
    assert op_id

    # counts=true: il quartetto con la formula
    q = client.get("/v1/retirements?counts=true", headers=hdr).json()
    assert q["retired"] == 1 and "formula" in q

    # POST /v1/undo/{op_id}: il ritiro si annulla via HTTP
    und = client.post(f"/v1/undo/{op_id}", headers=hdr)
    assert und.status_code == 200, und.text
    assert und.json()["action"] == "restored"
    assert client.get("/v1/retirements?counts=true",
                      headers=hdr).json()["retired"] == 0


def test_http_restore_quarantined(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from verimem.gateway import GatewayKeys, create_app

    monkeypatch.setenv("ENGRAM_L1_STRICT", "1")
    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    key = keys.create(tenant_id="t1", name="ci")
    client = TestClient(create_app(data_dir=tmp_path, keys=keys))
    hdr = {"Authorization": f"Bearer {key}"}

    r = client.post("/v1/memories", json={
        "content": "everything works perfectly and is fully verified",
        "topic": "hype"}, headers=hdr)
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "quarantined", (
        f"era uno `skip`, e lo skip rendeva questo guardiano VERDE proprio "
        f"nel caso in cui il gate avesse smesso di quarantinare. Se la "
        f"promessa principale cade, qui deve uscire un rosso: {body}")
    fid = body["id"]
    rest = client.post(f"/v1/memories/{fid}/restore", headers=hdr)
    assert rest.status_code == 200, rest.text
    assert rest.json()["restored"] is True, (
        "il falso positivo si libera dalla stessa porta che lo mostra")
