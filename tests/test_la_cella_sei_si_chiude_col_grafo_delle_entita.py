"""«Rossi» e «Bianchi» sono due entità, e il prodotto lo sapeva già.

LA CELLA 6, il buco storico. La matrice di ws5::

    caso                                    vivi  atteso
    un autore,  due entità CON codice         2      2    ✅ curato (codes_in)
    due autori, due entità CON codice         2      2    ✅
    un autore,  aggiornamento                 1      1    ✅ presidio
    due autori, aggiornamento                 1      1    ✅
    un autore,  due entità SENZA codice       1      2    ❌  <- QUESTA

Su questa cella sono caduti SEI criteri lessicali in una notte: i nomi propri
via `_CAPS_RE` (90% del corpus, e gli esempi erano «All», «Multiple»,
«Episodes»), l'ancoraggio (68% contro 66% sul corpus vero), l'allargamento di
`codes_in` alla coda alfabetica (ws5: 102 fatti, e dentro ci sono `JSON-Lines`,
`X-Frame`, `A-Za` — un pezzo di regex).

🔑 E LA RISPOSTA ERA IN CASA DAL PRINCIPIO, trovata da ws5 misurando::

    «DC-Nord e DC-Sud il prodotto li distingue GIÀ, senza nessun criterio
     lessicale: il grafo li estrae come due entità [proper] separate, nello
     stesso add() che archivia il fatto.»

`extract_entities_lite` è la funzione che alimenta il grafo (semantic.py:3101).
È pura, quindi il gate può chiamarla sulle due proposizioni: **stessa
superficie, non una copia**.

⚠️ SI CONFRONTANO I `proper`, NON TUTTE LE ENTITÀ, e senza questo la cura non
funzionerebbe sul caso che l'ha motivata::

    DC-Nord -> [{'DC','acronym'}, {'Nord','proper'}]
    DC-Sud  -> [{'DC','acronym'}, {'Sud','proper'}]

condividono l'acronimo `DC`. Un ACRONIMO è un tipo di cosa (`GB`, `RAM`, `DC`),
un `proper` è un'ISTANZA — ed è l'istanza che distingue due record.

I NUMERI DI ws5 sulle 104 coppie ordinarie del corpus vero::

    42 entità CONDIVISE        -> il veto lascia passare  (= il presidio)
    31 DISGIUNTE               -> il veto salva           (= il buco chiuso)
    31 senza entità da un lato -> non coperto             (= comportamento vecchio)
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.anti_confab_gate import _entita_diverse


class _F:
    def __init__(self, prop, t):
        self.proposition = prop
        self.created_at = t
        self.asserted_at = None
        self.verified_by = []
        self.source_signature = None
        self.writer_principal = None


@pytest.mark.parametrize("a,b,diverse", [
    # LA CELLA 6: nomi propri, nessun codice
    ("Il paziente Rossi pesa 70 chilogrammi.",
     "Il paziente Bianchi pesa 95 chilogrammi.", True),
    # IL CASO DI ws5: coda alfabetica, che `codes_in` non prendeva
    ("Il datacenter DC-Nord ha 480 rack installati.",
     "Il datacenter DC-Sud ha 512 rack installati.", True),
    # I CODICI: continuano a funzionare (nessuna entità, se ne occupa codes_in)
    ("Il magazzino K-77 di Rovigo ha 4200 metri quadrati.",
     "Il magazzino Z-08 di Ancona ha 2600 metri quadrati.", True),
    # ⛔ L'AGGIORNAMENTO: stessa entità, valore nuovo -> NON deve scattare
    ("Il magazzino K-77 di Rovigo ha 4200 metri quadrati.",
     "Il magazzino K-77 di Rovigo ha 5100 metri quadrati.", False),
    ("Il paziente Rossi pesa 70 chilogrammi.",
     "Il paziente Rossi pesa 78 chilogrammi.", False),
    # ⛔ SOLO ACRONIMI CONDIVISI: `GB` e `RAM` sono TIPI, non istanze
    ("Il server di produzione ha 64 GB di RAM.",
     "Il server di produzione ha 128 GB di RAM.", False),
    # NESSUNA ENTITÀ da un lato: non si sa nulla — e dal 2026-08-21 il «non so»
    # non autorizza più il ritiro. Questa riga diceva `False` con la nota
    # «comportamento di prima»: `59fb0862` (anti_confab_gate:232) ha cambiato
    # proprio quel comportamento, e la nota è diventata la descrizione di ciò
    # che non vale più.
    #
    # È LA STESSA COPPIA-TIPO del presidio gemello, chiusa in `f3496eda`
    # (`test_il_fatto_di_bruno_archiviava_quello_di_anna`, «K-77» / «di Ancona»):
    # là un magazzino, qui un paziente, in entrambi UN LATO SOLO ha un `proper`
    # e il ramo 232 risponde `True` = non ritirare. La motivazione, i 43 casi
    # del corpus e i 34 con entrambi i grounding ≥ 90 stanno in quel commit e
    # non li ricopio: se cade quella cura cade anche questa, e viceversa.
    #
    # ⚖️ E QUI IL CASO È PIÙ NETTO CHE LÀ:
    #     «Il paziente Rossi pesa 70 chilogrammi.» -> proper = ['rossi']
    #     «Il peso rilevato e' di 95 chilogrammi.» -> proper = []
    # La seconda frase NON NOMINA il paziente. Può essere il peso di Rossi
    # (aggiornamento) o di chiunque altro (fatto diverso), e nessun criterio
    # sintattico può deciderlo. Ritirare qui significa cancellare «Rossi pesa
    # 70» sulla base di una frase che Rossi non lo nomina.
    ("Il paziente Rossi pesa 70 chilogrammi.",
     "Il peso rilevato e' di 95 chilogrammi.", True),
])
def test_il_grafo_distingue_dove_i_codici_non_arrivavano(a, b, diverse):
    assert _entita_diverse(_F(b, 200.0), _F(a, 100.0)) is diverse


def _servibili(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rr = con.execute("SELECT status,superseded_by,proposition FROM facts").fetchall()
    return [r for r in rr if r["superseded_by"] is None
            and (r["status"] or "") != "quarantined"], rr


def test_END_TO_END_la_cella_sei_e_chiusa(tmp_path):
    """LA MISURA CHE CONTA: due pazienti diversi, nessun codice, e prima di
    questa cura ne sopravviveva UNO."""
    from verimem.client import Memory

    db = tmp_path / "cella6.db"
    m = Memory(str(db))
    m.add("Il paziente Rossi pesa 70 chilogrammi.", topic="az/p")
    m.add("Il paziente Bianchi pesa 95 chilogrammi.", topic="az/p")
    vivi, tutti = _servibili(db)
    assert len(vivi) == 2, (
        "la cella 6 e' ancora aperta: " +
        " · ".join(f"[{r['status']}] {r['proposition'][:34]}" for r in tutti))


def test_END_TO_END_l_aggiornamento_RITIRA_ancora(tmp_path):
    """IL PRESIDIO END-TO-END, e vale più della cura: lo stesso paziente che
    cambia peso deve continuare a sovrascrivere. Se questo cade, abbiamo
    trasformato una memoria che aggiorna in una che accumula."""
    from verimem.client import Memory

    db = tmp_path / "agg.db"
    m = Memory(str(db))
    m.add("Il paziente Rossi pesa 70 chilogrammi.", topic="az/p")
    m.add("Il paziente Rossi pesa 78 chilogrammi.", topic="az/p")
    vivi, tutti = _servibili(db)
    assert len(vivi) == 1, [r["proposition"] for r in tutti]
    assert "78" in vivi[0]["proposition"], (
        "sopravvive il valore VECCHIO: la correzione non ha sostituito nulla")
