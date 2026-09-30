"""T154 — `correct` deve accettare l'id che il prodotto STAMPA.

IL DIFETTO, incontrato usando il prodotto e non leggendolo: `facts list`
stampa un id di **otto** caratteri, e `correct` ne vuole dodici. Chi copia
quello che vede si sente rispondere «fatto non trovato» — che e' falso: il
fatto c'e', ed e' l'id a essere troncato dalla tabella che l'ha appena mostrato.

    $ verimem facts list --topic prova/id
    │ 1cf4b3bd │ prova/id │ model_claim │ ...
    $ verimem facts get 1cf4b3bd          -> Fact 1cf4b3bd3918   FUNZIONA
    $ verimem correct 1cf4b3bd "..."      -> fatto non trovato   EXIT=2

⚠️ LA CURA ESISTE GIA' NEL PRODOTTO: `_fact_id_resolve` (cli.py) risolve il
prefisso e gestisce l'ambiguita' (`LIMIT 2` + `len(rows) == 1`), e il suo
commento dice perche' esiste: «8-char ids are common in output». Due comandi la
chiamano, `correct_cmd` no. Non si scrive una cura nuova: si chiama quella.

⚠️ E LA TERZA CELLA E' QUELLA CHE CONTA QUANTO LA PRIMA: una cura che accetta
un prefisso non deve diventare una cura che accetta QUALUNQUE cosa. Con due
fatti nello store un prefisso ambiguo deve continuare a fallire — altrimenti
`correct` correggerebbe un fatto a caso, che e' molto peggio del difetto.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from verimem.cli import app

TOPIC = "prova/t154"
#: Quanti caratteri ne mostra la tabella di `facts list`.
CARATTERI_MOSTRATI = 8


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Uno store usa-e-getta, col giornale che lo segue.

    Quattro variabili, non tre: qui si e' IN-PROCESS, quindi lo store si sposta
    e il giornale no se non glielo si dice.
    """
    deposito = tmp_path / "store"
    for nome in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(deposito))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(deposito / "eventi.jsonl"))
    return deposito


def _fuori_dallo_store_vero(ricevuta: dict) -> bool:
    """La domanda giusta non e' «ha scritto dove ho detto io».

    Un controllo che pretende il posto ESATTO fallisce anche quando tutto va
    bene: il `conftest` di questo repo sposta la cartella dei dati prima che le
    variabili di questo banco contino, e la scrittura finisce in una cartella
    di prova che non e' quella che ho dichiarato. Il danno vero e' uno solo —
    scrivere nello store VERO — ed e' quello che si misura.
    """
    vero = str(Path.home() / ".engram")
    return vero.lower() not in str(ricevuta.get("store") or "").lower()


def _scrivi(testo: str, deposito: Path) -> str:
    """Scrive un fatto e rende il suo id INTERO, letto dallo store."""
    from verimem import Memory

    m = Memory()
    r = m.add(testo, topic=TOPIC)
    assert _fuori_dallo_store_vero(r), (
        f"scritto nello store VERO: {r.get('store')!r}")
    return str(r["id"])


def test_correct_accetta_l_id_di_otto_caratteri_che_la_tabella_stampa(store):
    """Il caso dell'utente: copia quello che vede, e deve funzionare."""
    intero = _scrivi("Il totale della fattura e' 500 euro.", store)
    mostrato = intero[:CARATTERI_MOSTRATI]
    assert mostrato != intero, "l'id non e' piu' troncato: la cella non misura piu' niente"

    esito = CliRunner().invoke(
        app, ["correct", mostrato, "Il totale della fattura e' 900 euro."])

    assert esito.exit_code == 0, (
        f"l'id che il prodotto stampa non e' stato accettato: {esito.output}")
    assert "superseded" in esito.output, esito.output


def test_un_id_che_non_esiste_resta_un_errore(store):
    """Il negativo: la cura non deve trasformare un id sbagliato in un successo."""
    _scrivi("Il totale della fattura e' 500 euro.", store)

    esito = CliRunner().invoke(app, ["correct", "ffffffff", "Un altro testo."])

    assert esito.exit_code != 0
    assert "non trovato" in esito.output


def test_un_prefisso_ambiguo_non_corregge_un_fatto_a_caso(store):
    """Due fatti, un prefisso che li prende entrambi: deve FERMARSI.

    Il prefisso vuoto li prende tutti, e' deterministico e non dipende da quali
    id casuali siano usciti. Se questa cella diventasse verde per la ragione
    sbagliata — cioe' se `correct` scegliesse uno dei due — il difetto curato
    sarebbe peggiore di quello di partenza.
    """
    _scrivi("Il totale della fattura e' 500 euro.", store)
    _scrivi("Il totale del bonifico e' 900 euro.", store)

    esito = CliRunner().invoke(app, ["correct", "", "Un testo qualunque."])

    assert esito.exit_code != 0, (
        "un prefisso ambiguo ha corretto qualcosa: " + esito.output)
    assert "superseded" not in esito.output
