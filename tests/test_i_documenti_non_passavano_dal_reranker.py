"""Il reranker era cablato ai fatti e non ai documenti, e là serve di più.

Misurato il 2026-08-02 su un documento vero — 10383 byte, 18 chunk — con tre
domande a cui risponde e tre a cui no::

    domanda                                     bi-encoder   reranker CE
    [SI] quante skill hanno due status diversi    0.8272        3.1453
    [SI] cosa faceva il campo moat sui respinti   0.8120        2.0328
    [SI] quale commit ha curato il caveat         0.8292       -0.2292
    [NO] quale database usa il cluster            0.8149       -5.4931
    [NO] come si configura il proxy aziendale     0.8128       -6.6794
    [NO] qual e la ricetta della carbonara        0.7984       -5.5207

    bi-encoder    dentro min 0.8120  fuori max 0.8149  margine -0.0029  NON separa
    reranker CE   dentro min -0.2292 fuori max -5.4931 margine +5.2639  SEPARA

Il bi-encoder da solo **non separa**: una domanda FUORI TEMA (0.8149) prende
più di una che il documento contiene (0.8120), e tutti i punteggi stanno fra
0.79 e 0.83. Nessuna soglia può funzionare su una banda così compressa — ed è
il motivo per cui la cura del 30/07 (`max(floor, noise_floor)`) era stata
ritirata, e per cui `--min-score` su `search-docs` resta uno strumento per chi
sa già che taglio vuole.

Il problema non era la soglia: era lo STADIO MANCANTE. Il prodotto ha un
reranker cross-encoder (`semantic._rerank_via_daemon`), usato dal recall dei
FATTI dal 2026-06-13, e `DocumentIndex.search` non ci passava.

PERIMETRO, e perché è stretto. Il rerank qui è **opzionale e degradante**,
esattamente come sul percorso fatti: se il daemon non risponde entro il budget
si torna all'ordine del bi-encoder, senza errori e senza attese. Non è una
dipendenza — è uno stadio in più quando c'è. La prima chiamata a freddo paga
comunque (~33 s di caricamento, misurato il 31/07), quindi il default NON
cambia il comportamento di chi non ha il daemon caldo.
"""
from __future__ import annotations

import pytest

from verimem.document_index import DocumentIndex

#: (testo, punteggio bi-encoder). L'ordine è quello sbagliato: il chunk
#: pertinente è secondo, come nella misura reale.
CHUNKS = [
    {"text": "La ricetta della nonna per il pane sta nel quaderno.",
     "score": 0.8149, "source_id": "doc.md", "start": 0, "end": 51,
     "version": 1},
    {"text": "Il campo moat diceva «the source entails» anche sui respinti.",
     "score": 0.8120, "source_id": "doc.md", "start": 51, "end": 112,
     "version": 1},
]


@pytest.fixture()
def punteggi_ce(monkeypatch):
    """Il reranker vero, sostituito da uno che conosce la risposta giusta.

    Cerca una SOTTOSTRINGA invece di una chiave esatta: la prima stesura
    tagliava a 30 caratteri da un lato e a 29 dall'altro, e il doppio
    rispondeva sempre il default — un test che non poteva passare per una
    ragione che non c'entrava con la cura."""
    def _con(mappa):
        import verimem.document_index as di

        def _finto(pairs, **kw):
            return [next((v for chiave, v in mappa.items() if chiave in p[1]),
                         -9.9) for p in pairs]
        monkeypatch.setattr(di, "_rerank_pairs", _finto, raising=False)
    return _con


def test_il_reranker_rimette_in_ordine(punteggi_ce, monkeypatch):
    """Il caso misurato: il pertinente è secondo per il bi-encoder e primo
    per il cross-encoder."""
    import verimem.document_index as di

    punteggi_ce({"campo moat": 2.03, "ricetta della nonna": -5.52})
    monkeypatch.setattr(di.DocumentIndex, "_search_bi",
                        lambda self, q, k: list(CHUNKS), raising=False)
    idx = DocumentIndex.__new__(DocumentIndex)
    got = di._applica_rerank(idx, "cosa faceva il campo moat", list(CHUNKS))
    assert "moat" in got[0]["text"], (
        f"il reranker non ha riordinato: {[h['text'][:30] for h in got]}")


def test_senza_daemon_l_ordine_resta_quello_di_prima(monkeypatch):
    """Degradazione: nessun errore, nessuna attesa, ordine invariato."""
    import verimem.document_index as di

    monkeypatch.setattr(di, "_rerank_pairs", lambda pairs, **kw: None,
                        raising=False)
    idx = DocumentIndex.__new__(DocumentIndex)
    got = di._applica_rerank(idx, "una domanda", list(CHUNKS))
    assert [h["text"] for h in got] == [h["text"] for h in CHUNKS]


def test_un_reranker_che_esplode_non_fa_cadere_la_ricerca(monkeypatch):
    """Mai una dipendenza, sempre un'ottimizzazione."""
    import verimem.document_index as di

    def _rotto(pairs, **kw):
        raise RuntimeError("daemon in fiamme")
    monkeypatch.setattr(di, "_rerank_pairs", _rotto, raising=False)
    idx = DocumentIndex.__new__(DocumentIndex)
    got = di._applica_rerank(idx, "una domanda", list(CHUNKS))
    assert [h["text"] for h in got] == [h["text"] for h in CHUNKS]


def test_il_punteggio_del_reranker_viaggia_col_risultato(punteggi_ce):
    """Chi legge deve poter distinguere un ordine tenuto dal solo bi-encoder
    da uno passato dal cross-encoder — la stessa onestà di `ranking` sui
    fatti."""
    import verimem.document_index as di

    punteggi_ce({"campo moat": 2.03, "ricetta della nonna": -5.52})
    idx = DocumentIndex.__new__(DocumentIndex)
    got = di._applica_rerank(idx, "cosa faceva il campo moat", list(CHUNKS))
    assert "rerank_score" in got[0], sorted(got[0])
    assert got[0]["score"] == 0.8120, (
        "il punteggio del bi-encoder deve restare leggibile: sono due misure "
        "diverse, non una che sostituisce l'altra")
