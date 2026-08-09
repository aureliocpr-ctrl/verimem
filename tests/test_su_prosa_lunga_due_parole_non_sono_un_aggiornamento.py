"""La guardia dell'evoluzione era misurata su frasi corte, e il corpus è prosa.

`_puo_essere_una_evoluzione` decide se un fatto nuovo può essere
l'aggiornamento di uno vecchio — cioè se il vecchio va RITIRATO. Il suo
docstring racconta perché esiste, e la misura che la motivò: dieci fatti veri e
scorrelati scritti dall'SDK, «sei ritirati su dieci, a catena — ogni fatto che
porta un numero mangiava il precedente». Il criterio scelto fu il numero di
parole di contenuto condivise, misurato su dodici coppie::

    sei finte (ritirate davvero) -> 0 parole condivise, tutte e sei
    sei evoluzioni legittime     -> da 3 a 5 parole condivise, tutte e sei

Fra 0 e 3 la soglia `>= 2` sta comoda. Ma quelle dodici coppie sono FRASI
CORTE, e il corpus vero è fatto di prosa: due handoff da 800 caratteri
condividono due parole per caso, non perché parlino della stessa cosa.

MISURATO sul corpus vero, campione di 200 fatti::

    prosa lunga (>400 char)   4005 coppie   1830 «può essere evoluzione» (45.7%)
                              quota condivisa: mediana 0.0588
    frasi corte (<=200 char)   528 coppie     94 «può essere evoluzione» (17.8%)
                              quota condivisa: mediana 0.8000

Quasi una coppia di prose su due passa la guardia, condividendo il 5.9% delle
proprie parole. Un ordine di grandezza sotto le frasi corte, per cui il
criterio era stato tarato: là la guardia protegge, qui è di fatto spenta.

LA SOGLIA NON È NUOVA. Le evoluzioni che i test presidiano — «Il corpus
contiene 6682 fatti» / «A gennaio il corpus conteneva 6000» — stanno a quota
0.667 e 1.000. Il rapporto 0.15 già in `quantity_match._shared_enough`
(misurato stamattina su un'altra superficie della stessa famiglia) sta in mezzo
con margine ampio da entrambi i lati, quindi si RIUSA quella invece di
introdurre una terza soglia: una superficie sola, una env sola.

Il conteggio `>= 2` resta accanto al rapporto e non viene sostituito: sulle
frasi corte è lui a fare il lavoro, ed è misurato.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import _puo_essere_una_evoluzione

#: Due prose PRESE DAL CORPUS VERO, accorciate senza toccare le parole che
#: contano. Condividono «reale» e «strutturale» su decine di termini — quota
#: 0.0260 — e il prodotto le dichiara l'una aggiornamento dell'altra.
#:
#: La prima stesura di questo file usava due prose INVENTATE da me, e non
#: riproduceva niente: condividevano ZERO parole, quindi la guardia le
#: rifiutava già e il test passava prima della cura. Un banco inventato mente
#: sul difetto che dovrebbe mostrare.
PROSA_A = (
    "quantity_match shared core piu' batch numeric-conflict scan shipped: "
    "win corpus-rilevante sull'ancora dei numeri isolati in extract, "
    "misurato sul corpus reale con la cura strutturale del gate lessicale "
    "e la suite riportata dal file."
)
PROSA_B = (
    "Continuous-thinker, architettura concreta: substrato a spazio di stati "
    "con dinamiche temporali native invece dei token discreti, un reale "
    "cambio strutturale del ciclo di inferenza, con la memoria di lavoro "
    "tenuta fuori dal contesto."
)

#: Le evoluzioni legittime che i test presidiano già altrove: quota 0.667-1.000.
EVOLUZIONI_VERE = [
    ("Il corpus contiene 6682 fatti.", "A gennaio il corpus conteneva 6000 fatti."),
    ("Il prezzo del piano annuale e 200 euro.", "Il prezzo e 100 euro."),
]


def test_due_prose_lunghe_non_si_aggiornano_a_vicenda():
    assert _puo_essere_una_evoluzione(PROSA_A, PROSA_B) is False, (
        "due prose che condividono una manciata di parole su decine sono "
        "trattate come aggiornamento l'una dell'altra: il vecchio viene "
        "RITIRATO")


@pytest.mark.parametrize("nuovo,vecchio", EVOLUZIONI_VERE)
def test_le_evoluzioni_vere_restano(nuovo, vecchio):
    assert _puo_essere_una_evoluzione(nuovo, vecchio) is True, (
        "un aggiornamento legittimo non è più riconosciuto: il prodotto "
        "terrebbe due valori in contesa invece di ritirare quello vecchio")


def test_le_frasi_corte_non_si_muovono():
    """Il criterio del CONTEGGIO resta quello che lavora sulle frasi corte,
    dove è stato misurato: due misure di soggetti diversi restano distinte."""
    assert _puo_essere_una_evoluzione(
        "Il corpus contiene 6682 fatti.",
        "La quarantena trattiene 528 fatti.") is False


def test_la_stessa_env_governa_le_due_superfici(monkeypatch):
    """Una soglia sola per la famiglia: spegnerla riporta al comportamento di
    prima QUI come sul percorso numerico."""
    monkeypatch.setenv("ENGRAM_CONFLICT_MIN_SHARED_RATIO", "0")
    assert _puo_essere_una_evoluzione(PROSA_A, PROSA_B) is True
