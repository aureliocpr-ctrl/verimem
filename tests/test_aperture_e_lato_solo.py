"""La prima parola della frase non deve decidere se due fatti si mangiano.

Questi test chiamano `_entita_diverse`, che decide col LESSICO
(`extract_entities_lite`) e non col coseno: lo stub dell'embedder di
`conftest.py` non li tocca, quindi qui pytest misura il prodotto e non il
proprio righello. La meta' che scrive davvero sta nel banco fuori da pytest,
`docs/stato-reale/banchi/ws3-aperture-e-lato-solo.py`.

Portata sul corpus di produzione (1933 supersessioni reali, A/B su due alberi):
27 ritiri non avvengono piu' — 26 fra fatti che il giudice sostiene entrambi a
>=90 — contro 1 che inizia ad avvenire, sul quale il fatto ritirato ha
grounding 0.17.
"""
import types

import pytest

from verimem.anti_confab_gate import _entita_diverse

_CODA = " la cella ha stampato 1 failed"


def _f(p):
    return types.SimpleNamespace(proposition=p)


@pytest.mark.parametrize("apertura", [
    # italiano: preposizioni semplici e articolate che aprono la frase
    "Su", "In", "Di", "Da", "Tra", "Nel", "Alla", "Dal",
    # inglese: la lingua in cui il prodotto e' documentato
    "On", "At", "By", "To", "Of", "From", "With",
    # i controlli: aperture che gia' funzionavano, e devono continuare
    "Il run", "The run",
])
def test_l_apertura_non_fa_mangiare_due_record_diversi(apertura):
    """A/B a variabile singola: cambia SOLO la parola d'apertura.

    Prima della cura ne cadevano 10 su 14, e non era un difetto italiano:
    `On`/`At`/`By`/`To`/`Of` cadevano come `Su`/`In`/`Di`/`Da`/`Tra`.
    """
    a = _f(apertura + " 42bb3839" + _CODA)
    b = _f(apertura + " b7bc7b77" + _CODA)
    assert _entita_diverse(a, b), (
        f"due fatti su record diversi si ritirano a vicenda perche' la "
        f"frase si apre con {apertura!r}")


@pytest.mark.parametrize("pa,pb", [
    # il fatto che ws7 ha perso: due colonne di una matrice, non due valori
    ("La cella stampa 1 failed e 11767 passed.",
     "Su b7bc7b77 la cella py3.13 stampa 8019 warnings."),
    # i due regimi che questo progetto tiene per la distinzione piu' importante
    ("Sotto pytest la domanda in olandese ottiene score 0.7006.",
     "Fuori da pytest la domanda in olandese ottiene score 0.8509."),
    ("Nel corpus i fatti live non quarantinati sono 4304.",
     "Il tool hippo_extract_entities sul testo di Aurelio rende 3 entita."),
])
def test_un_lato_solo_che_nomina_il_record_non_autorizza_il_ritiro(pa, pb):
    """Un lato vuoto e' il caso in cui si sa MENO, non abbastanza per ritirare.

    Il chiamante legge `False` come «nessun motivo di fermarsi»: un NON SO
    letto come un SI'. La scelta non e' simmetrica — ritirare per errore toglie
    un fatto vero dal recall, non ritirare lascia vivere un duplicato.
    """
    assert _entita_diverse(_f(pa), _f(pb))


@pytest.mark.parametrize("pa,pb", [
    ("Su 42bb3839 la cella ha stampato 1 failed",
     "Su 42bb3839 la cella ha stampato 3 failed"),
    ("On 42bb3839 the cell printed 1 failed",
     "On 42bb3839 the cell printed 3 failed"),
    ("Su 42bb3839 la versione e' 2.3.1", "Su 42bb3839 la versione e' 4.0.0"),
    ("Il piano costa 100 euro", "Il piano costa 150 euro"),
])
def test_presidio_lo_stesso_record_continua_ad_aggiornarsi(pa, pb):
    """La meta' obbligatoria: una cura che allarga le parole vuote potrebbe
    spegnere l'evoluzione dei fatti, ed e' il danno peggiore dei due."""
    assert not _entita_diverse(_f(pa), _f(pb)), (
        "l'aggiornamento di uno STESSO record ha smesso di superseder")
