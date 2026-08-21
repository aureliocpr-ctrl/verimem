"""La memoria multilingue è una promessa del prodotto, e nessuno la presidiava.

MISURATO DA UTENTE, con l'embedder VERO e i fatti scritti TUTTI IN ITALIANO::

    [it] 0.889   [en] 0.8641  [de] 0.8403  [fr] 0.8804
    [es] 0.8705  [pt] 0.8795  [nl] 0.8509  [pl] 0.8223
    risposte giuste: 8/8

Otto lingue, otto risposte corrette, tutte sopra 0.82. Il retrieval funziona
davvero cross-lingua — e questa è una **cosa che il prodotto fa bene** e che
non aveva un solo test.

⚠️ PERCHÉ SERVE UN PRESIDIO E NON BASTA LA MISURA: il giorno in cui qualcuno
cambia embedder, aggiunge una normalizzazione monolingue (una stoplist, uno
stemmer italiano, un lowercase ASCII) o tocca il ranking, questa garanzia si
rompe **in silenzio** — non c'è nessuna riga che la difenda. È già successo in
casa: `content_tokens` leggeva ASCII e dava zero token sul cirillico.

⚠️ E L'ASIMMETRIA CHE NE ESCE, da mettere accanto:
    TROVARE (recall)     8 lingue su 8    <- questo file
    CONTARE (ask/count)  2 lingue su 8    <- misurato, `_COUNT` è IT/EN
Il prodotto capisce le domande in otto lingue quando deve trovare, e in due
quando deve contare.

⚠️ QUESTO FILE USA L'EMBEDDER VERO. La fixture `_stub_embedding_model` di
conftest è `autouse` e sostituisce il modello con uno stub su SHA-256 dei
token: sotto quello stub ogni coseno è finto e un test cross-lingua non
misurerebbe NULLA. Qui la si sovrascrive a livello di modulo — è il pattern
pytest per disattivare una fixture autouse in un file solo. Marcato `slow`
perché carica sentence-transformers davvero.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

pytestmark = pytest.mark.slow

FATTI_IT = [
    "Il magazzino centrale di Rovigo ha 4200 metri quadrati.",
    "La prova gratuita dura quattordici giorni.",
    "L'assistenza risponde entro due giorni lavorativi.",
    "Il piano annuale costa 1200 euro all'anno.",
]

DOMANDE = [
    ("it", "Quanto dura la prova gratuita?"),
    ("en", "How long is the free trial?"),
    ("de", "Wie lange dauert die kostenlose Testphase?"),
    ("fr", "Combien de temps dure l'essai gratuit?"),
    ("es", "Cuanto dura la prueba gratuita?"),
    ("pt", "Quanto tempo dura o teste gratuito?"),
    ("nl", "Hoe lang duurt de gratis proefperiode?"),
    ("pl", "Jak dlugo trwa bezplatny okres probny?"),
]


@pytest.fixture()
def _stub_embedding_model(monkeypatch):
    """SOVRASCRIVE la fixture autouse di conftest: qui serve il modello VERO.

    Sotto lo stub (SHA-256 dei token) un test cross-lingua misurerebbe la
    coincidenza di due hash, non la somiglianza di due frasi — cioè
    esattamente nulla di ciò che questo file esiste per difendere.

    ⚠️ MA LA FIXTURE DI CONFTEST FA QUATTRO COSE, NON UNA (conftest.py:121-146):
    monta lo stub, **toglie `HIPPO_ENCODE_DELEGATE_ONLY` dall'ambiente**, mette
    `ENGRAM_ENCODE_SERVICE=0` e svuota la cache. Sovrascriverla per rinunciare
    allo STUB faceva rinunciare anche al resto — e il `delenv` serve qui più che
    altrove, perché questo è l'unico file che chiede un encode VERO.

    Il difetto misurato il 2026-08-21 su `68ea7614`, con il flag ereditato
    nell'ambiente (conftest.py:137 documenta dal 2026-06-06 che un
    `mcp_server.main()` in-process lo fa leakare permanentemente)::

        13 failed, 3 passed   —  passano solo it, es, pt
        WARNING store: encode delegate unavailable → scritto SENZA embedding

    Passavano cioè le sole lingue lessicalmente vicine all'italiano: i fatti
    entravano senza vettore e il recall cadeva su keyword. **Un test cross-lingua
    che misura la coincidenza delle parole è precisamente ciò che questo file
    esiste per impedire** — la stessa ragione per cui rifiuta lo stub.

    ⚠️ In CI passa lo stesso, perché là il flag non è nell'ambiente e non c'è
    niente da togliere: il difetto è LATENTE e si manifesta solo dove il flag è
    stato ereditato. E questo file è fra i 29 che nessun job della CI esegue,
    quindi non lo avrebbe visto nessuno.
    """
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    yield


@pytest.fixture
def memoria_italiana(tmp_path_factory):
    m = Memory(str(tmp_path_factory.mktemp("multi") / "s.db"))
    for f in FATTI_IT:
        m.add(f, topic="az/faq")
    return m


@pytest.mark.parametrize("lingua,domanda", DOMANDE)
def test_una_domanda_in_qualunque_lingua_trova_il_fatto_italiano(
        memoria_italiana, lingua, domanda):
    """IL CUORE: i fatti sono in italiano, la domanda no, la risposta è giusta."""
    hits = memoria_italiana.recall(domanda, k=1)
    assert hits, f"[{lingua}] nessun risultato per «{domanda}»"
    testo = str(hits[0].get("text") or "")
    assert "quattordici" in testo, (
        f"[{lingua}] risposta sbagliata: {testo[:60]}")


#: una domanda fuori tema PER OGNI lingua, con la stessa forma della sua
#: gemella in tema: è il termine di paragone che rende leggibile lo score.
FUORI_TEMA = {
    "it": "Quale database usa il cluster di produzione?",
    "en": "Which database does the production cluster use?",
    "de": "Welche Datenbank nutzt der Produktions-Cluster?",
    "fr": "Quelle base de donnees utilise le cluster de production?",
    "es": "Que base de datos usa el cluster de produccion?",
    "pt": "Qual base de dados usa o cluster de producao?",
    "nl": "Welke database gebruikt het productiecluster?",
    "pl": "Ktorej bazy danych uzywa klaster produkcyjny?",
}


@pytest.mark.parametrize("lingua,domanda", DOMANDE)
def test_e_la_SEPARA_da_una_domanda_fuori_tema(memoria_italiana, lingua, domanda):
    """IL PRESIDIO CHE SERVE DAVVERO — ed è la SEPARAZIONE, non il punteggio.

    Il test sopra passerebbe anche con un ranking casuale: con k=1 su quattro
    fatti, azzeccarla è un colpo su quattro. Serve sapere che il modello ha
    CAPITO la domanda invece di indovinarla.

    ⚠️ E NON CON UNA SOGLIA ASSOLUTA, che è la prima stesura di questo test ed
    era sbagliata: chiedeva `score >= 0.75` sulla scorta dei valori misurati a
    mano (0.82-0.89), e sotto pytest usciva 0.7006. Non era il modello — era
    che **fuori da pytest gira il rerank** (`{"rerank": "applied"}`) e dentro
    no, quindi la soglia misurava quali STADI del ranking sono attivi, non se
    il retrieval è multilingue. Due misure della stessa cosa divergevano, e la
    costruita male era la mia.

    La separazione invece non dipende dagli stadi: qualunque configurazione
    dia i punteggi, la domanda in tema deve stare SOPRA quella fuori tema
    nella stessa lingua. Se un giorno una lingua smette di separare, lì il
    multilingue si è rotto davvero."""
    in_tema = memoria_italiana.recall(domanda, k=1)
    fuori = memoria_italiana.recall(FUORI_TEMA[lingua], k=1)
    s_tema = float(in_tema[0].get("score") or 0.0) if in_tema else 0.0
    s_fuori = float(fuori[0].get("score") or 0.0) if fuori else 0.0
    assert s_tema > s_fuori, (
        f"[{lingua}] in tema {s_tema} NON supera fuori tema {s_fuori}: "
        f"in questa lingua il modello non sta capendo la domanda")
