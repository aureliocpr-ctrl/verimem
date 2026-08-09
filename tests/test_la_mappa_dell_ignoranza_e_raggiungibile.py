"""L'astensione si puo' chiedere PERCHE', da fuori.

Il prodotto si astiene — e' il claim che lo distingue, ripetuto dodici volte nel
README e nelle istruzioni del server MCP («abstention over hallucination»). Ma
un'astensione senza diagnosi lascia il chiamante esattamente dov'era: sa che non
sa, non sa cosa gli manca.

``ignorance_map`` risponde a quella domanda — nomina la CLASSE dell'ignoranza
(``no_evidence`` / ``below_floor`` / ``quarantined_only`` / ``conflict``) e cosa
la curerebbe — ed era completo, con DUE file di test suoi, e irraggiungibile da
ogni superficie: zero import fuori dal modulo, zero menzioni nel README e nei
docs. La capacita' piu' vicina al claim centrale del prodotto, e nessuno poteva
invocarla.

Qui non si prova la QUALITA' della classificazione (la provano
``test_ignorance_map.py`` e ``test_verimem_ignorance_noise.py``, e la suite gira
con un embedder stub — i punteggi non sono semantici). Si prova che un utente
puo' arrivarci: SDK, MCP, CLI. Un modulo giudicato bene da test che nessuna
porta raggiunge e' precisamente il difetto che stiamo chiudendo.
"""
from __future__ import annotations

import json
import re

import pytest
from typer.testing import CliRunner

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

CLASSI = {"no_evidence", "below_floor", "quarantined_only", "conflict",
          "answerable"}


@pytest.fixture()
def memoria(tmp_path, monkeypatch):
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    from verimem.client import Memory
    m = Memory(tmp_path / "ig.db")
    m.add("Il server di produzione sta a Francoforte.", topic="infra",
          verified_by=["runbook:t1"])
    return m


def test_l_sdk_puo_chiedere_cosa_manca(memoria):
    """Il pezzo che mancava: dall'SDK, in una riga."""
    rep = memoria.ignorance(["Qual e' la capitale di Marte?"])
    assert rep["n"] == 1
    riga = rep["queries"][0]
    assert riga["class"] in CLASSI, riga
    assert "by_class" in rep and sum(rep["by_class"].values()) == 1


def test_dice_da_dove_viene_il_pavimento_del_rumore(memoria):
    """0.0 significa tre cose diverse — non misurabile, misurazione fallita,
    imposto dal chiamante — e un 0.0 nudo non le distingueva. La superficie
    deve portare fuori anche questo, o l'operatore non sa se la guardia e'
    spenta o misurata."""
    rep = memoria.ignorance(["Qual e' la capitale di Marte?"])
    assert rep["noise_floor_source"] in {"caller", "measured", "unmeasurable",
                                         "failed"}
    imposto = memoria.ignorance(["x?"], noise_floor=0.3)
    assert imposto["noise_floor_source"] == "caller"
    assert imposto["noise_floor"] == 0.3


def test_ogni_riga_dice_cosa_servirebbe(memoria):
    """Una diagnosi senza prescrizione e' un'astensione piu' lunga."""
    riga = memoria.ignorance(["Qual e' la capitale di Marte?"])["queries"][0]
    if riga["class"] != "answerable":
        assert riga.get("what_would_help"), riga


@pytest.mark.asyncio
async def test_il_tool_mcp_esiste_e_risponde(memoria, monkeypatch):
    """Un agente che ha appena ricevuto «non lo so» deve poter chiedere «cosa
    ti manca» sullo STESSO canale, senza cambiare superficie."""
    from verimem import mcp_server as s
    strumenti = {t.name for t in await s.list_tools()}
    assert "hippo_ignorance_map" in strumenti

    out = await s.call_tool("hippo_ignorance_map",
                            {"queries": ["Qual e' la capitale di Marte?"]})
    dati = json.loads(out[0].text)
    assert dati.get("n") == 1, dati
    assert dati["queries"][0]["class"] in CLASSI, dati


def test_la_cli_la_mostra(memoria):
    from verimem.cli import app
    r = runner.invoke(app, ["ignorance", "Qual e' la capitale di Marte?"])
    testo = _ANSI.sub("", r.output)
    assert r.exit_code == 0, testo
    assert any(c in testo for c in CLASSI), testo


def test_la_cli_in_json_e_una_riga_sola(memoria):
    """Perche' sia componibile in uno script, non solo leggibile a schermo."""
    from verimem.cli import app
    r = runner.invoke(app, ["ignorance", "x?", "--json"])
    testo = _ANSI.sub("", r.output)
    assert r.exit_code == 0, testo
    dati = json.loads(testo[testo.index("{"):testo.rindex("}") + 1])
    assert dati["n"] == 1 and "by_class" in dati
