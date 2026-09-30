"""Un agente non toglie da solo dalla quarantena ciò che ha scritto (Atlas, 29/09).

Fino a qui ``hippo_quarantine_restore`` liberava qualsiasi fatto: un agente che
scriveva una confabulazione, trattenuta dal gate, poteva rimetterla in recall
con una chiamata. Via MCP ogni scrittura e ogni richiesta porta la stessa
etichetta, ``mcp:unbound``; con la regola nello store
(``SemanticMemory.libera_dalla_quarantena``) chi ha scritto non libera, quindi un
fatto scritto via MCP lo libera una persona dalla CLI (``verimem facts release``),
e la ricevuta dice chi ha liberato cosa.

⚠️ Sono etichette, non identità autenticate: la regola separa le porte e gli
attori dichiarati, non ferma chi mente sulla propria etichetta.
"""
from __future__ import annotations

import json
import sqlite3

import pytest
from typer.testing import CliRunner

from verimem import mcp_server
from verimem.semantic import Fact, SemanticMemory

PROPOSIZIONE = "The due-diligence review was completed before the acquisition closed."


@pytest.fixture
def sm(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")

    class _Agente:
        semantic = sm

    monkeypatch.setattr(mcp_server, "_ag", lambda: _Agente())
    monkeypatch.delenv("VERIMEM_ACTOR", raising=False)
    monkeypatch.delenv("ENGRAM_ACTOR", raising=False)
    return sm


def _in_quarantena(sm: SemanticMemory, scritto_da: str) -> str:
    f = Fact(proposition=PROPOSIZIONE, topic="legal/deal", status="quarantined",
             writer_principal=scritto_da)
    sm.store(f)
    return f.id


def _stato(sm: SemanticMemory, fid: str) -> str:
    with sqlite3.connect(str(sm.db_path)) as con:
        return con.execute("SELECT status FROM facts WHERE id = ?", (fid,)).fetchone()[0]


async def _restore_via_mcp(fid: str) -> dict:
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    risposta = await handler(CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name="hippo_quarantine_restore",
                                     arguments={"fact_id": fid})))
    payload = risposta.root if hasattr(risposta, "root") else risposta
    return json.loads([c.text for c in payload.content if hasattr(c, "text")][0])


@pytest.mark.asyncio
async def test_un_fatto_scritto_via_mcp_non_si_libera_via_mcp(sm):
    fid = _in_quarantena(sm, "mcp:unbound")
    out = await _restore_via_mcp(fid)
    assert out["restored"] is False, out
    assert str(out.get("refused_reason", "")).startswith("self_release"), out
    assert (out["released_by"], out["written_by"]) == ("mcp:unbound", "mcp:unbound"), out
    assert _stato(sm, fid) == "quarantined"


@pytest.mark.asyncio
async def test_controllo_positivo_via_mcp_si_libera_cio_che_ha_scritto_un_altro(sm):
    fid = _in_quarantena(sm, "sdk:local")
    out = await _restore_via_mcp(fid)
    assert out["restored"] is True, out
    assert (out["released_by"], out["written_by"]) == ("mcp:unbound", "sdk:local"), out
    assert _stato(sm, fid) == "model_claim"


def _release_dalla_cli(sm: SemanticMemory, fid: str):
    from verimem.cli import app
    return CliRunner().invoke(app, ["facts", "release", fid, "--db", str(sm.db_path),
                                    "--reason", "reviewed by a person"])


def test_una_persona_libera_dalla_cli_e_la_ricevuta_dice_chi(sm):
    fid = _in_quarantena(sm, "mcp:unbound")
    r = _release_dalla_cli(sm, fid)
    assert r.exit_code == 0, r.output
    assert "released_by cli:local" in r.output and "written_by mcp:unbound" in r.output, r.output
    assert _stato(sm, fid) == "model_claim"


def test_dalla_cli_chi_ha_scritto_con_la_stessa_etichetta_non_libera(sm, monkeypatch):
    monkeypatch.setenv("VERIMEM_ACTOR", "aldo")
    fid = _in_quarantena(sm, "cli:local/aldo")
    r = _release_dalla_cli(sm, fid)
    assert r.exit_code == 1, r.output
    assert "self_release" in r.output, r.output
    assert _stato(sm, fid) == "quarantined"
