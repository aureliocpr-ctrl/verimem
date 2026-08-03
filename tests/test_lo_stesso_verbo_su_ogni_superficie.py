"""La CLI dice `correct` e `forget`, l'SDK diceva `update` e `delete`.

Trovato percorrendo il ciclo di vita di un fatto come lo farebbe chi usa il
prodotto — scrivo, rileggo, correggo, rileggo, dimentico, rileggo::

    add       id=c5a339e3feee status=model_claim grounding=98.39
    search    1 hit  best=0.8913
    correct   AttributeError: 'Memory' object has no attribute 'correct'
    forget    AttributeError: 'Memory' object has no attribute 'forget'

Le capacità ci sono entrambe — `Memory.update` e `Memory.delete` — e il
docstring di `delete` si apre con «**Forget** a fact by id», cioè usa la parola
della CLI per descrivere un metodo che si chiama in un altro modo. Non manca
niente: manca il nome con cui l'utente lo cerca.

Il cricchetto sulle capacità (`4cea1aa8`) non lo vede, e giustamente: confronta
i NOMI, e `update` esiste. Un metodo che c'è ma si chiama diversamente non è
una capacità mancante, è attrito di scoperta — e si misura in modo diverso.

IL PRODOTTO HA GIÀ DECISO COME SI RISOLVE. `client.py:1808`::

    #: ``recall`` is the same operation as ``search`` (HippoAgent naming).
    recall = search

Stesso trattamento, stessa forma: un alias dichiarato, nessuna
reimplementazione, zero possibilità che le due divergano.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem import Memory

#: verbo della CLI -> metodo storico dell'SDK. Se domani la CLI cresce di un
#: verbo che agisce su un fatto, questa mappa è il posto dove dichiararlo.
VERBI = {"correct": "update", "forget": "delete", "recall": "search"}


@pytest.mark.parametrize("cli,sdk", sorted(VERBI.items()))
def test_il_verbo_della_cli_esiste_anche_sull_sdk(cli, sdk):
    assert hasattr(Memory, cli), (
        f"la riga di comando ha `{cli}` e l'SDK no: chi passa dall'una "
        f"all'altra non trova il metodo con il nome che sta cercando "
        f"(esiste come `{sdk}`)")


@pytest.mark.parametrize("cli,sdk", sorted(VERBI.items()))
def test_e_non_e_una_seconda_implementazione(cli, sdk):
    """Un alias, non una copia: due implementazioni della stessa operazione
    divergono, ed è la classe che questo repo passa le giornate a curare."""
    assert getattr(Memory, cli) is getattr(Memory, sdk), (
        f"`{cli}` non è lo stesso oggetto di `{sdk}`: se sono due funzioni "
        f"diverse, prima o poi diranno due cose diverse")


def test_il_ciclo_di_vita_funziona_con_i_nomi_della_cli():
    """La prova che conta: il percorso che ha trovato il difetto, rifatto con
    i nomi che l'utente si aspetta."""
    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))
    r = m.add("Il piano annuale costa 100 euro.", topic="listino",
              source="Listino 2026: il piano annuale costa 100 euro.")
    fid = r["id"]

    assert m.recall("quanto costa il piano annuale", k=3)

    m.correct(fid, "Il piano annuale costa 120 euro.")
    assert any("120" in h["text"] for h in m.search("piano annuale", k=5))

    vivi = [h for h in m.search("piano annuale", k=5)
            if not h.get("superseded_by")]
    assert vivi
    assert m.forget(vivi[0]["id"]) is True
