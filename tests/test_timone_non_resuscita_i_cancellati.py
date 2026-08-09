"""Un fatto CANCELLATO non torna in vita per l'undo di un ritiro precedente.

Trovato dal dogfooding delle camere dark (ws6, 2026-08-05, ~00:26) su codice
MIO: il timone (f288bbe2) fa snapshot pre-op di ogni supersessione, e
``undo_op`` ripristina con INSERT OR REPLACE — giusto per annullare un ritiro,
ma se nel frattempo l'utente ha CANCELLATO quel fatto la riga viene ricreata:

    add(A) · add(B) ritira A · forget(A) · undo(handle del ritiro) -> A TORNA
    e il recall lo serve.

La cancellazione è l'intenzione più recente e più forte (caso GDPR: «cancella
il mio dato»); un undo di un'operazione PRECEDENTE non può scavalcarla. Prima
del timone il difetto non poteva esistere: nessun supersede lasciava un
handle. L'ho introdotto io, e il critic 2-0 non l'ha visto — la composizione
forget × undo-supersede non era nel perimetro di nessuno dei due worker.

Contratto pinnato qui:
1. cancellare un fatto invalida gli handle PENDENTI che lo riguardano;
2. tranne quello del forget stesso — `delete_with_undo` resta annullabile,
   altrimenti la cura ucciderebbe la feature che il forget offre;
3. l'handle invalidato non compare più fra gli undoable (niente pulsante che
   promette un'azione impossibile: è la stessa regola per cui il pannello
   dichiara «irreversible» invece di fingere).
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

_ROSSI = "Il cliente Rossi ha un debito di 5000 euro."
_BIANCHI = "Il cliente Bianchi ha un debito di 3000 euro."


@pytest.fixture()
def mem(tmp_path):
    return Memory(tmp_path / "memory.db")


def _coppia_ritirata(m):
    """A ritirato da B con supersede esplicito. Ritorna (a, b, op_id)."""
    a = m.add(_ROSSI, topic="privacy/clienti", verified_by=["doc"])["id"]
    b = m.add(_BIANCHI, topic="privacy/altro", verified_by=["doc"])["id"]
    res = m.semantic.supersede(a, b, principal="test:ghost",
                               reason="test-ritiro")
    return a, b, res["undo_op_id"]


def test_undo_non_resuscita_un_fatto_cancellato(mem):
    m = mem
    a, _b, op = _coppia_ritirata(m)
    assert m.semantic.get(a) is not None

    m.semantic.delete(a, principal="test:ghost", action="forget")
    assert m.semantic.get(a) is None, "il forget deve rimuovere la riga"

    res = m.undo(op)
    assert res.get("ok") is not True, (
        f"un undo non puo' scavalcare una cancellazione: {res}")
    assert m.semantic.get(a) is None, (
        "IL FATTO CANCELLATO E' TORNATO IN VITA — la cancellazione e' "
        "l'intenzione piu' recente dell'utente e vince sull'undo")
    hits = m.search("Quanto deve il cliente Rossi?", k=3)
    assert all(_ROSSI not in h.get("text", "") for h in hits), (
        "il recall serve un fatto che l'utente ha cancellato")


def test_l_handle_invalidato_sparisce_dalla_lista(mem):
    """Nessun pulsante che promette un'azione impossibile."""
    m = mem
    a, _b, op = _coppia_ritirata(m)
    assert any(o["op_id"] == op for o in m.semantic.list_undoable_ops(limit=20))

    m.semantic.delete(a, principal="test:ghost", action="forget")
    assert not any(o["op_id"] == op
                   for o in m.semantic.list_undoable_ops(limit=20)), (
        "un handle che non puo' piu' agire non si mostra come disponibile")
    assert not any(r["reversible"] for r in m.retirement_log(limit=20)
                   if r["loser_id"] == a), (
        "il retirement-log deve dire irreversible su un loser cancellato")


def test_il_forget_resta_annullabile(mem):
    """La cura non deve uccidere la feature che il forget offre: l'handle
    del forget STESSO sopravvive e riporta indietro il fatto."""
    m = mem
    a = m.add(_ROSSI, topic="privacy/clienti", verified_by=["doc"])["id"]
    res = m.semantic.delete_with_undo(a, principal="test:ghost")
    assert res["removed"] is True and res["op_id"]
    assert m.semantic.get(a) is None

    undo = m.undo(res["op_id"])
    assert undo["ok"] is True and undo["action"] == "restored"
    assert m.semantic.get(a) is not None, (
        "delete_with_undo deve restare reversibile — e' la sua ragione d'essere")


def test_ritiro_e_poi_forget_del_WINNER_non_tocca_l_handle_del_loser(mem):
    """Falsificazione mirata: la cura deve colpire SOLO gli handle del fatto
    cancellato. Cancellare il VINCITORE non deve rendere irreversibile il
    ritiro del perdente — quel loser esiste ancora e ha diritto al ritorno."""
    m = mem
    a, b, op = _coppia_ritirata(m)
    m.semantic.delete(b, principal="test:ghost", action="forget")

    res = m.undo(op)
    assert res["ok"] is True and res["action"] == "restored", (
        f"l'handle del loser non c'entra col forget del winner: {res}")
    fa = m.semantic.get(a)
    assert fa is not None and fa.superseded_by is None
