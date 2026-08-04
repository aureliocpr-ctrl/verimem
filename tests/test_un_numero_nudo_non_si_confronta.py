"""Due numeri senza unità non vengono confrontati, ed è una PROTEZIONE.

Trovato il 2026-08-04 mentre si valutava se estendere al rilevatore numerico la
cura fatta su quello booleano. `numeric_conflict` non riconosce una
contraddizione vera:

    «La magnitudo momento del sisma è 6.3» / «… è 7.1»   ->  None

La causa è che `extract_quantities` restituisce ``('', 6.3)`` — unità vuota — e
il confronto richiede la stessa unità. Sembra un buco: due numeri diversi sullo
stesso identico soggetto e nessun conflitto.

⚠️ NON LO È, ED È LA RAGIONE PER CUI QUESTO FILE ESISTE. La stessa regola che
perde la magnitudo salva questi:

    «Il paziente 7 ha risposto»      / «Il paziente 12 ha risposto»   -> None
    «La stanza 101 è libera»         / «La stanza 102 è libera»       -> None
    «La release 2.1 è stabile»       / «La release 3.0 è stabile»     -> None
    «Delezione sul cromosoma 7»      / «… sul cromosoma 9»            -> None

Sono i sei casi su cui ws4 aveva falsificato il criterio del «residuo» (0 su 6,
04/08): togliendo i numeri quelle frasi diventano identiche, e un criterio
lessicale le dichiara la stessa cosa. Sono invece **entità diverse**, e
ritirarne una cancella un fatto vero — irreversibilmente.

Un numero in una frase è o **il valore misurato** (cambia legittimamente: è
un'evoluzione) o **parte dell'identità dell'entità** (e allora sono due cose
diverse). «Il paziente 7 pesa 80 kg» contiene entrambi. Nessuna regola sulla
forma li separa — è lo stesso nodo di NLI.

Di fronte a quel nodo il prodotto si comporta in modo conservativo: **se il
numero non porta un'unità, non lo si usa per dichiarare un conflitto**. Il
costo dell'errore è asimmetrico — ritirare un fatto vero è irreversibile,
tenerne due che si contraddicono è recuperabile al read, dove c'è la domanda —
quindi la scelta è quella giusta. Ma finora era **accidentale**: nessun test la
presidiava, e chiunque avesse «curato» il falso negativo della magnitudo
avrebbe riaperto i sei casi qui sopra senza accorgersene.

Questo file la rende una decisione, non un effetto collaterale.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities, numeric_conflict

#: Il numero È l'identità: ritirarne uno cancella un'entità.
IDENTITA = [
    ("Il paziente 7 ha risposto al trattamento.",
     "Il paziente 12 ha risposto al trattamento."),
    ("La stanza 101 e' libera.", "La stanza 102 e' libera."),
    ("La release 2.1 e' stabile.", "La release 3.0 e' stabile."),
    ("Delezione sul cromosoma 7.", "Delezione sul cromosoma 9."),
    ("Neutropenia di grado 3.", "Neutropenia di grado 4."),
    ("Il fatturato del 2024 e' consolidato.",
     "Il fatturato del 2025 e' consolidato."),
]

#: Il numero è un VALORE misurato, e porta un'unità: qui il conflitto è reale
#: e dev'essere visto.
VALORI = [
    ("Il piano annuale costa 100 euro.", "Il piano annuale costa 120 euro."),
    ("La latenza di lettura e' 5 ms.", "La latenza di lettura e' 9 ms."),
    ("The read latency is 5 ms.", "The read latency is 9 ms."),
    ("Il corpus contiene 7420 fatti.", "Il corpus contiene 7500 fatti."),
]


@pytest.mark.parametrize("a,b", IDENTITA)
def test_un_numero_che_e_identita_non_apre_un_conflitto(a, b):
    """Il cuore. Sono i sei casi su cui il criterio del residuo falliva 0 su 6:
    qui devono restare due fatti, non uno."""
    assert numeric_conflict(a, b) is None, (
        f"«{a}» e «{b}» sono due ENTITA' diverse, non due valori dello stesso "
        f"fatto: dichiararle in conflitto ne cancella una")


@pytest.mark.parametrize("a,b", VALORI)
def test_un_valore_con_unita_apre_il_conflitto(a, b):
    """IL VERSO OPPOSTO, che rende la protezione una scelta e non una
    rinuncia: dove il numero è chiaramente una misura, il conflitto si vede."""
    assert numeric_conflict(a, b) is not None, (
        f"«{a}» e «{b}» si contraddicono sulla stessa grandezza e il "
        f"rilevatore non lo vede")


def test_e_il_meccanismo_e_l_unita_vuota():
    """Un livello più sotto, così un domani si vede SUBITO se a cambiare è la
    regola o l'estrattore."""
    assert extract_quantities("La magnitudo momento del sisma e' 6.3.") == {
        ("", 6.3)}, "l'estrattore non da' piu' unita' vuota sui numeri nudi"
    assert extract_quantities("Il piano annuale costa 100 euro.") == {
        ("euro", 100.0)}


def test_IL_PREZZO_DELLA_PROTEZIONE_e_dichiarato():
    """Il falso negativo che questa scelta si porta dietro, scritto qui perché
    non si scopra due volte: una contraddizione VERA fra numeri nudi non viene
    vista.

    «La magnitudo momento del sisma è 6.3» e «… è 7.1» parlano della stessa
    grandezza dello stesso sisma e non possono essere entrambe vere. Il
    rilevatore le lascia passare, e le due convivono.

    ⚠️ NON SI CURA aggiungendo il confronto dei numeri nudi: riaprirebbe i sei
    casi di `IDENTITA` qui sopra, dove sbagliare significa CANCELLARE un fatto
    vero. Costa un falso negativo per evitare sei falsi positivi irreversibili,
    ed è il verso giusto dell'asimmetria. La cura vera richiede di sapere se il
    numero è un valore o un'identità — che è conoscenza del mondo, non della
    frase, e sul 2026-08-04 tre criteri per dedurla dalla forma sono stati
    misurati e ritirati."""
    assert numeric_conflict("La magnitudo momento del sisma e' 6.3.",
                            "La magnitudo momento del sisma e' 7.1.") is None
