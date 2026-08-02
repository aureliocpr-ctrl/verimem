"""`facts forget` prometteva la cancellazione GDPR e lasciava i predecessori.

Il comando si chiama «Delete one fact (privacy / GDPR / cleanup)» e dice «Use
--no-undoable for true privacy-compliant hard delete». Ma cancella UNA riga, e
un fatto aggiornato ne ha lasciata un'altra dietro di se': `update()` non
sovrascrive, STORE un fatto nuovo e SUPERSEDE il vecchio, che resta nel
database con lo stesso identico contenuto.

Misurato dall'SDK, dove il difetto e' lo stesso:

    scritto  «Il codice fiscale del cliente e RSSMRA80A01H501U.»
    update   -> il vecchio viene superseduto, il nuovo lo rimpiazza
    delete(nuovo)                          -> True
    righe col dato sensibile ANCORA nel DB -> 1
    get(vecchio)                           -> ANCORA LEGGIBILE

Il recall e' protetto — `deep search` non lo riporta — ma per una richiesta di
cancellazione «il dato non e' piu' nel database» e' esattamente cio' che
serve, e li' dentro c'e'.

LA CAPACITA' ESISTEVA E NON ERA RAGGIUNGIBILE. `Memory.delete` ha
`purge_history=True`, documentato come «the GDPR-grade delete», e la parola
`purge_history` non compare in TUTTO `cli.py` ne' in `mcp_server.py`: la
cancellazione completa viveva solo nell'SDK, cioe' nel canale che un utente
non usa per una richiesta di cancellazione.

Due cose, e la seconda conta piu' della prima: il flag `--purge-history`, e
l'AVVISO. Un comando che toglie una riga su due e stampa «forgotten» in verde
ha detto una cosa vera e ne ha taciuta una che cambia la decisione di chi
legge.
"""
from __future__ import annotations

import sqlite3

import pytest
from typer.testing import CliRunner

from verimem import cli as cli_mod
from verimem.client import Memory

SEGRETO = "Il codice fiscale del cliente e RSSMRA80A01H501U."


@pytest.fixture()
def store_con_catena(tmp_path, monkeypatch):
    """Un fatto sensibile, aggiornato una volta: due righe, stesso dato."""
    m = Memory(path=tmp_path / "m.db")
    vecchio = m.add(SEGRETO, topic="pii")["id"]
    nuovo = m.update(vecchio, SEGRETO + " Verificato.")["id"]
    monkeypatch.setattr(cli_mod, "_facts_sm", lambda: m.semantic)
    return m, vecchio, nuovo


def _righe_col_segreto(m: Memory) -> int:
    con = sqlite3.connect(m.semantic.db_path)
    try:
        return con.execute(
            "SELECT COUNT(*) FROM facts WHERE proposition LIKE '%RSSMRA%'"
        ).fetchone()[0]
    finally:
        con.close()


def test_la_cancellazione_normale_DICE_che_ha_lasciato_dei_predecessori(
        store_con_catena):
    """L'avviso: chi legge «forgotten» in verde deve sapere cosa resta."""
    m, _vecchio, nuovo = store_con_catena
    res = CliRunner().invoke(cli_mod.app, ["facts", "forget", nuovo, "--yes"])
    assert res.exit_code == 0, res.output
    assert _righe_col_segreto(m) == 1, "presupposto: il predecessore resta"
    basso = res.output.lower()
    assert "predecessor" in basso or "purge-history" in basso, (
        f"la cancellazione tace su cio' che ha lasciato:\n{res.output}")


def test_con_purge_history_non_resta_niente(store_con_catena):
    m, _vecchio, nuovo = store_con_catena
    res = CliRunner().invoke(
        cli_mod.app, ["facts", "forget", nuovo, "--yes", "--purge-history"])
    assert res.exit_code == 0, res.output
    assert _righe_col_segreto(m) == 0, (
        f"il dato sensibile e' ancora nel database:\n{res.output}")


def test_un_fatto_SENZA_catena_non_riceve_avvisi(tmp_path, monkeypatch):
    """Il caso normale non deve diventare rumoroso: un fatto che non ha
    predecessori si cancella e basta."""
    m = Memory(path=tmp_path / "m.db")
    solo = m.add("Il piano annuale costa 100 euro.", topic="prezzi")["id"]
    monkeypatch.setattr(cli_mod, "_facts_sm", lambda: m.semantic)
    res = CliRunner().invoke(cli_mod.app, ["facts", "forget", solo, "--yes"])
    assert res.exit_code == 0, res.output
    assert "predecessor" not in res.output.lower(), res.output
