"""Perché la guardia dell'overlap resta EN-only: una cura scritta e ritirata.

`truth_reconciliation._OVERLAP_STOP` ha 39 parole, tutte inglesi, mentre
`bm25_rank._QUERY_STOPWORDS` ne ha 128 EN+IT. Il 2026-08-02 il censimento delle
stoplist ha contato sei liste «povere» e questa sembrava la settima cura ovvia
della stessa classe: richiamare la lista condivisa invece di tenerne una copia.

**È stata scritta, misurata e ritirata nella stessa ora.** Il motivo è che su
un Jaccard togliere parole vuote può ALZARE il punteggio invece di abbassarlo,
quando quelle parole stanno in UNA SOLA delle due frasi::

    a = "Taylor David shared anecdotes about the museum trip"
    b = "Taylor David launched a new consultancy company"

    39 storiche   A=7 B=6 comuni=2 unione=11  ->  Jaccard 0.1818  rifiuta
    unione bm25   A=6 B=6 comuni=2 unione=10  ->  Jaccard 0.2000  ACCETTA

Una parola sola («about», presente solo in `a`): l'unione si accorcia, il
rapporto sale, e la guardia — che rifiuta sotto 0.2 — passa dall'altra parte.
Il caso è quello che la guardia esiste per prendere: stesso soggetto, attributo
DIVERSO, che l'NLI sovra-chiama come contraddizione. Accettarlo significa una
supersessione in più, cioè alimentare il problema più grosso del corpus.

Il test esisteva già (`test_reconcile_overlap_guard.py`) e ha preso la
regressione al primo giro di verifica. Questo file non ripete quel presidio:
tiene il RAGIONAMENTO, così chi rilegge la lista e la trova «povera» trova
anche il motivo per cui è rimasta così.

Lezione generale, che vale oltre questo file: una cura giusta ovunque —
togliere le parole vuote — non è automaticamente giusta dentro una metrica
NORMALIZZATA. Lì il denominatore fa parte del verdetto.
"""
from __future__ import annotations

from verimem.bm25_rank import _QUERY_STOPWORDS
from verimem.truth_reconciliation import _OVERLAP_STOP, _content_overlap

#: Il caso che ha ritirato la cura. Stesso soggetto, attributo diverso: la
#: guardia deve RIFIUTARE, e la soglia di riferimento è 0.2.
A = "Taylor David shared anecdotes about the museum trip"
B = "Taylor David launched a new consultancy company"


def test_la_guardia_rifiuta_gli_attributi_diversi():
    got = _content_overlap(A, B)
    assert got < 0.2, (
        f"overlap {got:.4f}: la guardia accetterebbe un conflitto fra due "
        f"attributi diversi dello stesso soggetto, cioè una supersessione in "
        f"più")


def test_unire_la_lista_condivisa_ROMPE_questa_guardia():
    """Presidia la DECISIONE, non il codice: se un domani qualcuno unisce le
    due liste «per coerenza», questo test mostra il conto prima che il danno
    arrivi in produzione."""
    from verimem.truth_reconciliation import _conflict_tokens

    def jaccard(stop):
        ta = {t for t in _conflict_tokens(A) if t not in stop}
        tb = {t for t in _conflict_tokens(B) if t not in stop}
        return len(ta & tb) / len(ta | tb)

    ora = jaccard(_OVERLAP_STOP)
    unita = jaccard(_OVERLAP_STOP | _QUERY_STOPWORDS)
    assert ora < 0.2 <= unita, (
        f"il conto è cambiato: ora {ora:.4f}, con la lista unita {unita:.4f}. "
        f"Se unita è tornata sotto 0.2 la cura è diventata sicura e questo "
        f"test va rifatto; se ora è salito sopra, la guardia è già rotta.")


def test_la_lista_e_rimasta_quella_storica():
    """Se `_OVERLAP_STOP` cresce, qualcuno ha applicato la cura ritirata."""
    assert len(_OVERLAP_STOP) == 39, (
        f"{len(_OVERLAP_STOP)} parole invece di 39: la lista è stata estesa, "
        f"e il motivo per cui era corta sta nel commento sopra la sua "
        f"definizione")
