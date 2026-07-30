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
