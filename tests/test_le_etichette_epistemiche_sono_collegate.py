"""Le etichette epistemiche si possono scrivere, leggere e contare.

Sostituisce test_le_etichette_epistemiche_non_hanno_superficie.py, che
registrava lo stato precedente: il sottosistema era completo e scollegato in
ENTRAMBE le direzioni — `set_epistemic` esisteva su SemanticMemory ed era
chiamato solo da due moduli che nessuna superficie raggiunge, e `epistemic` era
NULL su tutti e 6457 i fatti del corpus vivo mentre il README lo prometteva in
18 punti.

Mandato di Aurelio, 2026-07-31: «collega tutto». Collegato in tre punti, perche'
una capacita' su un canale solo e' il difetto che questa serie di commit ha
passato due giorni a chiudere:

    scrittura   Memory.label (SDK) · hippo_fact_label (MCP) · facts label (CLI)
    lettura     gia' fatta: il contratto di uscita porta `epistemic`
    conteggio   `verimem status`, cosi' un sottosistema fermo a zero SI VEDE

L'ultimo punto e' la lezione dei due giorni: cio' che non si conta resta spento
in silenzio. L'attrito dell'API non si tocca — `proven` senza una prova
nominata resta un errore, altrimenti diventa l'auto-dichiarazione che questo
prodotto esiste per impedire.
"""
from __future__ import annotations

import asyncio
import json
import re

import pytest
from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
FRASE = "L'algoritmo di ordinamento termina su ogni input finito."


@pytest.fixture
def mem(tmp_path, monkeypatch):
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    from verimem.client import Memory
    m = Memory(path=tmp_path / "semantic" / "semantic.db")
    r = m.add(FRASE, topic="prova")
    m._fid = r.get("id")
    return m


# ---------------------------------------------------------------- scrittura
def test_l_sdk_sa_etichettare(mem):
    assert mem.label(mem._fid, "proven", proof="pytest:test_termina_PASS") is True
    f = mem.semantic.get(mem._fid)
    assert (f.epistemic or {}).get("kind") == "proven"
    assert (f.epistemic or {}).get("proof") == "pytest:test_termina_PASS"


def test_una_prova_senza_riferimento_e_rifiutata(mem):
    """L'attrito e' la parte buona del sottosistema: «a proof must be
    machine-checkable, not a vibe». Collegarlo non deve smussarlo."""
    with pytest.raises(ValueError):
        mem.label(mem._fid, "proven", proof="   ")
    with pytest.raises(ValueError):
        mem.label(mem._fid, "unbeaten", bound=0)
    with pytest.raises(ValueError):
        mem.label(mem._fid, "refuted", counterexample="")


def test_una_specie_inventata_e_rifiutata(mem):
    with pytest.raises(ValueError):
        mem.label(mem._fid, "verificato-da-me", proof="x")


def test_refuted_e_assorbente(mem):
    """Le transizioni sono monotone e `refuted` assorbe: un fatto smentito non
    torna dimostrato perche' qualcuno lo richiede."""
    assert mem.label(mem._fid, "refuted", counterexample="input [3,1] cicla")
    assert mem.label(mem._fid, "proven", proof="pytest:x_PASS") is False
    f = mem.semantic.get(mem._fid)
    assert (f.epistemic or {}).get("kind") == "refuted"


# ------------------------------------------------------------------ lettura
def test_l_etichetta_esce_dalle_letture(mem):
    from verimem.fact_contract import fact_payload
    mem.label(mem._fid, "unbeaten", bound=1_000_000)
    p = fact_payload(mem.semantic.get(mem._fid))
    assert p["epistemic"]["kind"] == "unbeaten"
    assert p["epistemic"]["bound"] == 1_000_000


# ------------------------------------------------------------------- canali
def test_anche_il_tool_mcp_sa_etichettare(mem):
    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server

    class _A:
        def __init__(s):
            s.semantic = mem.semantic
    mcp_server._ag = lambda: _A()
    h = mcp_server.server.request_handlers[CallToolRequest]
    res = asyncio.run(h(CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(
            name="hippo_fact_label",
            arguments={"fact_id": mem._fid, "kind": "proven",
                       "proof": "pytest:test_termina_PASS"}))))
    p = res.root if hasattr(res, "root") else res
    d = json.loads(next(c.text for c in p.content if hasattr(c, "text")))
    assert d.get("labelled") is True, d
    assert (mem.semantic.get(mem._fid).epistemic or {}).get("kind") == "proven"


def test_lo_schema_del_tool_e_scopribile():
    """Un parametro che il client non puo' scoprire non esiste."""
    from verimem import mcp_server
    tools = asyncio.run(mcp_server._list_tools_unfiltered())
    t = next((x for x in tools if x.name == "hippo_fact_label"), None)
    assert t is not None, "il tool non e' nell'elenco: nessun client lo vedra'"
    props = (t.inputSchema or {}).get("properties") or {}
    assert {"fact_id", "kind"} <= set(props)


def test_anche_la_cli_sa_etichettare(mem):
    r = runner.invoke(app, ["facts", "label", mem._fid, "--proven",
                            "pytest:test_termina_PASS"])
    assert r.exit_code == 0, _ANSI.sub("", r.output)
    assert (mem.semantic.get(mem._fid).epistemic or {}).get("kind") == "proven"


# ----------------------------------------------------------------- conteggio
def test_lo_stato_conta_le_etichette(mem):
    """Cio' che non si conta resta spento in silenzio: e' la lezione dei due
    giorni, e questo e' il presidio che la applica al sottosistema appena
    collegato."""
    mem.label(mem._fid, "proven", proof="pytest:x_PASS")
    out = _ANSI.sub("", runner.invoke(app, ["status"]).output)
    assert "epistemic" in out.lower() or "etichett" in out.lower(), out
    assert "1" in out
