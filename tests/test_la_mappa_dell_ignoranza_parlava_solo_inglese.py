"""La mappa dell'ignoranza aveva una stoplist di sole 19 parole inglesi.

`ignorance_map._STOP` — the, and, for, with, what, which, who, how, why, does,
is, are, was, were, this, that, from, into, about — e nient'altro. Il prodotto
ne ha già una da 104 parole EN+IT in `bm25_rank._QUERY_STOPWORDS`, usata dal
percorso lessicale dal 2026-07-07. Qui c'era una copia più povera e monolingue.

DUE DANNI, misurati.

① IL CONSIGLIO. `what_would_help` dice «a source about: …» ed elencava parole
   vuote. Su otto domande, 5 termini su 31 (16%) erano funzionali, **tutti
   italiani** — le inglesi uscivano pulite::

     quale database usa il cluster di produzione
        -> cluster, database, produzione, **quale**, usa
     chi ha scritto il rapporto sulla sicurezza
        -> **chi**, rapporto, scritto, sicurezza, sulla
     which database does the production cluster use
        -> cluster, database, production, use          (pulita)

② LA CLASSIFICAZIONE, che è peggio. La stessa `_keywords` alimenta
   `_quarantined_overlap(min_shared=2)`, che decide la classe
   `quarantined_only` — quella che dice a chi legge «l'evidenza ESISTE ed è in
   quarantena, la cura è una fonte o una revisione, non altro retrieval».
   Con due sole funzionali condivise scattava su fatti che non c'entravano::

     'come si configura il backup della macchina per la produzione'
     vs «La ricetta della nonna per il pane e nel quaderno.»
        overlap = 2   su ['della', 'per']        -> quarantined_only

     'quale e il prezzo del contratto con il fornitore'
     vs «Il gatto del vicino dorme con il cane.»
        overlap = 2   su ['con', 'del']          -> quarantined_only

   Le stesse frasi in inglese: overlap 0, perché `the`/`of`/`for` sono nella
   lista. Il prodotto mandava l'utente italiano a cercare una fonte per un
   fatto che parla di un gatto, e quello inglese no.

`_WORD` richiede già 3+ caratteri, quindi «il»/«la»/«di» erano fuori: il danno
lo facevano le funzionali LUNGHE — della, per, con, del, alla, sul — che
nessuna lista inglese poteva contenere.

Quarta occorrenza in giornata della stessa classe: la cura esisteva
(`_QUERY_STOPWORDS`) e non era arrivata qui. Quindi si richiama, non si ricopia
— una lista copiata diverge, ed è esattamente ciò che era successo.
"""
from __future__ import annotations

import pytest

from verimem.bm25_rank import _QUERY_STOPWORDS
from verimem.ignorance_map import _STOP, _keywords

#: Coppie domanda/fatto che NON parlano della stessa cosa. Se le parole
#: condivise sono tutte funzionali, non c'è pertinenza da dichiarare.
ESTRANEI = [
    ("come si configura il backup della macchina per la produzione",
     "La ricetta della nonna per il pane e nel quaderno."),
    ("quale e il prezzo del contratto con il fornitore",
     "Il gatto del vicino dorme con il cane."),
    ("quando arriva la conferma dello stato della pratica",
     "La finestra della cucina dello zio resta aperta."),
]


@pytest.mark.parametrize("domanda,fatto", ESTRANEI)
def test_due_frasi_estranee_non_condividono_contenuto(domanda, fatto):
    comuni = _keywords(domanda) & _keywords(fatto)
    assert len(comuni) < 2, (
        f"overlap {len(comuni)} su {sorted(comuni)} fra due frasi che non "
        f"parlano della stessa cosa: con >=2 scatta `quarantined_only`, cioè "
        f"«l'evidenza esiste ed è in quarantena»\n  {domanda}\n  {fatto}")


def test_le_funzionali_italiane_non_sono_parole_chiave():
    """Il criterio, non l'elenco: qualunque parola la lista condivisa
    consideri vuota, non deve uscire da `_keywords`."""
    testo = ("quale e il costo del contratto con la ditta della zona "
             "per quanto riguarda sulla base dei dati")
    residue = {w for w in _keywords(testo) if w in _QUERY_STOPWORDS}
    assert not residue, (
        f"parole che il percorso lessicale scarta da luglio finiscono nelle "
        f"chiavi della mappa: {sorted(residue)}")


def test_le_inglesi_continuano_a_essere_scartate():
    """Controprova: la cura non deve perdere quello che già funzionava."""
    testo = "which is the cost of the annual plan for the team"
    residue = {w for w in _keywords(testo) if w in _QUERY_STOPWORDS}
    assert not residue, sorted(residue)


def test_le_parole_di_contenuto_restano():
    """E non deve mangiare il contenuto: senza queste il consiglio è vuoto."""
    got = _keywords("quale database usa il cluster di produzione")
    assert {"database", "cluster", "produzione"} <= got, sorted(got)


def test_la_lista_non_e_una_copia():
    """Due copie divergono, ed è così che questa è nata: la mappa deve
    chiedere le parole vuote allo stesso posto del percorso lessicale."""
    assert _QUERY_STOPWORDS <= _STOP, (
        "la mappa dell'ignoranza ha una lista propria più povera: mancano "
        + " ".join(sorted(_QUERY_STOPWORDS - _STOP))[:120])
