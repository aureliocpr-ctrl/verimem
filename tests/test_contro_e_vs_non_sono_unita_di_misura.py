"""«120 vs 45» aveva unità «vs», e «sub 136 contro sub 10» aveva unità «contro».

IL DIFETTO, censito da ws1 sul mandato lingue («'a', 'vs', 'passed', 'produce'
sono trattate come unità di misura») e riprodotto::

    «il bench ha fatto 120 vs 45»          -> [('vs', 120.0), ('', 45.0)]
    «sub 136 contro sub 10»                -> [('contro', 136.0), ('', 10.0)]
    «il fatto 7453 verified contro 553»    -> [('verified', 7453.0), ('', 553.0)]

🔑 `vs` e `contro` sono **congiunzioni di confronto**: la parola che segue un
numero quando si mettono due numeri UNO ACCANTO ALL'ALTRO. Non c'è forma in cui
siano un'unità di misura — e sono proprio la forma in cui si scrive un
confronto, cioè il testo che questo store contiene di più.

⚠️ COSA COSTA: due numeri della STESSA frase prendono unità diverse — il primo
«vs», il secondo nessuna — e la frase si confronta con altre per un'unità che
non esiste. ws1 l'ha misurato: **28 conflitti su 30 sono fra topic diversi**, e
le unità che li generano sono `verified` (38022 contro 9622), `sub`, `fatto`.

📌 È LA CLASSE ②, e la lista giusta esiste già: `_NON_UNIT_WORDS` nasce
esattamente per questo — *«function words that can FOLLOW a number but are never
units ("30 and 45", "5 of 10")»* — e contiene già `and`, `or`, `to`, `of`. Le
congiunzioni di CONFRONTO non ci sono mai arrivate, e sono lo stesso identico
caso: «30 **and** 45» e «30 **vs** 45» hanno la stessa struttura.

⚠️ NON copro i PARTICIPI (`passed`, `verified`, `produce`), ed è una scelta: lì
la parola può davvero essere ciò che si conta («33 passed» sono 33 test
passati). Il difetto che ws1 misura su `verified` non è che la parola sia
sbagliata — è che due fatti di topic diversi si confrontino, e quella è la
guardia del soggetto, un'altra cura. Qui si chiude solo ciò che non è un'unità
in nessuna lettura.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities

#: Confronti: due numeri accostati da una congiunzione. Nessuno dei due ha unità.
CONFRONTI = [
    "il bench ha fatto 120 vs 45",
    "sub 136 contro sub 10",
    "la misura passa da 33 a 45",
    "il punteggio e' 120 contro 45",
    "the benchmark did 120 vs 45",
    "il valore oscilla fra 30 e 45",
]

#: ⚠️ LA POPOLAZIONE OPPOSTA: unità VERE che devono continuare a essere lette.
#: Senza, il test sopra è soddisfatto da un estrattore che non trova mai un'unità.
UNITA_VERE = [
    ("il magazzino contiene 300 pallet", "pallet"),
    ("la riunione e' durata 45 minuti", "minuto"),
    ("il contratto vale 4500 euro", "euro"),
    ("the warehouse holds 300 pallets", "pallet"),
    ("il file pesa 72 MB", "mb"),
]


@pytest.mark.parametrize("frase", CONFRONTI)
def test_una_congiunzione_di_confronto_non_e_una_unita(frase):
    """IL CUORE: in «120 vs 45» nessuno dei due numeri ha un'unità. Attribuirne
    una al primo fa sì che la frase si confronti con altre su una grandezza che
    non esiste."""
    unita = {u for u, _v in extract_quantities(frase) if u}
    assert not unita, f"«{frase}» produce unità {unita}"


@pytest.mark.parametrize("frase,attesa", UNITA_VERE)
def test_CONTROLLO_POSITIVO_le_unita_vere_restano(frase, attesa):
    """⚠️ IL PRESIDIO: se la cura togliesse anche le unità vere, il rilevamento
    dei conflitti numerici smetterebbe di funzionare — cioè spegnerei la
    funzione invece di curarla."""
    unita = {u for u, _v in extract_quantities(frase) if u}
    assert attesa in unita, f"«{frase}» ha perso l'unità: {unita}"


def test_LIMITE_DICHIARATO_i_participi_restano_scoperti():
    """⚠️ Il limite, misurato e scritto invece che nascosto: «33 passed» e
    «7453 verified» continuano a produrre un'unità, e non è un dimenticanza.

    Lì la parola può davvero essere ciò che si conta — 33 test *passati* — e il
    difetto che ws1 misura su `verified` (38022 contro 9622, topic diversi) non
    è che la parola sia sbagliata: è che due fatti di topic diversi si
    confrontino. Quella è la guardia del soggetto, ed è un'altra cura.
    """
    assert {u for u, _v in extract_quantities("la suite ha dato 33 passed") if u}
