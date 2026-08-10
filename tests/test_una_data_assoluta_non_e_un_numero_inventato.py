"""«Il 10 agosto 46 fatti…» contro una fonte che dice «oggi»: NUMERO INVENTATO.

✅ CURATO. Il file è nato come guardiano con quattro allarmi ``xfail(strict)``
mentre la cura non c'era; la cura è arrivata subito dopo e **gli allarmi sono
scattati tutti e quattro insieme** — quattro ``XPASS(strict)``, che è il modo in
cui uno xfail severo dice «il difetto che sorvegliavo non c'è più». I marcatori
sono stati tolti in quel momento e le asserzioni sono rimaste identiche: quello
che segue è lo stesso banco, ora verde.

📌 Perché è scritto qui: il difetto aveva già colpito **due fatti veri** e la
sua causa era stata attribuita a due cose diverse — e sbagliate — prima che
qualcuno la misurasse. Il banco è nato per impedire che si riperda, e serve
ancora a questo.

═══ LA CAUSA, A/B nella stessa esecuzione (immune allo SHA) ═══

    claim «…dalle 16:00 del 10 agosto…»  ->  accusato ('10', 'agosto')
    claim «…dalle 16:00 di oggi…»        ->  []

Un solo cambiamento nel claim e l'accusa sparisce. L'estrattore lo dice in
chiaro: ``extract_quantities`` legge ``10 agosto`` come la coppia
``('agosto', 10.0)`` — valore 10, unità «agosto». Se la fonte scrive la data in
forma RELATIVA e il claim la risolve, quel 10 è per il gate un valore che la
fonte non contiene: **un numero inventato**.

🔑 PERCHÉ CONTA PIÙ DEI DUE FATTI COLPITI: una memoria persistente ESIGE che le
date relative siano risolte — «oggi», dentro un fatto che vivrà mesi, è inutile
o falso. **Il gate punisce esattamente la pratica che la persistenza richiede.**
Chi scrive «oggi» passa; chi scrive «10 agosto» viene accusato di inventare.

═══ QUANTO È LARGA: TUTTE le notazioni, e la peggiore è la più comune ═══

    claim                       accusati
    «Il 10/08/2026 …»           ['08', '10', '2026']   <- anche l'ANNO
    «Il 2026-08-10 …»           ['08', '10']           <- l'ISO degli archivi
    «Il 10 agosto …»            ['10']
    «On 10 August …»            ['10']                 <- e in inglese uguale

⚖️ **LA COPERTURA C'È GIÀ E SI FERMA UN PASSO PRIMA.** Il docstring di
``valore_non_nella_fonte`` dichiara che *«un ANNO nudo non è una quantità (lo
esclude già extract_quantities)»* — ed è vero, ``«scade nel 2027»`` non produce
nulla. Ma l'anno DENTRO una data non è nudo, e infatti ``10/08/2026`` fa
accusare anche il 2026. La causa non è «manca un criterio»: il criterio c'era,
**incompleto** — la classe di errore più frequente di questa casa.

═══ ⚖️ LA POPOLAZIONE, che RIDIMENSIONA questo stesso file ═══

    status          con data giorno+mese   totale   quota
    model_claim                       65     4243    1.5%
    quarantined                        7     2048    0.3%
                                      76     9480

I fatti con una data si quarantinano MENO della media (9,2% contro 21,7%), e dei
7 quarantinati che portano una data **solo DUE sono caduti per la data**:
``8728c271428f`` («10 agosto», l'esemplare qui sotto) e ``45c3e17bd43f`` («31
luglio»). Gli altri cinque hanno una data e sono caduti per altro — è il
controllo interno che dice che **la data da sola non basta: serve la coppia
claim-DATATO + fonte-NON-datata**. Due occorrenze indipendenti sono una forma,
non una classe di massa, e questo file non deve far credere il contrario.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

# L'esemplare REALE, dal fatto 8728c271428f. Le due stringhe sono copiate dal
# corpus (``proposition`` e ``grounding_span``) e non lette dal database: un
# test che interroga lo store dell'utente non è riproducibile altrove, e il
# difetto non ha bisogno del database per manifestarsi.
CLAIM_VERO = (
    "Fra i fatti scritti dalle 16:00 del 10 agosto 46 riportano cli:local come "
    "autore e 7 riportano cli:local/ws7:lanterna, su 53 totali.")
FONTE_VERA = (
    "=== per autore dichiarato ===\n"
    "    46  cli:local\n"
    "     7  cli:local/ws7:lanterna\n"
    "fatti scritti dalle 16:00 di oggi: 53")

FONTE_RELATIVA = "Il run di oggi e' fallito dopo 15 minuti."


def _accusati(claim: str, fonte: str) -> list[str]:
    return [v.come_scritto() for v in valori_non_nella_fonte(claim, fonte)]


def test_l_esemplare_vero_non_viene_piu_accusato():
    """IL CASO CHE HA APERTO TUTTO, e l'asserzione non è cambiata con la cura.

    Il fatto ``8728c271428f`` era stato quarantinato con un punteggio del
    giudice di 99,9 — cioè il giudice lo riteneva ben fondato e il gate lo ha
    trattenuto lo stesso. Tutti e tre i numeri che afferma (46, 7, 53) SONO
    nella fonte: l'unico contestato era il 10 di «10 agosto», che nella fonte
    compare come «oggi».
    """
    assert _accusati(CLAIM_VERO, FONTE_VERA) == []


@pytest.mark.parametrize("claim", [
    "Il 10/08/2026 il run e' fallito dopo 15 minuti.",   # accusa anche il 2026
    "Il 2026-08-10 il run e' fallito dopo 15 minuti.",   # l'ISO degli archivi
    "Il 10 agosto il run e' fallito dopo 15 minuti.",
])
def test_nessuna_notazione_di_data_va_letta_come_quantita(claim):
    """Le tre notazioni che un archivio usa davvero, e cadevano tutte.

    Stanno insieme perché hanno una causa sola, ma il costo NON era lo stesso:
    la forma italiana ``10/08/2026`` produceva **tre** accuse contro l'unica
    della forma estesa, perché ci finisce dentro anche l'anno. ⚠️ Restano
    parametrizzate e non riassunte in un'asserzione sola per una ragione che
    vale ancora oggi: **una cura che riconoscesse solo «giorno + nome del mese»
    passerebbe l'ultimo caso e lascerebbe in piedi i due peggiori**, e il banco
    deve poterlo dire caso per caso.
    """
    assert _accusati(claim, FONTE_RELATIVA) == []


def test_CONTROLLO_NEGATIVO_un_numero_DAVVERO_inventato_resta_accusato():
    """⚠️ SENZA QUESTO, il file si leggerebbe come «spegniamo L4.1 sulle date».

    Il 99 non è in nessuna fonte e deve continuare a essere contestato: ciò che
    va corretto è la lettura della DATA, non la severità del confronto. È la
    differenza fra restringere un criterio e disattivarlo.
    """
    assert _accusati("Il 10 agosto 99 fatti riportano cli:local.",
                     "Conteggio del 10 agosto: 46 fatti riportano cli:local.") == ["99"]


@pytest.mark.parametrize("claim,fonte,atteso", [
    ("Il magazzino contiene 480 pallet.", "Il magazzino ha 320 pallet.", ["480"]),
    ("La tolleranza e' 0.125 mm.", "La tolleranza e' 0.250 mm.", ["0.125"]),
])
def test_CONTROLLO_POSITIVO_le_quantita_vere_restano_misurabili(claim, fonte, atteso):
    """LA POPOLAZIONE OPPOSTA: le quantità che non sono date non si toccano."""
    assert _accusati(claim, fonte) == atteso


def test_una_fonte_ANCH_ESSA_datata_non_produce_accusa():
    """LA DELIMITAZIONE, ed è ciò che rende il difetto raro invece che diffuso.

    Serve la COPPIA claim-datato + fonte-non-datata. Quando anche la fonte porta
    la data, il 10 si ritrova da entrambe le parti e nessuno protesta — ed è il
    motivo per cui nel corpus solo due fatti su 2048 quarantinati sono caduti
    così, invece dei 76 che una data ce l'hanno.
    """
    assert _accusati("Il 10 agosto 46 fatti riportano cli:local.",
                     "Conteggio del 10 agosto: 46 fatti riportano cli:local.") == []


def test_LA_COPERTURA_DEGLI_ANNI_C_ERA_GIA_e_ora_arriva_al_giorno():
    """Le due metà dello stesso criterio, che ora coprono la stessa cosa.

    L'anno nudo era già escluso: la classe «questo non è un numero da
    verificare, è una data» era **già riconosciuta** dal prodotto, e alla cura
    è toccato aggiungere il resto della data invece di inventare un criterio
    nuovo. Le due asserzioni stanno insieme perché se un giorno cadesse la
    PRIMA vorrebbe dire che qualcuno ha rimosso la copertura storica mentre
    lavorava sulla nuova — un'informazione diversa da tutte le altre di questo
    file, e che nessun altro test qui dentro saprebbe dare.
    """
    assert extract_quantities("Il contratto scade nel 2027.") == set()
    assert extract_quantities("Il 10 agosto il run e' fallito.") == set()
