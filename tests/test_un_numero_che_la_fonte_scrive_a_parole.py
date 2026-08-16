"""La fonte scrive «SEI», il claim scrive «6», e il gate perdeva un fatto VERO.

Misurato il 16/08 da ws8 usando il prodotto — tre casi con
`withheld_despite_judge=True` e grounding 99,3–99,9: il layer tratteneva mentre
il giudice era contento. La causa, misurata alla porta::

    extract_quantities('La CI prova SEI combinazioni su dodici promesse.')  -> []
    extract_quantities('La CI prova 6 combinazioni su 12 promesse.')        -> [6.0, 12.0]

⇒ La fonte a parole risulta priva di quantità, quindi il valore del claim
«non c'è nella fonte» e L4.1 lo ferma.

═══ DOVE VA LA CURA — lo dichiara il modulo, e non è nel parser ═══

`valore_non_nella_fonte.py:228` ha già deciso questa domanda per un caso
gemello («nessun X» vale zero)::

    «Insegnare al parser che "nessun X" vale 0 creerebbe quantità dove il testo
     non ne misura nessuna […] e quelle quantità fantasma finirebbero nei sei
     moduli del gate che leggono extract_quantities […] Qui invece
     l'equivalenza vive solo nel confronto fra claim e fonte: non entra nel
     corpus e non crea nulla.»

⇒ Stessa scelta qui: **l'equivalenza cifra↔parola vive nel confronto**, non nel
parser.

═══ PERCHÉ AVVISA INVECE DI AMMETTERE IN SILENZIO ═══

Per «nessun X» l'equivalenza è certa. Qui **non lo è**: «sei» è anche il verbo
essere, «venti» anche il plurale di vento. ⇒ Il valore non si aggiunge alla
fonte come se fosse scritto: si toglie dal VETO e si mette in un AVVISO, che è
la regola di casa scritta a `anti_confab_gate.py:1897` — «un avviso non ha
bisogno della popolazione opposta, un veto sì».

═══ QUALI PAROLE, E PERCHÉ QUESTE ═══

La partizione è per FREQUENZA e non per pericolosità, ed è una misura di ws8 sul
corpus reale (11.262 proposizioni)::

    un   1481 (13,2%)  una 772 (6,9%)  uno 193 (1,7%)  -> 21,8 punti: FUORI
    due   527 (4,7%)   tre 252 (2,2%)  one 240 (2,1%)  sei 162 (1,4%): DENTRO

⇒ Con la lista completa l'avviso sarebbe scattato su **2484 fatti su 11262
(22,1%)**, e «un avviso che compare sempre equivale a nessun avviso». Tolti i
tre articoli — che da soli valgono oltre l'80% degli scatti — l'avviso resta
raro e **«sei» rientra**, cioè cura il caso che ha originato tutto.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import valori_scritti_a_parole
from verimem.valore_non_nella_fonte import (
    assenti_che_la_fonte_scrive_a_parole,
    valori_non_nella_fonte,
)

FONTE_PAROLE = "La CI prova SEI combinazioni su dodici promesse."


def _assenti(claim: str, fonte: str = FONTE_PAROLE):
    return valori_non_nella_fonte(claim, fonte)


def _declassabili(claim: str, fonte: str = FONTE_PAROLE):
    return assenti_che_la_fonte_scrive_a_parole(_assenti(claim, fonte), fonte)


# --------------------------------------------------------------- il difetto --
def test_il_valore_che_la_fonte_scrive_a_parole_e_riconoscibile():
    """Resta fra gli «assenti» — la cifra nella fonte davvero non c'è — ma è
    riconosciuto come declassabile, così il gate lo sposta da veto ad avviso
    invece di far sparire il fatto."""
    assert [a for a in _declassabili("La CI prova 6 combinazioni.")
            if a.valore == 6.0], (
        "6 non è stato riconosciuto in una fonte che dice SEI: è il fatto vero "
        f"che si perde. Assenti: {[a.valore for a in _assenti('La CI prova 6 combinazioni.')]}")


def test_vale_anche_in_inglese():
    fonte = "The CI runs SIX combinations out of twelve promised."
    assert [a for a in _declassabili("The CI runs 6 combinations.", fonte)
            if a.valore == 6.0]


# ------------------------------------------------- LE POPOLAZIONI OPPOSTE ----
def test_un_numerale_nella_fonte_non_giustifica_un_valore_DIVERSO():
    """⚠️⚠️ IL PRESIDIO CHE DECIDE SE LA CURA VALE. Senza questo, «la fonte ha
    un numerale» diventerebbe un lasciapassare per qualunque cifra, e il layer
    smetterebbe di fare il suo mestiere."""
    assenti = _assenti("La CI prova 7 combinazioni.")
    assert [a for a in assenti if a.valore == 7.0], (
        "7 NON è nella fonte (che dice SEI e dodici) e deve restare un valore "
        f"assente. Assenti: {[(a.valore, a.unita) for a in assenti]}")
    assert not _declassabili("La CI prova 7 combinazioni."), (
        "7 è stato dichiarato declassabile: la fonte non lo scrive né in cifra "
        "né a parole, e il veto deve restare")


@pytest.mark.parametrize("frase,parola", [
    ("UNA configurazione è stata cambiata.", "una"),
    ("Ne resta UNA sola da misurare.", "una"),
    ("Ho corretto UN numero.", "un"),
    ("Ne ho aggiunto UNO solo.", "uno"),
])
def test_gli_articoli_non_portano_il_numero_uno(frase, parola):
    """⚠️ Misurato da ws8 sul corpus: `un/una/uno` valgono 21,8 punti su 26,5 —
    oltre l'80% degli scatti. Con dentro questi, l'avviso comparirebbe su un
    fatto su quattro e nessuno lo leggerebbe più."""
    assert 1.0 not in valori_scritti_a_parole(frase), (
        f"«{parola}» in «{frase}» è stato letto come il numero 1")


def test_i_numerali_veri_invece_si_leggono():
    """L'altra metà: se non leggesse più nulla, i test qui sopra passerebbero
    per il motivo sbagliato."""
    assert 6.0 in valori_scritti_a_parole(FONTE_PAROLE)
    assert 12.0 in valori_scritti_a_parole(FONTE_PAROLE)
    assert 6.0 in valori_scritti_a_parole("The CI runs SIX combinations.")


def test_il_banco_delle_frasi_difficili(subtests=None):
    """⚠️ Le frasi sono di ws8, misurate da lei il 16/08: otto su dodici hanno
    un numerale-parola che NON è un numero. Qui restano quelle il cui esito
    NON dipende dalla lista degli articoli — gli omonimi veri, che una cura
    per frequenza NON risolve e che restano il limite dichiarato di questa
    riga."""
    # Documentati come limite NOTO: la cura per frequenza non li distingue.
    assert 6.0 in valori_scritti_a_parole("Tu SEI la persona giusta.")
    assert 20.0 in valori_scritti_a_parole("I VENTI forti hanno abbattuto tutto.")
