"""L'apostrofo di Word non era un apostrofo.

Il regex della copula conosce solo `U+0027`, l'apostrofo dritto della
tastiera. Word, macOS, iOS e ogni editor con l'autocorrezione producono
`U+2019` — la virgoletta singola destra — quindi il testo scritto da una
PERSONA e quello scritto in un editor di codice si comportano in modo diverso.
Misurato:

    Il senatore è Dell'Utri.        dritto -> ('il senatore', "dell'utri")
    Il senatore è Dell’Utri.        curvo  -> None
    Il gatto è l'animale preferito. dritto -> ('il gatto', "l'animale preferito")
    Il gatto è l’animale preferito. curvo  -> None

Si perde il cognome appena curato E una classe vera.

E C'E' UN DANNO PIU' SOTTILE DELLA PERDITA. `subject_key` e' «la UNICA
definizione di stesso soggetto» per il guardian e per la contro-evidenza:
senza normalizzare, «Dell'Utri» col dritto e «Dell’Utri» col curvo sono due
soggetti DIVERSI, e due fatti che parlano della stessa persona non finiscono
mai in contesa. Basta che un fatto arrivi incollato da un documento e l'altro
digitato a mano.

La normalizzazione tocca solo gli APOSTROFI, non le virgolette doppie: qui
serve che una parola elisa resti una parola, non ripulire la punteggiatura.
"""
from __future__ import annotations

import pytest

from verimem.composer import _copula_parse, subject_key

DRITTO = "'"
VARIANTI = ["’", "‘", "ʼ", "´"]


@pytest.mark.parametrize("apo", VARIANTI, ids=["U+2019", "U+2018", "U+02BC", "U+00B4"])
def test_un_cognome_eliso_si_parsa_con_ogni_apostrofo(apo):
    atteso = _copula_parse(f"Il senatore è Dell{DRITTO}Utri.")
    assert atteso is not None, "presupposto: col dritto funziona"
    assert _copula_parse(f"Il senatore è Dell{apo}Utri.") == atteso


@pytest.mark.parametrize("apo", VARIANTI, ids=["U+2019", "U+2018", "U+02BC", "U+00B4"])
def test_una_classe_vera_si_parsa_con_ogni_apostrofo(apo):
    atteso = _copula_parse(f"Il gatto è l{DRITTO}animale preferito.")
    assert atteso is not None, "presupposto: col dritto funziona"
    assert _copula_parse(f"Il gatto è l{apo}animale preferito.") == atteso


@pytest.mark.parametrize("apo", VARIANTI, ids=["U+2019", "U+2018", "U+02BC", "U+00B4"])
def test_lo_stesso_soggetto_ha_UNA_chiave(apo):
    """Il danno che non si vede: due grafie, due chiavi, nessuna contesa."""
    assert subject_key(f"Dell{apo}Utri") == subject_key(f"Dell{DRITTO}Utri")


@pytest.mark.parametrize("apo", VARIANTI, ids=["U+2019", "U+2018", "U+02BC", "U+00B4"])
def test_il_locativo_eliso_resta_respinto_con_ogni_apostrofo(apo):
    """La guardia sulle preposizioni non deve aprirsi sulla grafia nuova."""
    assert _copula_parse(f"Il documento è nell{apo}archivio.") is None


def test_le_virgolette_doppie_non_sono_toccate():
    """Si normalizzano gli APOSTROFI, non la punteggiatura: una frase con le
    virgolette curve non deve cambiare comportamento per colpa di questa
    cura."""
    a = _copula_parse('Il libro è "un classico".')
    b = _copula_parse("Il libro è “un classico”.")
    assert a == b
