"""Una frase resta la stessa frase anche senza il punto finale.

Trovati dall'altra istanza il 2026-07-31, verificando i miei commit da
avversaria (F23 e F24 del suo registro):

    F23  «Il linguaggio principale è Rust»   (senza punto)  -> None
         «Il linguaggio principale è Rust.»  (col punto)    -> parsata

    F24  «Il linguaggio è Rust e il database è Postgres.»
         -> oggetto 'rust e il database è postgres' invece di None

Il primo conta perche' `_copula_parse` e `subject_key` alimentano CINQUE
moduli — composer, guardian (il rilevatore di contraddizioni), active_probe,
source_trust, ignorance_map — e un fatto che il parser non vede non entra MAI
in nessun confronto. Due fatti contraddittori scritti senza punto finale
coesistono senza che nessuno dichiari la contesa. E nessuno scrive col punto
per abitudine: e' proprio quello che ha reso divergenti le nostre due prove
(«le mie frasi erano senza punto, le tue col punto»).

Il punto finale NON era una mia scelta: c'era gia' prima della copula
multilingua (`4a282db4^` ha lo stesso `\\s*\\.$`). Ereditato, e curato qui.

Il secondo e' il rovescio: una frase con DUE copule non e' una «clean copula
sentence» e non va parsata a meta'. Prendendone una a caso si ottiene un
oggetto che non e' l'oggetto di nessuna delle due proposizioni — inerte
finche' nessun rivale gli somiglia, ma e' un dato inventato, e questo prodotto
esiste per non inventarne.
"""
from __future__ import annotations

import pytest

from verimem.composer import _copula_parse


@pytest.mark.parametrize("frase", [
    "Il linguaggio principale è Rust",
    "Il linguaggio principale è Rust.",
    "The main language is Rust",
    "The main language is Rust.",
    "Le langage principal est Rust",
    "El lenguaje principal es Rust",
])
def test_il_punto_finale_non_cambia_cio_che_la_frase_dice(frase):
    r = _copula_parse(frase)
    assert r is not None, f"non parsata: {frase!r}"
    assert "rust" in r[1].lower(), r


def test_col_punto_e_senza_danno_LO_STESSO_soggetto():
    """Se le due forme dessero soggetti diversi, il guardian confronterebbe
    fatti che parlano della stessa cosa come se parlassero di cose diverse."""
    a = _copula_parse("Il linguaggio principale è Rust")
    b = _copula_parse("Il linguaggio principale è Rust.")
    assert a == b, (a, b)


def test_una_frase_con_DUE_copule_non_si_parsa_a_meta():
    """F24: prenderne una a caso produce un oggetto che non appartiene a
    nessuna delle due proposizioni."""
    r = _copula_parse("Il linguaggio è Rust e il database è Postgres.")
    assert r is None, (
        f"frase composta parsata come proposizione singola: {r!r} — "
        f"quell'oggetto non e' l'oggetto di nessuna delle due")


def test_le_frasi_che_NON_sono_copule_restano_fuori():
    """Il presidio dell'altra direzione: allargare il criterio non deve far
    entrare tutto. Senza questo, «punto opzionale» diventerebbe «qualunque
    testo con un verbo in mezzo»."""
    for frase in ("Rust", "", "   ", "Il linguaggio principale",
                  "Se il linguaggio è Rust allora compila",
                  "Il linguaggio è"):
        assert _copula_parse(frase) is None, frase


def test_l_interrogativa_non_e_un_asserzione():
    """«Il linguaggio principale è Rust?» chiede, non afferma: trattarla come
    un fatto la metterebbe in contesa con i fatti veri."""
    assert _copula_parse("Il linguaggio principale è Rust?") is None
