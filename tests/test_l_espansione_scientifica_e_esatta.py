"""`123456789012345 x 10^3` non fa `123456789012344992`.

IL DIFETTO, misurato sul tronco il 21/09 — la cura del 20/09 che espande la
notazione scientifica passa da `float`, e sopra le 15 cifre significative il
prodotto **inventa un valore**::

    '123456789012345 x 10^3'  ->  '123456789012344992'
    float(123456789012345) * 1000 = 1.23456789012345e+17
    int esatto                    = 123456789012345000

⚠️ PERCHE' E' LA CLASSE PEGGIORE per questo prodotto, e non «un errorino di
arrotondamento»: il valore espanso entra nel confronto claim-fonte. Un valore
MANCANTE si nota — il layer accusa e chi legge va a guardare. Un valore
INVENTATO no: il confronto avviene contro un numero che nessuno ha scritto, e
l'esito (accusa o assoluzione) e' governato da una cifra che non esiste in
nessuno dei due testi.

RAGGIO, misurato PRIMA della cura su uno snapshot (27 080 testi): **zero**
occorrenze della forma `n x 10^e`, quindi zero con mantissa lunga. Il difetto e'
reale nel codice e non ha popolazione nei nostri dati — per questo e' un ticket
a parte e non e' stato infilato nella richiesta che cura un'altra riga dello
stesso modulo. Il controllo positivo del righello che ha prodotto lo zero si
accendeva sul caso costruito.

E LA SECONDA META' DEL TICKET E' UNA FRASE: il commento entrato in main con la
cura del ReDoS dichiara «i limiti coprono ogni numero reale (una mantissa di 15
cifre, un esponente di 4: `10^9999`)». Misurato: `1,5 x 10^9999` **non** viene
espanso — eccede il float e cade nel ripiego. Il comportamento e' sicuro, la
frase no, e una frase falsa in un commento sopravvive a chi l'ha scritta.
"""
from __future__ import annotations

import pytest

from verimem.valore_non_nella_fonte import _espandi_notazione_scientifica


@pytest.mark.parametrize("testo,atteso", [
    # IL RED: oggi da' '123456789012344992'
    ("Gli impulsi sono 123456789012345 x 10^3.",
     "Gli impulsi sono 123456789012345000."),
    # la mantissa con la virgola, sempre oltre il float
    ("La misura e' 1,23456789012345678 x 10^5 unita.",
     "La misura e' 123456.789012345678 unita."),
])
def test_l_espansione_NON_inventa_cifre(testo, atteso):
    """Il valore espanso deve essere quello scritto, cifra per cifra."""
    assert _espandi_notazione_scientifica(testo) == atteso


@pytest.mark.parametrize("testo,atteso", [
    ("Gli impulsi registrati sono 1,5 x 10^3.", "Gli impulsi registrati sono 1500."),
    ("Le particelle sono 2,5 x 10^5.", "Le particelle sono 250000."),
    ("Le iterazioni sono 6 x 10^4.", "Le iterazioni sono 60000."),
    ("Lo spessore e' 4 x 10^-4 metri.", "Lo spessore e' 0.0004 metri."),
])
def test_IL_CONTROLLO_POSITIVO_i_casi_reali_non_cambiano(testo, atteso):
    """I quattro casi del banco che la cura del 20/09 gia' copre: se uno di
    questi cambia, la cura nuova ha spostato il difetto invece di curarlo."""
    assert _espandi_notazione_scientifica(testo) == atteso


def test_UN_ESPONENTE_ENORME_NON_SI_ESPANDE_e_il_commento_ora_lo_dice():
    """⚠️ IL TETTO SUL RISULTATO, non sul float.

    Con l'aritmetica esatta `10^9999` si espanderebbe davvero — in un numero di
    diecimila cifre che finirebbe nel testo dato al confronto. Oggi non succede
    per un motivo accidentale (il float va in overflow e il ripiego restituisce
    il testo com'e'), e il commento in main lo raccontava al contrario.

    Con la cura il limite e' ESPLICITO e dichiarato: oltre una lunghezza
    ragionevole non si espande, e il testo resta quello scritto.
    """
    testo = "Il valore e' 1,5 x 10^9999 unita."
    assert _espandi_notazione_scientifica(testo) == testo, (
        "un esponente enorme ora si espande: il confronto riceverebbe un numero "
        "di migliaia di cifre")


def test_il_ripiego_resta_il_testo_INTATTO_quando_non_si_espande():
    """Il ripiego non e' «nessun numero»: e' il testo originale. Se un giorno
    diventasse una stringa vuota o un segnaposto, il claim perderebbe pezzi e il
    confronto lavorerebbe su una frase mutilata."""
    for testo in ("Il valore e' 12345678901234567890123456789012345678901234 x 10^9999.",
                  "Nessuna notazione qui: 1500 impulsi."):
        assert _espandi_notazione_scientifica(testo) == testo
