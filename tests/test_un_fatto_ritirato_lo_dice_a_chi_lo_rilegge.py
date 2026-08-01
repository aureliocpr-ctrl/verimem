"""Un fatto ritirato deve DIRLO a chi lo rilegge.

`update()` e' la porta ufficiale della sostituzione e promette, nel suo
docstring, che «the old version stays in the provenance chain, it is not
destroyed». La promessa e' mantenuta a meta': il vecchio si rilegge davvero,
ma la vista che l'SDK restituisce e' INDISTINGUIBILE da quella di un fatto
vivo — stesso `status`, nessun campo che nomini il successore. Il recall di
default smette di servirlo e chi ha in mano l'id non ha modo di accorgersene.

Misurato su store vergine, canale SDK, zero flag (2026-08-01):

    DB:   ('fdb0345b31d5', 'Il piano annuale costa 100 euro.',
           'model_claim', 'a8b1b7d03471')     <- superseded_by valorizzato
    SDK:  status: model_claim
          'superseded_by' fra le chiavi? False

E' la SECONDA occorrenza della stessa classe su questa stessa funzione: il
docstring di `_fact_view` racconta che nacque perche' «get/get_all lacked the
fields search exposes», cioe' perche' una superficie di lettura taceva una
proprieta' di provenienza. Il campo aggiunto allora fu `verified_by`; questo
e' lo stesso difetto sul campo accanto.

Il caso non e' teorico: la supersessione scatta DA SOLA sull'euristica
dell'evoluzione, non solo su `update()` esplicita, e ha gia' ritirato fatti
veri e scorrelati (vedi `test_due_misure_diverse_non_sono_un_aggiornamento`).
Finche' la lettura tace, quel ritiro e' invisibile a chiunque non apra il DB
con sqlite3.
"""
from __future__ import annotations

import sqlite3

from verimem.client import Memory

VECCHIO = "Il piano annuale costa 100 euro."
NUOVO = "Il piano annuale costa 200 euro."


def _superseded_by_nel_db(m: Memory, fact_id: str) -> str | None:
    con = sqlite3.connect(m.semantic.db_path)
    try:
        riga = con.execute("SELECT superseded_by FROM facts WHERE id = ?",
                           (fact_id,)).fetchone()
    finally:
        con.close()
    return riga[0] if riga else None


def test_chi_rilegge_un_fatto_sostituito_lo_vede_dichiarato(tmp_path):
    """Il caso della porta ufficiale: `update()`."""
    m = Memory(path=tmp_path / "m.db")
    primo = m.add(VECCHIO, topic="prezzi")
    id_vecchio = primo["id"]

    esito = m.update(id_vecchio, NUOVO)
    assert esito.get("stored"), esito
    id_nuovo = esito["id"]
    assert _superseded_by_nel_db(m, id_vecchio) == id_nuovo, (
        "presupposto del test: il DB deve aver registrato la sostituzione")

    vista = m.get(id_vecchio)
    assert vista is not None, "il vecchio deve restare consultabile"
    assert vista.get("superseded_by") == id_nuovo, (
        f"la vista non dichiara il successore: {sorted(vista)}")


def test_il_fatto_vivo_non_porta_un_successore(tmp_path):
    """Il campo dev'essere None sul fatto vivo, non assente: chi lo legge
    deve poter distinguere «non sostituito» da «questa vista non lo dice»."""
    m = Memory(path=tmp_path / "m.db")
    vivo = m.add(VECCHIO, topic="prezzi")
    vista = m.get(vivo["id"])
    assert "superseded_by" in vista, sorted(vista)
    assert vista["superseded_by"] is None


def test_anche_la_lista_e_la_ricerca_lo_dicono(tmp_path):
    """Le tre superfici passano dalla stessa `_fact_view` e devono restare
    d'accordo: era proprio il loro disaccordo a generare quella funzione."""
    m = Memory(path=tmp_path / "m.db")
    id_vecchio = m.add(VECCHIO, topic="prezzi")["id"]
    m.update(id_vecchio, NUOVO)

    for riga in m.get_all(topic="prezzi", limit=50):
        assert "superseded_by" in riga, (
            f"get_all tace il campo che get dichiara: {sorted(riga)}")

    for riga in m.search("quanto costa il piano annuale", k=10):
        assert "superseded_by" in riga, (
            f"search tace il campo che get dichiara: {sorted(riga)}")
