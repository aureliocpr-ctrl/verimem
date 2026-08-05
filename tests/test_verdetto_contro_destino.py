"""Dove il verdetto del moat e il destino del fatto non concordano.

Misurato sul corpus reale il 2026-08-05, in ENTRAMBE le direzioni:

    quarantinati vivi 686, di cui 11 con verdetto >= 90 (10 a >= 99)
      es. 99.98  «Il rilevatore L1.13 elenca la parola italiana "fatto"...»
    serviti con verdetto SOTTO la soglia 40: 10, fino a 0.22
      es.  0.22  «La misura di 101.4 secondi su Memory.ignorance...»

Due anomalie opposte e nessuna vista che le nomini:
- il moat spende ~42 secondi per dire «vero al 100%» e il fatto resta fuori
  (lavoro pagato e dato perso — ws5 ha isolato che sono i referti che
  DOCUMENTANO un difetto, bloccati perché contengono le parole del difetto);
- il moat dice «la fonte non lo sostiene» e il fatto viene servito lo stesso.

Il secondo è il più serio per chi legge la memoria: il prodotto restituisce
come suo ciò che il proprio giudice ha bocciato. Questa vista non decide
niente — mostra le due liste, come il registro dei ritiri mostra le coppie.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory
from verimem.retirement_log import verdict_mismatches

_FONTE = "Company handbook: our head office is located in Milan, Italy."


@pytest.fixture()
def store(tmp_path):
    return Memory(tmp_path / "memory.db")


def test_un_fatto_giudicato_vero_ma_trattenuto_compare(store):
    m = store
    r = m.add("the office headquarters are in Milan", topic="hq", source=_FONTE)
    assert r["grounding_score"] is not None
    m.semantic.quarantine_fact(r["id"], reason="banco")

    out = verdict_mismatches(m.semantic)
    ids = [x["fact_id"] for x in out["judged_true_but_withheld"]]
    assert r["id"] in ids, out
    riga = out["judged_true_but_withheld"][0]
    assert riga["grounding_score"] >= 90
    assert riga["status"] == "quarantined"


def test_un_fatto_bocciato_ma_servito_compare(store):
    """Il caso serio: il giudice dice che la fonte non lo sostiene e il
    prodotto lo restituisce comunque."""
    m = store
    r = m.add("the office headquarters are in Milan", topic="hq", source=_FONTE)
    # porto il verdetto sotto la soglia lasciando il fatto servibile: è
    # esattamente lo stato in cui si trovano i dieci del corpus reale
    with __import__("sqlite3").connect(m.semantic.db_path) as con:
        con.execute("UPDATE facts SET grounding_score = 3.2 WHERE id = ?",
                    (r["id"],))

    out = verdict_mismatches(m.semantic)
    ids = [x["fact_id"] for x in out["judged_false_but_served"]]
    assert r["id"] in ids, out


def test_un_corpus_coerente_non_produce_righe(store):
    """Niente allarmi quando non c'è nulla da dire: una vista che segnala
    sempre qualcosa viene ignorata come il rumore che è."""
    m = store
    m.add("the office headquarters are in Milan", topic="hq", source=_FONTE)
    out = verdict_mismatches(m.semantic)
    assert out["judged_true_but_withheld"] == []
    assert out["judged_false_but_served"] == []


def test_le_soglie_sono_dichiarate(store):
    """Un numero senza la sua definizione è il difetto che questo ramo cura:
    «vero» e «falso» qui sono due tagli, e chi legge deve vederli."""
    out = verdict_mismatches(store.semantic)
    assert "90" in out["thresholds"] and "40" in out["thresholds"], out


def test_la_banda_contesa_e_una_categoria_a_parte(store):
    """ws4 ha misurato il 2026-08-05 che la cut di ammissione NON è una:
    40 (scala claude, il ripiego) o 70 (la calibrata del fine-tune), e quale
    tocchi dipende da quale giudice era disponibile in quel momento. Un 55
    entra con la prima e viene trattenuto con la seconda.

    Fra le due cut il destino non è un'INCOERENZA — è un'INCERTEZZA, e va
    nominata a parte: non «il prodotto ha sbagliato» ma «l'esito dipendeva
    dal minuto». Sul corpus reale sono 23 fatti, tutti trattenuti."""
    m = store
    r = m.add("the office headquarters are in Milan", topic="hq", source=_FONTE)
    with __import__("sqlite3").connect(m.semantic.db_path) as con:
        con.execute("UPDATE facts SET grounding_score = 55.0 WHERE id = ?",
                    (r["id"],))

    out = verdict_mismatches(m.semantic)
    ids = [x["fact_id"] for x in out["contested_band"]]
    assert r["id"] in ids, out
    # e NON deve finire fra i bocciati-ma-serviti: sotto la cut alta lo
    # sarebbe, sotto quella bassa no — chiamarlo difetto sarebbe una scelta
    # travestita da misura
    assert r["id"] not in [x["fact_id"] for x in out["judged_false_but_served"]]


def test_i_bocciati_serviti_sono_un_limite_inferiore_dichiarato(store):
    """La lista usa il taglio BASSO: sotto 40 un fatto è respinto da
    qualunque cut, quindi ogni riga è certa e il totale è un minimo. Deve
    dirlo, altrimenti si legge come «sono tutti»."""
    out = verdict_mismatches(store.semantic)
    assert "lower bound" in out["thresholds"].lower(), out["thresholds"]
