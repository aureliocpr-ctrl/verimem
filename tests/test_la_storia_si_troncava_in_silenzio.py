"""La storia si fermava a cinque, e nessuno diceva che ce n'era dell'altra.

MISURATO il 2026-08-04 su un registro di 25 schede: `recall(with_history=True)`
restituisce CINQUE voci, non ventiquattro. Il limite e' `max_hops=5`, il valore
di default di `temporal_context.fact_history` — e `client.py` non lo passava
mai, quindi la superficie SDK non poteva ne' alzarlo ne' sapere di averlo.

    fact_history(sm, fact_id, *, max_hops: int = 5)       temporal_context.py:115
        temporal_context.py:251/272   lo passa
        trust_report.py:86            lo passa
        client.py:630                 NON lo passava     <- la porta pubblica

⚠️ IL DIFETTO NON E' IL NUMERO CINQUE. Un limite ci vuole: una catena di
duecento schede riversata in un contesto e' un'altra forma dello stesso danno
che questo modulo combatte. Il difetto e' che il taglio era MUTO — cinque voci
e nessun segno che ce ne fossero altre diciannove. Chi legge conclude che la
storia sia quella, ed e' la classe del silent-drop.

LA CURA, due pezzi:
  * si CHIEDE UN SALTO IN PIU' di quelli che si mostrano: se torna, il taglio
    c'e' stato e si dichiara (`history_truncated`). Costa un hop, non un
    conteggio dell'intera catena.
  * si ESPONE il limite (`history_hops`), perche' chi ne vuole di piu' possa
    chiederlo invece di non sapere che esiste una manopola.
"""
from __future__ import annotations

from verimem.client import Memory


def _catena(m: Memory, n: int) -> None:
    """n scritture sullo stesso soggetto: il write path le incatena."""
    for i in range(n):
        m.add(f"Il server nexus ha {16 * (i + 1)} gigabyte di memoria.",
              topic="lab/catena")


def test_la_storia_dichiara_di_essere_stata_tagliata(tmp_path):
    m = Memory(str(tmp_path / "s.db"))
    _catena(m, 8)
    hits = m.recall("Quanta memoria ha il server nexus?", k=1,
                    with_history=True, history_hops=3)
    assert hits, "nessun risultato"
    h = hits[0]
    assert len(h.get("history") or []) == 3, h.get("history")
    assert h.get("history_truncated") is True, (
        "la storia e' stata tagliata e non lo dichiara")


def test_una_storia_intera_non_si_dichiara_tagliata(tmp_path):
    """IL PRESIDIO: se ci sta tutta, nessun avviso — un flag sempre acceso
    non e' un'informazione."""
    m = Memory(str(tmp_path / "s.db"))
    _catena(m, 3)
    hits = m.recall("Quanta memoria ha il server nexus?", k=1,
                    with_history=True, history_hops=10)
    assert hits
    assert not hits[0].get("history_truncated")


def test_il_limite_si_puo_alzare(tmp_path):
    """Prima non c'era modo di chiedere di piu' dalla porta pubblica: il
    valore era il default di una funzione che questa superficie non passava."""
    m = Memory(str(tmp_path / "s.db"))
    _catena(m, 9)
    corta = m.recall("Quanta memoria ha il server nexus?", k=1,
                     with_history=True, history_hops=2)
    lunga = m.recall("Quanta memoria ha il server nexus?", k=1,
                     with_history=True, history_hops=8)
    assert len(corta[0]["history"]) == 2
    assert len(lunga[0]["history"]) > len(corta[0]["history"])


def test_senza_with_history_non_cambia_nulla(tmp_path):
    """L'ALTRO PRESIDIO: chi non chiede la storia non paga nulla e non vede
    campi nuovi."""
    m = Memory(str(tmp_path / "s.db"))
    _catena(m, 8)
    h = m.recall("Quanta memoria ha il server nexus?", k=1)[0]
    assert "history" not in h
    assert "history_truncated" not in h
