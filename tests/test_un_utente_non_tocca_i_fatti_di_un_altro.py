"""Un utente non TOCCA i fatti di un altro: cancellare, aggiornare, etichettare,
ripristinare, raccontarne la storia, dimenticare col referto, disfare.

ATLAS, pezzo 2 (29/09). Il pezzo 1 ha legato all'ambito le LETTURE e ha chiuso
tutto il resto: su un handle legato i metodi che lavorano per id rifiutavano.
Qui si aprono uno per uno, ciascuno con la sua prova. Un id di un altro utente
vale come un id che non esiste: nessun effetto, e la STESSA risposta, perche'
una risposta diversa direbbe a chi chiede che quel fatto c'e'.

⚖️ Ogni cella ha il suo controllo: l'handle di Alice, sui fatti di Alice,
funziona. Un metodo che rifiutasse tutto passerebbe le celle su Bob e cadrebbe
sul controllo — ed era lo stato del pezzo 1.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory
from verimem.scope import scoped_topic
from verimem.semantic import Fact, SemanticMemory

BOB = "Bob rinnova il piano mensile ogni primo del mese."


@pytest.fixture()
def due_utenti(tmp_path):
    db = tmp_path / "negozio" / "semantic.db"
    sm = SemanticMemory(db_path=db)
    ids: dict[str, str] = {}
    for chi, testo, utente, stato in (
            ("alice", "Alice rinnova il piano annuale ogni gennaio.", "alice",
             "model_claim"),
            ("bob", BOB, "bob", "model_claim"),
            ("alice_q", "Alice ha chiesto un rimborso per il mese di luglio.",
             "alice", "quarantined"),
            ("bob_q", "Bob ha chiesto un rimborso per il mese di agosto.",
             "bob", "quarantined")):
        fatto = Fact(proposition=testo, status=stato,
                     topic=scoped_topic("abbonamenti", user_id=utente))
        sm.store(fatto, embed="sync")
        ids[chi] = fatto.id
    return db, ids


def _riga(db, fact_id: str):
    """La riga come la vede lo store NON legato: il testimone esterno."""
    return SemanticMemory(db_path=db).get(fact_id)


def test_cancellare(due_utenti):
    db, ids = due_utenti
    alice = Memory(path=str(db), user_id="alice")
    assert alice.delete(ids["bob"]) is False
    assert _riga(db, ids["bob"]) is not None, (
        "l'handle di Alice ha cancellato il fatto di Bob")
    assert alice.delete(ids["alice"]) is True, (
        "CONTROLLO: l'handle di Alice non cancella nemmeno il suo fatto")
    assert _riga(db, ids["alice"]) is None


def test_la_purga_non_attraversa_l_ambito(due_utenti):
    db, ids = due_utenti
    alice = Memory(path=str(db), user_id="alice")
    assert alice.delete(ids["bob"], purge_history=True) is False
    assert _riga(db, ids["bob"]) is not None, (
        "la purga dell'handle di Alice ha cancellato il fatto di Bob")


def test_aggiornare(due_utenti):
    db, ids = due_utenti
    alice = Memory(path=str(db), user_id="alice")
    r = alice.update(ids["bob"], "Bob rinnova il piano mensile ogni quindici.")
    assert r == {"updated": False, "reason": "not found"}, r
    bob = _riga(db, ids["bob"])
    assert bob.proposition == BOB and not bob.superseded_by, (
        "l'handle di Alice ha sostituito il fatto di Bob")
    ok = alice.update(ids["alice"], "Alice rinnova il piano annuale ogni febbraio.")
    assert ok.get("updated") is True, f"CONTROLLO: {ok}"
    assert _riga(db, ok["id"]).topic.startswith("user:alice/")


def test_etichettare(due_utenti):
    db, ids = due_utenti
    alice = Memory(path=str(db), user_id="alice")
    assert alice.label(ids["bob"], "proven", proof="contratto del 3/09") is False
    assert not _riga(db, ids["bob"]).epistemic, (
        "l'handle di Alice ha etichettato il fatto di Bob")
    assert alice.label(ids["alice"], "proven", proof="contratto del 2/09") is True, (
        "CONTROLLO: l'handle di Alice non etichetta nemmeno il suo fatto")


def test_ripristinare(due_utenti):
    db, ids = due_utenti
    alice = Memory(path=str(db), user_id="alice")
    assert alice.restore(ids["bob_q"]) is False
    assert _riga(db, ids["bob_q"]).status == "quarantined", (
        "l'handle di Alice ha tolto dalla quarantena il fatto di Bob")
    assert alice.restore(ids["alice_q"]) is True, (
        "CONTROLLO: l'handle di Alice non ripristina nemmeno il suo fatto")


def test_la_storia(due_utenti):
    db, ids = due_utenti
    alice = Memory(path=str(db), user_id="alice")
    assert alice.history(ids["bob"]) == [], (
        "l'handle di Alice racconta la storia del fatto di Bob")
    assert alice.history(ids["alice"]), (
        "CONTROLLO: la storia del fatto di Alice e' vuota")


def test_dimenticare_col_referto(due_utenti):
    """Il referto dice dove un fatto resta leggibile (le copie dei sogni): per
    l'id di Bob non deve dirlo ad Alice, e non deve cancellare niente."""
    db, ids = due_utenti
    alice = Memory(path=str(db), user_id="alice")
    r = alice.forget_with_report(ids["bob"])
    assert r == {"removed": False, "fact_id": ids["bob"], "residual_copies": []}, r
    assert _riga(db, ids["bob"]) is not None, (
        "l'handle di Alice ha dimenticato il fatto di Bob")
    assert alice.forget_with_report(ids["alice"])["removed"] is True, (
        "CONTROLLO: l'handle di Alice non dimentica nemmeno il suo fatto")


def test_disfare_un_operazione_di_bob(due_utenti):
    """Un'operazione disfacibile nasce da un ritiro: Bob aggiorna il suo fatto,
    il vecchio si ritira, e disfarlo e' affare di Bob."""
    db, ids = due_utenti
    bob = Memory(path=str(db), user_id="bob")
    nuovo = bob.update(ids["bob"], "Bob rinnova il piano mensile ogni quindici.")
    assert nuovo.get("updated") is True, nuovo
    op = next(o for o in SemanticMemory(db_path=db).list_undoable_ops()
              if o["fact_id"] == ids["bob"])
    alice = Memory(path=str(db), user_id="alice")
    r = alice.undo(op["op_id"])
    assert r == {"ok": False, "op_id": op["op_id"], "action": "not_found"}, r
    assert _riga(db, ids["bob"]).superseded_by, (
        "l'handle di Alice ha disfatto il ritiro di Bob")
    assert bob.undo(op["op_id"])["ok"] is True, (
        "CONTROLLO: l'handle di Bob non disfa la sua operazione")
    assert not _riga(db, ids["bob"]).superseded_by
