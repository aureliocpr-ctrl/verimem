"""TERZA VOLTA che questo messaggio dichiara un'azione non avvenuta — e stavolta la
combinazione l'ha creata la guardia a1 (aeee8305), cioe' io.

Il file gia' documenta le altre due, nel commento a ``anti_confab_gate.py:1820``:
  «IL MESSAGGIO DICHIARAVA UN'AZIONE CHE NON ERA AVVENUTA … annunciando "the older
   value is superseded" con supersede_ids INTATTO»
  «SECONDA VOLTA CHE QUESTO MESSAGGIO DICHIARA UNA COSA CHE NON E' AVVENUTA»

LA GIUNTURA, misurata con un A/B fra 42bb3839 e 68ea7614:
  · il ramo LESSICALE mette il cid fra i conflitti (guardia a1) -> il nuovo e' QUARANTINATO
  · il ramo SEMANTICO valuta la stessa coppia «evolution» -> emette L3-supersession
  · l'handler NON applica la supersessione (lo fa solo se action=='persist')
  ⇒ il vecchio resta VIVO, il nuovo e' RESPINTO, e la ricevuta annuncia il contrario.

PRIMA della guardia il messaggio diceva il vero (superseded_by valorizzato, nuovo
ammesso): non e' un difetto latente che ho scoperto, e' uno che ho INTRODOTTO.
"""
from __future__ import annotations

import pytest

from verimem import Memory

TOPIC = "pricing/plan"
FONTE = ["source-doc:billing:1"]


def test_un_write_quarantinato_non_annuncia_di_aver_superseduto(tmp_path, monkeypatch):
    """Se il write finisce in quarantena, nessun avviso puo' dire che il vecchio
    e' stato superseduto: non lo e', ed e' vivo nello store."""
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)
    mem = Memory(path=tmp_path / "sem" / "sem.db")

    t1 = "The subscription costs 100 euros per month."
    r1 = mem.add(t1, topic=TOPIC, verified_by=FONTE, source=t1, validate="full")
    r2 = mem.add("The subscription costs 150 euros per month.",
                 topic=TOPIC, verified_by=FONTE, validate="full")   # niente source

    vecchio = mem.semantic.get(r1["id"])
    # presupposti del banco: se cadono questi, il test misura un altro caso
    assert r2.get("status") == "quarantined", "presupposto: la guardia a1 respinge il nuovo"
    assert vecchio.superseded_by is None, "presupposto: il vecchio resta vivo"

    avvisi = r2.get("warnings") or []
    bugiardi = [w for w in avvisi
                if "supersed" in (str(w.get("layer", "")) + str(w.get("reason", ""))
                                  + str(w.get("advice", ""))).lower()]
    assert not bugiardi, (
        "la ricevuta annuncia una supersessione che NON e' avvenuta: il vecchio ha "
        f"superseded_by=None e il nuovo e' {r2.get('status')!r}, ma gli avvisi dicono "
        f"{[w.get('layer') for w in bugiardi]!r} -> {[str(w.get('advice'))[:80] for w in bugiardi]!r}")


def test_CONTROLLO_quando_supersede_DAVVERO_l_avviso_ci_deve_essere(tmp_path, monkeypatch):
    """Il gemello obbligatorio: se la supersessione avviene, l'avviso deve restare.
    Senza questo, la cura potrebbe semplicemente cancellare l'avviso sempre — e
    passerebbe il test di sopra togliendo informazione vera all'utente."""
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)
    mem = Memory(path=tmp_path / "sem" / "sem.db")

    t1 = "The subscription costs 100 euros per month."
    t2 = "The subscription costs 150 euros per month."
    r1 = mem.add(t1, topic=TOPIC, verified_by=FONTE, source=t1, validate="full")
    r2 = mem.add(t2, topic=TOPIC, verified_by=FONTE, source=t2, validate="full")

    assert mem.semantic.get(r1["id"]).superseded_by == r2["id"], (
        "presupposto: con la source la supersessione avviene ancora")
    avvisi = r2.get("warnings") or []
    assert any("supersed" in (str(w.get("layer", "")) + str(w.get("advice", ""))).lower()
               for w in avvisi), (
        "la supersessione e' avvenuta ma la ricevuta non lo dice piu': la cura ha "
        f"tolto un avviso VERO. avvisi={[w.get('layer') for w in avvisi]!r}")
