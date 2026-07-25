"""AMPIEZZA — i casi d'uso ovvi di chi usa una memoria, tutti in un posto.

Perche' questo file esiste. Il 25/07 il gate ritirava fatti veri su "issue 42" /
"issue 43": un caso d'uso banale, in produzione da mesi, che nessuno aveva
testato. Misurato: 9 fatti enumerati scritti, 2 vivi. La suite aveva 8000 test e
copriva in profondita' i casi PENSATI — moat, audit firmato, astensione — e
quasi nulla di quelli che un utente fa il primo giorno.

Questa e' la differenza fra profondita' e ampiezza, e questo file copre la
seconda: una batteria di scritture ordinarie dove la risposta giusta e' ovvia
prima di eseguire. Ogni caso dichiara se i fatti devono COESISTERE (soggetti
distinti, enumerazioni, diario) o se il secondo deve RITIRARE il primo (lo stesso
valore che cambia). Nessuna finezza: se uno di questi si rompe, il prodotto e'
rotto per chi lo usa, indipendentemente dagli altri 8000 test.

Nota di costo: ogni add passa dal gate completo, quindi il file e' lento per
costruzione. E' il prezzo di misurare la cosa vera invece di un fake.
"""
from __future__ import annotations

import sqlite3

import pytest

from engram import Memory

# (etichetta, fatti da scrivere, quanti devono restare VIVI)
COESISTONO = [
    ("issue numerate",
     [f"issue {n} nel tracker e' aperta" for n in (41, 42, 43, 44)], 4),
    ("log enumerati",
     [f"The email module sends message {i}." for i in range(3)], 3),
    ("porte di servizi diversi",
     ["il servizio verimem ascolta sulla porta 8080",
      "il servizio cortex ascolta sulla porta 9090",
      "il servizio gateway ascolta sulla porta 7070"], 3),
    ("diario per giorni",
     [f"day {d}: ho lavorato sul retrieval" for d in (1, 2, 3, 4)], 4),
    ("righe di un file",
     ["la riga 12 di client.py va cambiata",
      "la riga 340 di client.py va cambiata"], 2),
    pytest.param(
        "misure di soggetti diversi",
        ["il recall di verimem risponde in 45 ms",
         "il recall di cortex risponde in 120 ms"], 2,
        id="misure di soggetti diversi",
        marks=pytest.mark.xfail(strict=True, reason=(
            "APERTO 2026-07-25: due soggetti nominati con nomi MINUSCOLI "
            "(verimem, cortex) e la stessa unita'. _named_subjects_disjoint "
            "esiste ma richiede le maiuscole. Un criterio strutturale sui token "
            "esclusivi e' stato provato e falsificato (non distingue un nome da "
            "un sinonimo ne' da un valore cambiato: cache holds/bounded, Alice "
            "Rome/Paris). strict=True: il giorno che si risolve questo test "
            "FALLISCE e va togliere il marker — non resta un difetto silenzioso.")),
    ),
    ("codici identificativi",
     ["la sequenza A000045 e' Fibonacci",
      "la sequenza A000032 e' Lucas"], 2),
    ("attributi diversi dello stesso soggetto",
     ["il gate legge in 45 ms", "il gate scrive in 300 ms"], 2),
]

#: Il secondo write aggiorna lo STESSO valore: il primo deve uscire dal recall,
#: altrimenti il recall serve un dato stale — il difetto opposto, e altrettanto
#: grave, di quello curato il 25/07.
RITIRANO = [
    ("conteggio che cresce",
     ["la full suite di verimem conta 7883 test passati",
      "la full suite di verimem conta 8053 test passati"]),
    ("versione che avanza",
     ["verimem e' alla versione 0.7.0 su PyPI",
      "verimem e' alla versione 0.8.0 su PyPI"]),
    ("latenza che peggiora",
     ["il recall di verimem risponde in 45 ms",
      "il recall di verimem risponde in 2850 ms"]),
]


def _vivi(db) -> int:
    con = sqlite3.connect(str(db))
    try:
        return con.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL "
            "AND status NOT IN ('quarantined','orphaned')").fetchone()[0]
    finally:
        con.close()


@pytest.mark.parametrize(("label", "facts", "attesi"), COESISTONO)
def test_distinct_everyday_facts_all_survive(tmp_path, label, facts, attesi):
    """Fatti distinti che un utente scrive nello stesso pomeriggio: devono
    esserci ancora tutti. Il conteggio e' sul DB, non sul recall, perche' un
    fatto ritirato sparisce dal recall ma resta nella riga: la domanda e'
    quanti sono VIVI."""
    db = tmp_path / "m.db"
    mem = Memory(path=str(db))
    for f in facts:
        mem.add(f, topic="everyday")
    vivi = _vivi(db)
    assert vivi == attesi, (
        f"[{label}] scritti {len(facts)}, vivi {vivi}, attesi {attesi} — "
        f"il gate ha ritirato fatti distinti")


@pytest.mark.parametrize(("label", "facts"), RITIRANO)
def test_an_updated_value_retires_the_old_one(tmp_path, label, facts):
    """Controllo nullo dell'intero file: la feature che ritira i valori superati
    deve restare viva. Senza questi casi, ogni guardia aggiunta per proteggere i
    fatti distinti potrebbe spegnere il supersede senza che nessuno se ne
    accorga — e il recall inizierebbe a servire dati stale."""
    db = tmp_path / "m.db"
    mem = Memory(path=str(db))
    for f in facts:
        mem.add(f, topic="everyday")
    vivi = _vivi(db)
    assert vivi == 1, (
        f"[{label}] scritti {len(facts)}, vivi {vivi}, atteso 1 — "
        f"il valore superato non e' stato ritirato")
