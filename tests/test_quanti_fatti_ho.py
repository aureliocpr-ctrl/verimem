"""«Quanti fatti ho?» — e il conteggio contava anche quelli che non ti restituisce.

`Memory.count` si presenta come **the honest primitive for aggregation
queries**, e la sua docstring dichiara cosa conta:

    * none — the whole live corpus (excludes superseded).
    Live facts only (superseded excluded), **matching `search`'s default view**.

Sul corpus di produzione, il 2026-08-04:

    count()                       5428
    search_facts('')  (il default) 4834
    differenza                      594   -> esattamente i quarantinati vivi

La promessa «matching `search`'s default view» era falsa, e la parola che
mancava è *quarantined*. Un fatto quarantinato è quello che il gate ha
respinto, e il prodotto dichiara nelle proprie istruzioni che lo tiene «**OUT of
default recall, so you never get it back as truth**». Contarlo fra i propri
fatti significa rispondere «ne hai 5428» e restituirne 4834: il 12% del numero
è materiale che non uscirà mai.

DUE RAMI SU QUATTRO, ed è la mia stessa cura lasciata a metà. Il 2026-08-02
avevo spostato il ramo `query` e il ramo `topic_prefix` da `list_facts` a
`search_facts` proprio per allineare le popolazioni; i rami `topic` e `none`
sono rimasti indietro. La classe «la cura c'era e mancava lo sweep», su un
codice che avevo toccato io.

LA CURA È ADDITIVA E PASSA DA SQL. `semantic.count()` filtrava solo
`superseded_by IS NULL`; ora accetta `include_quarantined` (default **True**, il
comportamento storico invariato per ogni altro chiamante) e `Memory.count` lo
chiede a False, così mantiene la promessa della propria docstring. Passare da
`search_facts('')` avrebbe funzionato ma costa 0.45s contro 0.00s su 7000
fatti — e un conteggio che si paga mezzo secondo smette di essere una primitiva.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem import Memory


@pytest.fixture()
def mem() -> Memory:
    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "c.db"))
    # Un fatto qualunque, e uno che il gate quarantina: una metrica asserita
    # senza uno straccio di evidenza è il caso che L1.19 prende sempre.
    m.add("Il servizio gira su tre nodi.", topic="conta/prova")
    r = m.add("La latenza è 40 ms.", topic="conta/prova")
    assert r.get("status") == "quarantined", (
        f"il banco presuppone che questo venga quarantinato, invece: {r}")
    return m


def test_il_conteggio_non_include_cio_che_non_ti_restituisce(mem):
    """Il cuore: un quarantinato non è «un fatto che hai», perché non te lo
    ridà mai. Contarlo gonfia la risposta con materiale invisibile."""
    assert mem.count() == 1, (
        f"count() dice {mem.count()} ma i fatti richiamabili sono 1: sta "
        f"contando anche il quarantinato, che il prodotto tiene fuori dal "
        f"recall di default")


def test_e_combacia_con_search_come_la_docstring_PROMETTE(mem):
    """La docstring dichiara «matching `search`'s default view». Questo test
    esiste perché quella riga smetta di essere un'aspirazione."""
    dal_conteggio = mem.count()
    dalla_ricerca = len(mem.semantic.search_facts("", limit=1_000_000))
    assert dal_conteggio == dalla_ricerca, (
        f"count()={dal_conteggio} e search default={dalla_ricerca}: la "
        f"docstring di `count` promette che coincidano")


def test_anche_il_ramo_per_TOPIC(mem):
    """Quattro rami, e due erano rimasti su `list_facts`. Se si cura solo
    quello senza argomenti, la stessa domanda ristretta a un topic continua a
    dare il numero gonfiato."""
    assert mem.count(topic="conta/prova") == 1, (
        f"count(topic=) dice {mem.count(topic='conta/prova')} invece di 1")


def test_e_il_ramo_per_PREFISSO_che_era_gia_giusto(mem):
    """Il ramo curato il 2026-08-02: qui si presidia che resti giusto."""
    assert mem.count(topic_prefix="conta") == 1


def test_la_primitiva_di_BASSO_livello_non_cambia_per_nessuno(mem):
    """La cura è additiva. `semantic.count()` senza argomenti deve continuare a
    contare quello che contava — ci sono altri chiamanti, e cambiargli il
    significato sotto i piedi sarebbe la stessa classe di difetto che questo
    file cura."""
    assert mem.semantic.count() == 2, (
        "il conteggio di basso livello ha cambiato significato: era «tutte le "
        "righe non superseded» e altri chiamanti ci contano")
    assert mem.semantic.count(include_quarantined=False) == 1


def test_un_quarantinato_RIABILITATO_torna_nel_conteggio(mem):
    """Il verso opposto, perché la cura non diventi un filtro cieco: se un
    fatto esce dalla quarantena deve tornare a contare. Altrimenti si è
    scambiato «non contarlo» per «cancellarlo»."""
    quarantinati = [f for f in mem.semantic.all()
                    if getattr(f, "status", "") == "quarantined"]
    assert quarantinati, "il banco non ha prodotto nessun quarantinato"
    fid = quarantinati[0].id
    with mem.semantic._connect() as conn:
        conn.execute("UPDATE facts SET status='model_claim' WHERE id=?", (fid,))
    assert mem.count() == 2, (
        "un fatto riabilitato non è tornato nel conteggio: il filtro guarda "
        "qualcosa di diverso dallo stato corrente")
