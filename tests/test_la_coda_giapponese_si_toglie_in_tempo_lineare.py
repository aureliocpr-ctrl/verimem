r"""T170 — dodici secondi per normalizzare UNA parola.

`_senza_coda_verbale_giapponese` toglie la coda hiragana con
`re.compile(r"[ぁ-ゟ]+$").sub("", w)`. Su una parola fatta di molti hiragana
che NON finisce in hiragana, quel `+$` costringe il motore a ripartire da ogni
posizione: costo quadratico, e su 40 000 caratteri sono **12 432,8 ms**.

    una parola di 40 000 hiragana seguita da un katakana:
      .sub()    12 432,8 ms
      rstrip         0,0 ms

L'HA SEGNALATO CodeQL (alert 1491, `py/polynomial-redos`, 19/09) e **il
percorso che ci porta il testo dell'utente l'ho aperto io**: la cura di T105 ha
aggiunto `norm_unit(dopo_m.group(1))`, e `norm_unit` chiama questa funzione. La
regex è più vecchia (commit 66583acc), la strada no.

LA CURA È `str.rstrip`, che in Python è **lineare**: toglie dalla coda tutti i
caratteri che stanno nell'insieme, senza backtracking. Fa esattamente la stessa
cosa — questo banco lo verifica sui nove casi del presidio giapponese, contatori
compresi, perché una cura che «va più veloce» cambiando il risultato è un
difetto nuovo con un buon cronometro.
"""
from __future__ import annotations

import time

import pytest

from verimem.quantity_match import _senza_coda_verbale_giapponese, norm_unit

#: I nove del presidio, dal docstring della funzione: cinque code verbali da
#: togliere e quattro unita' hiragana che devono restare INTERE (`つ` e' il
#: contatore generico, `まい` conta i fogli, `ぴき` gli animali piccoli).
CASI = [
    ("ミリグラム含まれています", "ミリグラム含"),
    ("ミリグラムです", "ミリグラム"),
    ("キロ", "キロ"),
    ("400", "400"),
    ("metri", "metri"),
    ("つ", "つ"),
    ("まい", "まい"),
    ("ぴき", "ぴき"),
    ("ひとつ", "ひとつ"),
]


@pytest.mark.parametrize("dentro,fuori", CASI)
def test_EQUIVALENZA_la_cura_non_cambia_nemmeno_un_caso(dentro: str, fuori: str):
    """Il controllo positivo che viene PRIMA del cronometro: se cambia un solo
    esito, la cura non e' una cura — e i quattro contatori hiragana sono
    esattamente la popolazione che il presidio del giapponese difende."""
    assert _senza_coda_verbale_giapponese(dentro) == fuori


def test_IL_TEMPO_una_parola_lunga_non_costa_dodici_secondi():
    """⏱️ IL CUORE. Misurato prima della cura: 12 432,8 ms.

    La soglia è 50 ms, cioè **duecentoquaranta volte** sotto il valore
    rosso e ben sopra qualunque oscillazione di macchina: fra i due regimi non
    c'e' una sfumatura, c'e' un ordine di grandezza.
    """
    parola = "x" + "ぁ" * 40000 + "ア"
    inizio = time.perf_counter()
    _senza_coda_verbale_giapponese(parola)
    trascorso_ms = 1000 * (time.perf_counter() - inizio)
    assert trascorso_ms < 50, (
        f"normalizzare una parola di 40 000 hiragana costa {trascorso_ms:.1f} ms: "
        "il backtracking della regex e' tornato")


def test_IL_TEMPO_vale_anche_dalla_porta_pubblica_del_modulo():
    """`norm_unit` e' la funzione che il resto del prodotto chiama davvero, ed
    e' da li' che il testo dell'utente arriva alla regex. Misurare solo la
    funzione interna proverebbe la cura e non il percorso."""
    parola = "ぁ" * 20000 + "ア"
    inizio = time.perf_counter()
    norm_unit(parola)
    trascorso_ms = 1000 * (time.perf_counter() - inizio)
    assert trascorso_ms < 50, (
        f"norm_unit su una parola di 20 000 hiragana costa {trascorso_ms:.1f} ms")


def test_CONTROLLO_NEGATIVO_una_parola_normale_resta_normale():
    """Senza, una cura che rende «» a tutto passerebbe tempo e equivalenza.

    ⚠️ `metri` diventa `metro`, non `m`: questa funzione singolarizza, non
    traduce in sigla. L'attesa sbagliata era mia e l'ha presa il RED — un'altra
    aspettativa scritta a memoria invece che letta dal prodotto.
    """
    assert norm_unit("metri") == "metro"
    assert norm_unit("") == ""
    assert _senza_coda_verbale_giapponese("") == ""
