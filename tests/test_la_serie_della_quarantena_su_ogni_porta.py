"""La serie della quarantena esce da tutte le porte — e la CLI il listato
non ce l'aveva affatto.

Cercando dove mettere la serie ho trovato un'asimmetria che nessuno aveva
notato: il listato dei claim fermati esisteva su **SDK, MCP e HTTP** e non
sulla CLI, cioè mancava proprio sulla porta da cui un umano guarda il
corpus. È la stessa classe che questo ramo ha già curato tre volte, e
stavolta si è presentata da sé.
"""
from __future__ import annotations

import sqlite3
import time

import pytest

from verimem.client import Memory


def _prepara(m: Memory) -> None:
    ora = time.time()
    for i in range(3):
        fid = m.add(f"the depot {i} holds crates", topic=f"log/{i}")["id"]
        with sqlite3.connect(m.semantic.db_path) as con:
            con.execute("UPDATE facts SET created_at = ? WHERE id = ?",
                        (ora, fid))
        if i < 2:
            m.semantic.quarantine_fact(fid, reason="banco")


def test_porta_CLI_il_listato_che_non_esisteva(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from verimem.cli import app

    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    _prepara(Memory(tmp_path / "semantic" / "semantic.db"))

    res = CliRunner().invoke(app, ["facts", "quarantine-log"])
    assert res.exit_code == 0, res.output
    assert "log/0" in res.output or "log/1" in res.output, res.output


def test_porta_CLI_la_serie(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from verimem.cli import app

    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    _prepara(Memory(tmp_path / "semantic" / "semantic.db"))

    res = CliRunner().invoke(app, ["facts", "quarantine-log", "--breakdown"])
    assert res.exit_code == 0, res.output
    assert "written" in res.output and "quarantined" in res.output


@pytest.mark.asyncio
async def test_porta_MCP(tmp_path, monkeypatch):
    import json as _json

    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server

    m = Memory(tmp_path / "m.db")
    _prepara(m)

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = m.semantic

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    handler = mcp_server.server.request_handlers[CallToolRequest]
    res = await handler(CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name="hippo_quarantine_log",
                                     arguments={"breakdown": True})))
    payload = res.root if hasattr(res, "root") else res
    out = _json.loads(next(c.text for c in payload.content
                           if hasattr(c, "text")))

    assert out["quarantined"] == 2
    assert out["by_day"][0]["written"] == 3
    assert out["by_day"][0]["rate"] == pytest.approx(2 / 3, abs=0.01)


def test_porta_HTTP(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from verimem.gateway import GatewayKeys, create_app

    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    key = keys.create(tenant_id="t1", name="ci")
    client = TestClient(create_app(data_dir=tmp_path, keys=keys))
    hdr = {"Authorization": f"Bearer {key}"}

    r = client.post("/v1/memories",
                    json={"content": "The migration is complete and verified.",
                          "topic": "rel"}, headers=hdr)
    assert r.json()["status"] == "quarantined", r.json()

    out = client.get("/v1/quarantine?breakdown=true", headers=hdr).json()
    assert out["quarantined"] == 1
    assert out["by_day"][0]["quarantined"] == 1
    assert "busiest day" in out["concentration"]["formula"].lower()
