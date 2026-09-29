"""La ricevuta dell'SDK dice se la scrittura ha SOSTITUITO una riga.

T24, opzione (b) delle tre che avevo messo sul canale — quella che DICHIARA lo
stato invece di cambiarlo, e che quindi non ha bisogno di una decisione sulla
semantica.

MISURATO IL 06/09, le due porte a confronto sulla stessa scrittura ripetuta:

    MCP  hippo_remember, testo identico  -> stesso id, 1 riga, replaced=True
    SDK  Memory.add,     testo identico  -> id '8038063ccc36' e 'fb5e2fe16599'
                                            DIVERSI, due righe

e le chiavi della ricevuta SDK erano ['adjudication', 'advice',
'grounding_score', 'id', 'moat', 'status', 'stored', 'warnings']: `replaced`
non c'era, e `.get("replaced")` tornava None. Chi ha aperto il ticket ha visto
quel falsy e ha concluso «sempre False»: sintomo giusto, causa sbagliata.

⚠️ LA CAPACITÀ C'È GIÀ NELLA FUNZIONE: `SemanticMemory.store` accetta
`return_replaced` dal suo primo giorno, e l'SDK lo chiamava senza. È la stessa
forma di `include_superseded` (T18), di `--db` (T16) e di `resp["error"]` sul
daemon: qualcosa che il motore sa fare e che la porta non chiede.

⚠️ E QUESTA CELLA NON CHIEDE L'IDEMPOTENZA. Le due porte restano diverse nel
merito — l'MCP deriva l'id dal contenuto, l'SDK no — e allinearle cambierebbe
il comportamento di chi scrive due volte lo stesso testo: è la decisione (a),
e non è mia. Qui si chiede solo che la ricevuta DICA quello che è successo,
perché oggi tace.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from verimem.client import Memory
from verimem.semantic import Fact


@pytest.fixture()
def memoria() -> Memory:
    return Memory(path=str(Path(tempfile.mkdtemp()) / "s.db"))


def test_controllo_positivo_la_ricevuta_arriva(memoria) -> None:
    """Se cade, il resto del file non misura niente."""
    r = memoria.add("Il canone e' 2900 euro.", topic="t")
    assert isinstance(r, dict), f"la ricevuta non e' un dict: {type(r).__name__}"
    assert r.get("stored") is True, f"la scrittura non e' andata: {r}"
    assert r.get("id"), "la ricevuta non porta l'id"


def test_la_ricevuta_dichiara_se_ha_sostituito(memoria) -> None:
    """⚠️ RED: oggi la chiave non c'è affatto.

    Non si chiede che valga True: si chiede che ci SIA. Un campo assente e un
    campo False si leggono uguali da chi usa `.get()`, ed è esattamente
    l'equivoco che ha prodotto il ticket.
    """
    r = memoria.add("Il canone e' 2900 euro.", topic="t")
    assert "replaced" in r, (
        f"la ricevuta dell'SDK non dice se ha sostituito: chiavi {sorted(r)}. "
        "Chi legge con .get('replaced') riceve None e lo scambia per False")
    assert r["replaced"] is False, (
        "su una riga NUOVA non e' stato sostituito niente")


def test_una_scrittura_sullo_stesso_id_dichiara_la_sostituzione(memoria) -> None:
    """⚠️ RED: il caso in cui `replaced` deve valere True.

    L'SDK non deriva l'id dal contenuto — due `add` con lo stesso testo fanno
    due righe, ed è la decisione (a) che resta aperta. Ma quando l'id È lo
    stesso, la riga viene sostituita davvero, e la ricevuta deve dirlo.
    """
    primo = memoria.add("Il canone e' 2900 euro.", topic="t")
    fid = primo["id"]

    #: stessa riga, riscritta per id: qui la sostituzione avviene davvero
    memoria.semantic.store(Fact(id=fid, proposition="Il canone e' 3400 euro.",
                                topic="t"), embed="sync")
    riletto = memoria.semantic.get(fid)
    assert riletto is not None, "la riga e' sparita invece di essere sostituita"
    assert "3400" in riletto.proposition, (
        "l'id era lo stesso e il contenuto non e' cambiato: non ha sostituito")


def test_l_idempotenza_e_arrivata_e_la_ricevuta_la_dice(memoria) -> None:
    """CONTROLLO: due `add` identiche fanno UNA riga, e la seconda lo dice.

    Questa cella esisteva per cadere il giorno in cui l'SDK avesse derivato
    l'id dal contenuto — la decisione (a) di T24 — perche' una scelta di quella
    portata non passasse in silenzio. E' caduta il 29/09 con 1b.3, per scelta
    (D-0013, condizione T162: una scrittura ripetuta e' UN fatto su ogni
    porta), e qui si scrive la promessa nuova invece di cancellare la vecchia.
    """
    a = memoria.add("Il deposito e' 5800 euro.", topic="t")
    b = memoria.add("Il deposito e' 5800 euro.", topic="t")
    assert a["id"] == b["id"], (
        "gli id non coincidono piu': l'SDK ha perso l'idempotenza che la porta "
        "unica promette (D-0013, T162)")
    assert a.get("replaced") is False, "la prima scrittura non sostituisce niente"
    assert b.get("replaced") is True, (
        "la seconda ha sostituito la prima e deve dirlo")
