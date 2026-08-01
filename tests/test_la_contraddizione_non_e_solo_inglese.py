"""Due fatti che si contraddicono in italiano si contraddicono lo stesso.

TROVATO il 2026-07-30 dal dogfooding in parallelo, che aveva osservato: due
write opposti («Il linguaggio principale di AcmeApp e' Rust» / «e' Go»),
entrambi con la loro fonte e moat alto, e nessuna superficie del percorso utente
dichiara la contesa. Riprodotto su store isolato, e la causa e' precisa:

    _copula_parse("Il linguaggio principale di AcmeApp e' Rust.")  -> None
    _copula_parse("AcmeApp's main language is Rust.")              -> parsato

``_COPULA_RE`` e' ``\\s+is\\s+``: inglese e basta. Il prodotto dichiara e
MISURA il proprio giudice su EN/IT/FR/ES (il commento in anti_confab_gate lo
ripete: «the CE is multilingual — measured EN/IT/FR/ES»), ma l'identita' del
soggetto — quella che decide se due fatti parlano della stessa cosa — vive in
un regex monolingue.

Non e' un dettaglio di una funzione: ``_copula_parse`` e ``subject_key``
alimentano CINQUE moduli, fra cui il ``guardian`` che rileva le contraddizioni e
``active_probe`` che cerca la contro-evidenza. In italiano quei meccanismi non
hanno mai avuto niente da confrontare.

LA TRAPPOLA, che questo file prova per prima: «a» e' ARTICOLO in inglese
(«is a labrador») e PREPOSIZIONE in italiano («e' a Roma»). Mettere le due
liste nello stesso insieme fa perdere l'oggetto in inglese o accettare un
locativo in italiano. La lingua si decide dalla COPULA incontrata, e ogni lingua
porta i suoi articoli e le sue preposizioni.
"""
from __future__ import annotations

import pytest

from verimem.composer import _copula_parse, subject_key


def test_l_italiano_viene_parsato():
    """Il caso esatto del dogfooding."""
    r = _copula_parse("Il linguaggio principale di AcmeApp e' Rust.")
    assert r is not None, "la copula italiana non viene riconosciuta"
    assert r[1] == "rust", r


def test_anche_con_l_accento_vero():
    """`e'` e `è` sono la stessa parola: chi scrive dall'editor usa l'accento."""
    r = _copula_parse("Il linguaggio principale di AcmeApp è Rust.")
    assert r is not None and r[1] == "rust", r


def test_due_fatti_opposti_hanno_LO_STESSO_soggetto():
    """E' questo che serve al guardian: se i soggetti non coincidono, i due
    fatti non sono rivali e la contesa non viene mai dichiarata."""
    a = _copula_parse("Il linguaggio principale di AcmeApp è Rust.")
    b = _copula_parse("Il linguaggio principale di AcmeApp è Go.")
    assert a and b
    assert subject_key(a[0]) == subject_key(b[0]), (a[0], b[0])
    assert a[1] != b[1], "i due oggetti devono restare distinti"


def test_l_articolo_italiano_viene_tolto_come_quello_inglese():
    a = _copula_parse("Il gatto è un mammifero.")
    b = _copula_parse("The cat is a mammal.")
    assert a and b
    assert a[1] == "mammifero" and b[1] == "mammal", (a, b)


@pytest.mark.parametrize("frase,atteso", [
    ("Le langage principal d'AcmeApp est Rust.", "rust"),
    ("El lenguaje principal de AcmeApp es Rust.", "rust"),
])
def test_francese_e_spagnolo(frase, atteso):
    """Le quattro lingue su cui il giudice del moat e' misurato."""
    r = _copula_parse(frase)
    assert r is not None and r[1] == atteso, r


def test_LA_TRAPPOLA_a_e_articolo_in_inglese_e_preposizione_in_italiano():
    """Se le liste si mescolano, una delle due lingue si rompe in silenzio."""
    inglese = _copula_parse("Rex is a labrador.")
    assert inglese is not None and inglese[1] == "labrador", (
        "«a» inglese e' un articolo: l'oggetto non deve sparire")
    italiano = _copula_parse("Rex è a Roma.")
    assert italiano is None, (
        "«a» italiano e' una preposizione: «è a Roma» e' un locativo, non una "
        f"classe — non deve produrre un soggetto rivale. Ottenuto: {italiano}")


def test_l_inglese_non_cambia_di_una_virgola():
    """La cura non deve spostare il comportamento su cui gira tutto il corpus."""
    assert _copula_parse("Rex is a labrador.") == ("rex", "labrador", "a labrador")
    assert _copula_parse("Rex is in Rome.") is None
    assert _copula_parse("Rex is the.") is None
    assert _copula_parse("not a copula at all") is None


def test_il_locativo_e_scartato_in_ogni_lingua():
    for frase in ("Il server è in Germania.", "Le serveur est en Allemagne.",
                  "El servidor es de Alemania."):
        assert _copula_parse(frase) is None, frase
