"""Chi chiede `--json` riceve JSON anche quando la risposta è «niente».

`--json` è la superficie che leggono gli script, e la differenza con quella umana
non è di stile: un messaggio a schermo si legge lo stesso, un `json.loads` su del
testo cade.

Due comandi uscivano da un ramo anticipato PRIMA di guardare `--json`, e su uno
store vuoto stampavano una frase:

    verimem tip --json         ->  «(no facts yet)»
    verimem telemetry --json   ->  «no audit log at …»

Il caso è il PRIMO AVVIO — cioè quando un'integrazione viene provata per la prima
volta — e sparisce appena lo store si popola: chi sviluppa non lo incontra mai.

⚠️ Per `telemetry` non basta emettere `{}`: «nessuna chiamata registrata» e «il
registro non esiste» sono due risposte diverse, e il codice lo dichiarava già per
il lettore umano. Il JSON dice quale delle due.
"""
from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from verimem.cli import app


@pytest.fixture()
def store_vuoto(tmp_path, monkeypatch):
    """Uno store che non esiste ancora: nessun fatto, nessun registro di audit."""
    for var in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(var, str(tmp_path))
    return tmp_path


def _json_da(risultato) -> object:
    """Il primo blocco JSON dell'uscita: le righe di log finiscono su stdout."""
    testo = risultato.stdout
    inizi = [i for i in (testo.find("{"), testo.find("["), testo.find("null")) if i >= 0]
    assert inizi, (
        f"`--json` non ha prodotto nulla che assomigli a JSON. Uscita:\n{testo[:400]}")
    return json.loads(testo[min(inizi):].strip())


def test_tip_su_store_vuoto_emette_json(store_vuoto):
    """Nessun fatto è una risposta, e va data nel formato richiesto."""
    r = CliRunner().invoke(app, ["tip", "--json"])
    assert r.exit_code == 0, r.stdout
    assert _json_da(r) is None, (
        "su uno store senza fatti `tip --json` deve emettere `null` — un oggetto che "
        "dice «nessuna punta» — non la frase «(no facts yet)», che fa cadere ogni "
        "script che chiama json.loads")


def test_telemetry_senza_registro_emette_json(store_vuoto):
    """E dice QUALE delle due risposte è: «non c'è registro», non «zero chiamate»."""
    r = CliRunner().invoke(app, ["telemetry", "--json"])
    assert r.exit_code == 0, r.stdout
    d = _json_da(r)
    assert isinstance(d, dict) and d.get("audit_log") is None, (
        f"deve uscire un oggetto che dichiara l'assenza del registro, non {d!r}")
    assert d.get("reason"), (
        "un `{}` direbbe «nessuna chiamata registrata», che è l'ALTRA risposta e "
        "sarebbe falsa: il motivo deve essere esplicito")


def test_il_criterio_riconoscerebbe_il_difetto():
    """Il controllo positivo: il vecchio comportamento deve far fallire il criterio."""
    with pytest.raises((json.JSONDecodeError, AssertionError)):
        class _Finto:
            stdout = "(no facts yet)\n"
        _json_da(_Finto())
