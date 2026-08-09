"""La vista dei verdetti contraddetti esce da OGNI porta, non solo dalla CLI.

Il principio l'ho consegnato io su questo ramo (`d5442fab`): una funzione
di governo esce su tutte le porte nello stesso commit, altrimenti nasce
la classe di difetto che stiamo curando da due giorni — la garanzia è
unica e il modo di leggerla no.

E poi l'ho violato io stesso stamattina: `verdict_mismatches` è arrivato
con `11146748` e `7b8dbf05` **solo su `verimem facts retirement-log
--mismatches`**. Un agente che parla MCP, un cliente HTTP e chi usa l'SDK
non avevano modo di sapere che il proprio corpus contiene fatti serviti
con un verdetto di bocciatura — che è esattamente la domanda per cui
questo prodotto esiste.

Le tre righe che la vista restituisce (giudicato-vero-trattenuto,
giudicato-falso-servito, banda contesa) devono avere lo STESSO nome su
ogni porta: un client che legge `judged_false_but_served` non può trovarlo
scritto in un altro modo altrove.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

import pytest

from verimem.client import Memory

_FONTE = "Company handbook: our head office is located in Milan, Italy."
_CHIAVI = {"judged_true_but_withheld", "judged_false_but_served",
           "contested_band", "thresholds"}


def _corpus(db_path) -> Memory:
    """Un fatto SERVITO con un verdetto sotto qualunque taglio: è il caso
    grave, dieci volte sul corpus reale."""
    m = Memory(db_path)
    r = m.add("the office headquarters are in Milan", topic="hq",
              source=_FONTE)
    with sqlite3.connect(m.semantic.db_path) as con:
        con.execute("UPDATE facts SET grounding_score = 3.2 WHERE id = ?",
                    (r["id"],))
    m._atteso = r["id"]  # type: ignore[attr-defined]
    return m


# ---- porta 1: SDK ------------------------------------------------------------

def test_sdk_espone_i_mismatch(tmp_path):
    m = _corpus(tmp_path / "m.db")
    out = m.verdict_mismatches()
    assert _CHIAVI <= set(out), out
    assert m._atteso in [x["fact_id"] for x in out["judged_false_but_served"]]


# ---- porta 2: CLI ------------------------------------------------------------

def test_cli_espone_i_mismatch(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from verimem.cli import app

    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    m = _corpus(tmp_path / "semantic" / "semantic.db")

    res = CliRunner().invoke(app, ["facts", "retirement-log", "--mismatches"])
    assert res.exit_code == 0, res.output
    assert m._atteso[:8] in res.output.replace("\n", "")


# ---- porta 3: MCP ------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_espone_i_mismatch(tmp_path, monkeypatch):
    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server

    m = _corpus(tmp_path / "m.db")

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = m.semantic

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    handler = mcp_server.server.request_handlers[CallToolRequest]
    res = await handler(CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name="hippo_retirement_log",
                                     arguments={"mismatches": True})))
    payload = res.root if hasattr(res, "root") else res
    out: dict[str, Any] = json.loads(
        next(c.text for c in payload.content if hasattr(c, "text")))

    assert out.get("ok") is True, out
    assert _CHIAVI <= set(out), sorted(out)
    assert m._atteso in [x["fact_id"] for x in out["judged_false_but_served"]]


# ---- porta 4: HTTP -----------------------------------------------------------

def test_http_espone_i_mismatch(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from verimem.gateway import GatewayKeys, create_app

    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    key = keys.create(tenant_id="t1", name="ci")
    client = TestClient(create_app(data_dir=tmp_path, keys=keys))
    hdr = {"Authorization": f"Bearer {key}"}

    r = client.post("/v1/memories",
                    json={"content": "the office headquarters are in Milan",
                          "topic": "hq", "source": _FONTE}, headers=hdr)
    assert r.status_code == 200
    fid = r.json()["id"]
    # stesso stato dei dieci del corpus reale: servito, verdetto sotto il
    # taglio. Lo store del tenant sta in <data_dir>/tenants/<id>/memory.db
    with sqlite3.connect(tmp_path / "tenants" / "t1" / "memory.db") as con:
        con.execute("UPDATE facts SET grounding_score = 3.2 WHERE id = ?",
                    (fid,))

    out = client.get("/v1/retirements?mismatches=true", headers=hdr)
    assert out.status_code == 200, out.text
    body = out.json()
    assert _CHIAVI <= set(body), sorted(body)
    assert fid in [x["fact_id"] for x in body["judged_false_but_served"]]


# ---- la garanzia trasversale -------------------------------------------------

def test_le_quattro_porte_usano_LE_STESSE_chiavi(tmp_path):
    """Il test che vale più dei quattro sopra: le stesse chiavi ovunque.
    Un client che legge `judged_false_but_served` non deve trovarlo
    scritto in un altro modo su un'altra porta — è la classe di difetto
    che ws4 ha misurato stasera sul campo `moat` (enum di qua, prosa di
    là), e che qui viene chiusa prima di nascere."""
    m = _corpus(tmp_path / "m.db")
    dal_modulo = __import__("verimem.retirement_log", fromlist=["x"]) \
        .verdict_mismatches(m.semantic)
    assert set(m.verdict_mismatches()) == set(dal_modulo)
    for k in ("judged_true_but_withheld", "judged_false_but_served",
              "contested_band"):
        assert isinstance(dal_modulo[k], list)
