"""Tagliare a N caratteri mutila le lingue che compongono i segni.

Mandato di Aurelio del 2026-08-07, verbatim: «verimem non deve essere solo
in italiano, ma deve funzionare IMPECCABILMENTE su tutte le lingue».
Assegnazione a ws7: **che le superfici mostrino i caratteri non-latini
senza mutilarli — un accento perso in una UI è un dato perso.**

Misurato prima di scrivere, tagliando dove la sequenza si spezza:

    'caffé macchiato'[:5]   ->  'caffe'      ⚠️ l'accento sparisce
    'नमस्ते deposito'[:3]    ->  'नमस'        ⚠️ perde il virama: altra parola
    'deposito 🇮🇹 pieno'[:10] ->  'deposito 🇮'  ⚠️ mezza bandiera
    'operatore 👩‍💻'[:12]     ->  'operatore 👩\\u200d'  ⚠️ ZWJ penzolante

⚠️ **E il presidio che ws3 chiede vale doppio qui: il primo caso è
ITALIANO.** Il difetto non è «delle altre lingue» — è del taglio, e in
italiano si vede meno solo perché le nostre vocali accentate arrivano
quasi sempre già composte. Se avessi misurato solo hindi avrei consegnato
«difetto delle lingue indiane», che è falso.

La regola: **non emettere mai un grafema mutilato**. Meglio un carattere
in meno che una parola diversa — e `caffe` al posto di `caffé` è una
parola diversa per chi legge, e per chiunque cerchi quella stringa.
"""
from __future__ import annotations

import unicodedata as _ud

import pytest

from verimem.text_cut import safe_cut

#: COSTRUITA ESPLICITAMENTE, non battuta come letterale. La prima stesura
#: di questo banco scriveva la lettera accentata nel file: Python l'ha
#: salvata PRECOMPOSTA (un solo code point), quindi il taglio non spezzava
#: niente e il test passava SENZA MISURARE NULLA. La stessa lettera, in una
#: fonte che la compone, e' DUE caratteri (base + segno).
#: 🔑 E' la trappola vera del mandato multilingua: lo stesso testo, a schermo
#: identico, arriva in due codifiche — e il difetto vive solo in una.
_ACCENTO = _ud.normalize("NFD", "caffé macchiato")
_DEVA = "नमस्ते deposito"  # नमस्ते
_BANDIERA = "deposito \U0001F1EE\U0001F1F9 pieno"        # 🇮🇹
_ZWJ = "operatore \U0001F469‍\U0001F4BB attivo"     # 👩‍💻


def test_non_stacca_un_accento_dalla_sua_lettera():
    """Il caso italiano, che è anche il più insidioso: il taglio cade fra
    la `e` e il suo accento, e la stringa esce con una parola diversa."""
    assert safe_cut(_ACCENTO, 5) == "caff"
    assert safe_cut(_ACCENTO, 6) == _ACCENTO[:6]


def test_non_spezza_una_sillaba_devanagari():
    """Perdere il virama non accorcia la parola: la cambia."""
    fuori = safe_cut(_DEVA, 3)
    assert not fuori.endswith("स"), fuori
    assert len(fuori) <= 3


def test_non_lascia_mezza_bandiera():
    """Un indicatore regionale da solo si vede come una lettera in un
    riquadro: un simbolo che non esiste al posto di uno che esisteva."""
    fuori = safe_cut(_BANDIERA, 10)
    assert fuori == "deposito ", repr(fuori)


def test_non_lascia_uno_ZWJ_penzolante():
    """Un giuntore senza il pezzo che unisce è un carattere invisibile che
    viaggia nel dato e rompe i confronti."""
    for n in (11, 12):
        assert "‍" not in safe_cut(_ZWJ, n), n


def test_l_ITALIANO_e_l_inglese_NON_cambiano():
    """Il presidio che chiede ws3: la stessa misura in italiano. Se la
    cura cambiasse il testo latino avrei curato una lingua rompendone
    un'altra."""
    for s in ("Il magazzino di Città Sant'Angelo", "The depot in Milan"):
        for n in (5, 12, 20, 100):
            assert safe_cut(s, n) == s[:n], (s, n)


def test_il_cinese_non_cambia_perche_non_compone():
    """Controprova: dove non ci sono segni combinanti il taglio resta
    quello di prima. Una cura che tocca anche ciò che non c'entra è una
    cura che nessuno può verificare."""
    s = "仓库在北京有三百个货架"
    for n in (3, 7, 11, 50):
        assert safe_cut(s, n) == s[:n]


def test_un_taglio_piu_lungo_del_testo_rende_il_testo():
    assert safe_cut("breve", 100) == "breve"
    assert safe_cut("", 5) == ""
