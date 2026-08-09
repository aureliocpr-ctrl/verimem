"""La distribuzione dei ritiri esce da tutte e quattro le porte.

La regola che mi sono imposto su questo ramo: una funzione di governo esce
su TUTTE le porte nello stesso commit, non nel prossimo. Qui pesa più del
solito, perché la domanda a cui risponde — «è un tasso o è stato un
evento?» — se la pone chi legge da MCP (un agente) tanto quanto chi legge
dalla CLI, e su HTTP la pone un cliente che deve fidarsi.
"""
from __future__ import annotations

import sqlite3
import time

import pytest

from verimem.client import Memory


def _prepara(m: Memory) -> None:
    ora = time.time()
    for i in range(3):
        a = m.add(f"the depot {i} holds 10 crates", topic=f"log/a{i}")["id"]
        b = m.add(f"the depot {i} holds 20 crates", topic=f"log/b{i}")["id"]
        m.semantic.supersede(a, b, principal="test", reason="daily collapse")
        with sqlite3.connect(m.semantic.db_path) as con:
            con.execute("UPDATE facts SET superseded_at = ?, "
                        "superseded_reason = ? WHERE id = ?",
                        (ora, "daily collapse", a))


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
        params=CallToolRequestParams(name="hippo_retirement_log",
                                     arguments={"breakdown": True})))
    payload = res.root if hasattr(res, "root") else res
    out = _json.loads(next(c.text for c in payload.content
                           if hasattr(c, "text")))

    assert out["by_reason"][0]["reason"] == "daily collapse"
    assert out["by_reason"][0]["n"] == 3
    assert out["concentration"]["share"] == 1.0


def test_porta_HTTP(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from verimem.gateway import GatewayKeys, create_app

    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    key = keys.create(tenant_id="t1", name="ci")
    client = TestClient(create_app(data_dir=tmp_path, keys=keys))
    hdr = {"Authorization": f"Bearer {key}"}

    r1 = client.post("/v1/memories", json={"content": "the depot holds 10 crates",
                                           "topic": "log/a"}, headers=hdr)
    r2 = client.post("/v1/memories", json={"content": "the depot holds 20 crates",
                                           "topic": "log/b"}, headers=hdr)
    a, b = r1.json()["id"], r2.json()["id"]
    with sqlite3.connect(tmp_path / "tenants" / "t1" / "memory.db") as con:
        con.execute("UPDATE facts SET superseded_by = ?, superseded_at = ?, "
                    "superseded_reason = ? WHERE id = ?",
                    (b, time.time(), "daily collapse", a))

    out = client.get("/v1/retirements?breakdown=true", headers=hdr).json()
    assert out["total_retired"] == 1
    assert out["by_reason"][0]["reason"] == "daily collapse"
    assert "busiest day" in out["concentration"]["formula"].lower()


def test_porta_CLI(tmp_path, monkeypatch, capsys):
    """La CLI e' la porta da cui un umano guarda il corpus: se la
    distribuzione non esce di li', la domanda se la pone solo chi legge
    codice."""
    from typer.testing import CliRunner

    from verimem.cli import app

    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    m = Memory(tmp_path / "semantic" / "semantic.db")
    _prepara(m)

    res = CliRunner().invoke(app, ["facts", "retirement-log", "--breakdown"])
    assert res.exit_code == 0, res.output
    assert "daily collapse" in res.output
    assert "concentration" in res.output
