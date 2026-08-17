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


def _comandi_con_json() -> list[str]:
    """I comandi che dichiarano `--json` e si possono invocare senza argomenti.

    ⚠️ Questa funzione esiste perché la prima stesura elencava DUE comandi a mano
    mentre `--json` è dichiarato dodici volte: un terzo comando con lo stesso
    difetto sarebbe nato senza che nessun collaudo se ne accorgesse. Il buco l'ha
    trovato un'altra istanza applicando il criterio giusto — «un presidio che
    apre un percorso COSTANTE non vede la porta nuova, la lascia passare
    restando verde».

    Restano fuori i comandi che richiedono un argomento obbligatorio (`trust
    CLAIM`, `ignorance QUERIES…`): lì un `exit 2` è la risposta corretta a
    un'invocazione incompleta, non un difetto di formato. Sono ESCLUSI PER
    NOME, così l'elenco degli esclusi è visibile quanto quello dei provati.
    """
    import ast
    from pathlib import Path

    RADICE = Path(__file__).resolve().parent.parent
    sorgente = (RADICE / "verimem" / "cli.py").read_text(encoding="utf-8", errors="replace")
    albero = ast.parse(sorgente)
    con_json: list[str] = []
    for nodo in ast.walk(albero):
        if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        firma = ast.unparse(nodo.args)
        if '"--json"' not in firma and "'--json'" not in firma:
            continue
        for dec in nodo.decorator_list:
            testo = ast.unparse(dec)
            if ".command(" not in testo:
                continue
            # il nome esposto: `@app.command("x")` oppure il nome della funzione
            if isinstance(dec, ast.Call) and dec.args and isinstance(dec.args[0], ast.Constant):
                con_json.append(str(dec.args[0].value))
            else:
                con_json.append(nodo.name.replace("_", "-"))
            break
    return sorted(set(con_json))


#: Chiedono un argomento obbligatorio: `exit 2` senza è la risposta giusta.
_VOGLIONO_ARGOMENTI = {"trust", "ignorance", "introspect", "recall", "ask",
                       "correct", "index", "search-docs", "save", "remember",
                       "chain-show", "audit-anchor"}


def test_ogni_comando_con_json_emette_json_su_store_vuoto(store_vuoto):
    """Il criterio CAMMINA su tutti i comandi, invece di elencarne due a mano."""
    provati, rotti = [], {}
    for nome in _comandi_con_json():
        if nome in _VOGLIONO_ARGOMENTI:
            continue
        r = CliRunner().invoke(app, [nome, "--json"])
        if r.exit_code != 0:
            continue          # un errore d'uso non è un difetto di formato
        provati.append(nome)
        try:
            _json_da(r)
        except (json.JSONDecodeError, AssertionError) as e:
            rotti[nome] = str(e)[:120]
    assert provati, (
        "nessun comando con `--json` è stato provato: o il criterio non li trova più, "
        "o l'elenco degli esclusi se li è mangiati tutti — in entrambi i casi questo "
        "collaudo sarebbe vero e vuoto")
    assert not rotti, (
        f"questi comandi hanno `--json` e su uno store vuoto NON emettono JSON: {rotti}. "
        f"Provati: {provati}")


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
