"""`verimem recall` mostrava la somiglianza e non il verdetto.

    $ verimem recall "su quale porta ascolta il servizio di fatturazione"
    - Il servizio di fatturazione ascolta sulla porta 8443. [0.90]

Quel `[0.90]` e' la SOMIGLIANZA fra la domanda e il fatto: dice quanto il fatto
risponde, non se e' vero. Il fatto era stato ammesso a 99.0 e non si vedeva.

E' il comando di lettura per eccellenza — chi interroga la memoria da riga di
comando passa di qui — e un solo numero accanto a una frase invita a leggerlo
come una misura di affidabilita'. Sono due assi diversi e servono entrambi: un
fatto molto pertinente e mai verificato e' precisamente il caso in cui chi legge
va avvisato.

Prova la RIGA, non il recall. Il primo tentativo passava dal comando intero e
dava n=0: la suite sostituisce l'embedder con uno stub deterministico
(tests/conftest.py — «i test non dovrebbero dipendere dal modello reale») e una
fixture autouse ridefinisce il data dir. Dalla shell, col modello vero, lo
stesso comando trova il fatto a 0.90 e stampa `moat 94.5`; dentro pytest sarebbe
stato un test che misura il retrieval stubbato invece della formattazione.
Verificato prima di riscriverlo, cosi' il rosso non e' passato per un difetto
del prodotto.
"""
from __future__ import annotations

import re

import pytest

from verimem.cli import riga_di_recall

_ANSI_MARKUP = re.compile(r"\[/?[a-z ]+\]")
FATTO = "Il servizio di fatturazione ascolta sulla porta 8443."


def _piano(riga: str) -> str:
    """Via il markup rich, resta il testo che l'utente legge."""
    return _ANSI_MARKUP.sub("", riga)


def test_la_riga_porta_il_verdetto():
    r = _piano(riga_di_recall({"text": FATTO, "score": 0.9,
                               "grounding_score": 94.5}))
    assert "8443" in r
    assert "94.5" in r, r


def test_la_somiglianza_resta():
    """Si affianca, non sostituisce: i due numeri rispondono a domande
    diverse."""
    r = _piano(riga_di_recall({"text": FATTO, "score": 0.9,
                               "grounding_score": 94.5}))
    assert "0.90" in r, r


def test_un_fatto_mai_giudicato_lo_dice_senza_fingere_uno_zero():
    r = _piano(riga_di_recall({"text": FATTO, "score": 0.9,
                               "grounding_score": None}))
    assert "moat --" in r, r
    assert "0.0" not in r.replace("0.90", ""), r


def test_un_punteggio_basso_non_si_confonde_con_uno_alto():
    """Il colore cambia sotto la soglia, ma il numero c'e' comunque: un
    verdetto basso e' un'informazione, non qualcosa da nascondere."""
    basso = riga_di_recall({"text": FATTO, "score": 0.9, "grounding_score": 12.0})
    alto = riga_di_recall({"text": FATTO, "score": 0.9, "grounding_score": 95.0})
    assert "12.0" in _piano(basso) and "95.0" in _piano(alto)
    assert basso != alto


@pytest.mark.parametrize("hit", [
    {"text": FATTO, "score": None, "grounding_score": 94.5},
    {"text": FATTO},
    "una stringa e non un dict",
])
def test_non_si_rompe_su_una_riga_incompleta(hit):
    """Una lettura non deve mai cadere per come e' fatto un hit."""
    assert isinstance(riga_di_recall(hit), str)
# --- la versione superata si riconosce (T56, cella 2) -----------------------


def test_una_versione_superata_lo_dice_e_nomina_chi_la_sostituisce():
    """Chiedendo anche i superati arrivano DUE risposte alla stessa domanda:
    senza un segno, chi legge ha due valori e nessun ordine.

    Il campo esisteva gia' nel dizionario dell'SDK (`_fact_view` porta
    `superseded_by`, `None` quando il fatto e' vivo); a mancare era la riga
    che l'utente legge. Si pretende il segno E l'id del successore: senza
    l'id il segno dice «questa e' vecchia» e non «ecco quella nuova».
    """
    r = _piano(riga_di_recall({"text": FATTO, "score": 0.9,
                               "grounding_score": 94.5,
                               "superseded_by": "a8b1b7d03471cafe"}))
    assert "superseded by" in r, r
    assert "a8b1b7d0" in r, r
    assert "8443" in r, "il fatto deve restare leggibile: " + r


def test_CONTROLLO_un_fatto_VIVO_non_porta_quel_segno():
    """⚠️ IL NEGATIVO, senza il quale il test sopra passerebbe anche con un
    segno stampato SEMPRE — e la riga di tutti i giorni direbbe a ogni
    risposta che e' superata. `superseded_by` e' presente e vale `None` sui
    fatti vivi: e' `None` che deve restare muto, non l'assenza della chiave.
    """
    vivo = _piano(riga_di_recall({"text": FATTO, "score": 0.9,
                                  "grounding_score": 94.5,
                                  "superseded_by": None}))
    assert "superseded" not in vivo, vivo
    senza_chiave = _piano(riga_di_recall({"text": FATTO, "score": 0.9,
                                          "grounding_score": 94.5}))
    assert "superseded" not in senza_chiave, senza_chiave
