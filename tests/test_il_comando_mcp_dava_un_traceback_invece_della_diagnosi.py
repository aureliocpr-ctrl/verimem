"""`verimem mcp` si rompeva con un traceback mentre la diagnosi era gia' scritta.

IL CASO E' REALE E ATTUALE, misurato da un'altra istanza end-to-end alle 00:47
del 2026-09-02: chi scrive `pip install verimem` oggi riceve `mcp 2.1.1`, e::

    verimem mcp   (0.7.0 pubblicata + mcp 2.1.1)   AttributeError … EXIT=1
    verimem mcp   (wheel 0.7.1 + mcp 1.29.1)       parte

    AttributeError: 'Server' object has no attribute 'list_tools'

La causa e' nota e il rimedio pure: `mcp` 2.x ha rimosso l'API di basso livello
su cui il server e' costruito, e `pip install "mcp<2"` lo rimette in piedi.
`verimem doctor` lo dice gia' — FAIL, con il rimedio — e lo dice per averlo
ESEGUITO ai due lati del confine (`1.29.1` funziona, `2.0.0` no).

🔑 IL DIFETTO NON E' LA DIAGNOSI MANCANTE: E' CHE NON ARRIVA A CHI SERVE. Chi
lancia `verimem mcp` su un'installazione rotta non passa dal doctor — vede un
traceback su una libreria di cui non sa nulla. La diagnosi esiste in un posto
dove quell'utente non guarda. E' la forma «il prodotto lo diceva gia' e non lo
eseguivamo», applicata a due comandi dello stesso pacchetto.

⚖️ PERCHE' LA DIAGNOSI NON E' INCONDIZIONATA. Un `except` che dicesse «e' colpa
di mcp 2.x» davanti a QUALUNQUE errore di import sarebbe una diagnosi
fabbricata: mascherebbe un bug diverso con una spiegazione plausibile e
sbagliata — esattamente il difetto che questo prodotto esiste per non fare. La
frase esce **solo se la versione installata e' davvero >= 2**; altrimenti
l'errore viene rilanciato intatto.

⚠️ COSA QUESTO BANCO NON PROVA: non esegue `mcp 2.x` vero (non e' installato
qui). Simula il fallimento dell'import e verifica **cosa il comando DICE** nei
due regimi di versione. Che sia proprio la 2.x a rompere l'import e' misurato
altrove — dal banco del doctor e dall'A/B end-to-end citato sopra.
"""

from __future__ import annotations

import sys
import types

import pytest
from typer.testing import CliRunner

import verimem.cli as cli
import verimem.doctor as doc

runner = CliRunner()


@pytest.fixture()
def import_rotto(monkeypatch):
    """`from .mcp_server import main` fallisce, come su un'installazione con
    la 2.x — dove il modulo esplode mentre viene eseguito."""
    finto = types.ModuleType("verimem.mcp_server")   # senza `main`
    monkeypatch.setitem(sys.modules, "verimem.mcp_server", finto)
    return finto


def _versione(monkeypatch, v):
    monkeypatch.setattr(doc, "_versione_di_mcp", lambda: v)


def test_la_premessa_la_diagnosi_ESISTE_gia_nel_doctor():
    """Controllo positivo del banco: se queste costanti sparissero, il resto
    del file misurerebbe una frase inventata qui."""
    assert "will not start" in doc.AVVISO_MCP_2X
    assert "mcp<2" in doc.RIMEDIO_MCP_2X


def test_con_mcp_2x_il_comando_DICE_la_causa_invece_del_traceback(
        import_rotto, monkeypatch):
    """IL CUORE. L'utente ha lanciato il comando che la documentazione chiama
    «the HEADLINE use», e riceveva un errore su un attributo di una classe di
    un'altra libreria."""
    _versione(monkeypatch, "2.1.1")

    res = runner.invoke(cli.app, ["mcp"])

    assert res.exit_code != 0, "un server che non parte non esce con successo"
    testo = res.output
    assert "2.1.1" in testo, (
        f"la versione che rompe non e' nominata: chi legge non sa cosa "
        f"disinstallare\n{testo}")
    assert 'mcp<2' in testo, (
        f"il rimedio non c'e': la diagnosi senza la cura e' meta' referto\n"
        f"{testo}")
    assert "Traceback" not in testo, (
        f"c'e' ancora il traceback al posto della spiegazione\n{testo}")


def test_la_frase_e_LA_STESSA_del_doctor(import_rotto, monkeypatch):
    """⚠️ UNA FRASE SOLA, O LE COPIE DIVERGONO. Se un giorno il confine di
    versione cambia, deve cambiare in un posto: qui si verifica che il comando
    non abbia una sua versione della storia."""
    _versione(monkeypatch, "2.4.0")
    res = runner.invoke(cli.app, ["mcp"])
    attesa = doc.AVVISO_MCP_2X.format(v="2.4.0")
    # il confronto e' sul contenuto, non sull'a capo: `rich` manda a capo.
    nucleo = attesa.split("—")[1].strip().split(",")[0]
    assert nucleo.split()[0] in res.output, (attesa, res.output)


def test_CONTROLLO_con_mcp_1x_l_errore_NON_viene_mascherato(
        import_rotto, monkeypatch):
    """⚖️ LA POPOLAZIONE OPPOSTA, ed e' quella che rende onesta la cura: se
    l'import fallisce per un motivo diverso, dare la colpa a `mcp 2.x` sarebbe
    una spiegazione fabbricata. Con una versione sotto il confine l'errore deve
    restare quello vero."""
    _versione(monkeypatch, "1.29.1")

    res = runner.invoke(cli.app, ["mcp"])

    assert res.exit_code != 0
    assert "mcp<2" not in res.output, (
        "il comando incolpa la 2.x mentre la versione installata e' 1.29.1: "
        f"e' una diagnosi inventata\n{res.output}")


def test_CONTROLLO_senza_mcp_installato_nessuna_diagnosi_inventata(
        import_rotto, monkeypatch):
    """Se `mcp` non e' installato affatto, non si puo' dire che sia la 2.x."""
    _versione(monkeypatch, None)
    res = runner.invoke(cli.app, ["mcp"])
    assert res.exit_code != 0
    assert "mcp<2" not in res.output, res.output
