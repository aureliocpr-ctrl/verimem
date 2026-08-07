"""«443 secondi» non è un'invenzione se la fonte dice 443.0485324859619.

IL FALSO POSITIVO, trovato da ws1 **senza cercarlo** — gli è capitato al primo
fatto vero salvato dopo la cura, che è il modo che vale di più::

    fonte: «ESITO: COMPLETATO durata 443.0485324859619 chiamate LLM 8»
    A) «…in 443 secondi producendo 7 skill nuove»      QUARANTINATO  ['L4.1','L4.2']
    B) «…con durata 443.0485324859619 e 7 skill nuove»  ammesso       []
    C) «…producendo 7 skill nuove» (senza durata)       ammesso       []

Una sola variabile: l'arrotondamento. E il fatto aveva **grounding 100.0** — il
moat lo approvava al massimo mentre L4.1 lo tratteneva.

🔑 **Troncare un decimale è la forma più comune in cui un umano riporta una
durata**, e questo rende il falso positivo ad alta frequenza.

LE DUE STRADE CADUTE, misurate da ws5 (che ha fatto cadere anche la propria)::

    prefisso letterale («443» sta dentro «443.048…»)
        veri ammessi 6/10 · falsi fermati 8/9   ← ammette «44», che è un altro numero
    tolleranza relativa ≤1%
        19/19 sugli arrotondamenti, poi CADE 4 volte su 4 dove l'1% è una
        differenza VERA:  «505» da «500 mg» AMMESSO (è un'altra dose) ·
        «4.03» da «4 per cento» AMMESSO · «50.4» da «50.00 mm» AMMESSO
    ⇒ una tolleranza fissa non può funzionare: l'1% di una durata è rumore,
      l'1% di una dose è un errore clinico.

✅ IL CRITERIO CHE REGGE — le CIFRE SIGNIFICATIVE: **un numero riportato con k
decimali dichiara la propria precisione**, e vale ±mezza unità dell'ultima cifra
SCRITTA::

    tolleranza = 0.5 * 10^(-decimali_scritti_nel_claim)
    ammesso  ⟺  esiste y nella fonte con |x - y| < tolleranza   (STRETTO)

    «443»  da «443.0485…»  ±0.5    |0.0485| < 0.5     AMMESSO   ← il caso di ws1
    «505»  da «500 mg»     ±0.5    |5|      > 0.5     FERMATO
    «4.03» da «4 per cento» ±0.005 |0.03|   > 0.005   FERMATO
    «44»   da «443.048»    ±0.5    |399|    > 0.5     FERMATO

🔑 **Nessun parametro da tarare**: la tolleranza non è una costante scelta da
noi, la dichiara chi scrive il numero. È il modo standard in cui scienza e
ingegneria trattano un valore riportato, ed è la ragione per cui regge su domini
che nessuno di noi ha previsto — non c'è niente da ri-calibrare.

⚠️ QUESTO BANCO È MIO E I CASI SONO MIEI. ws5 ha misurato 38/38 sulle proprie
prove e ha dichiarato da sé il limite: *«le 38 prove le ho scritte io, che ho in
mente la cura»* — è la trappola che questa casa ha pagato cinque volte. Qui i
casi sono scritti da chi la cura la implementa e non l'ha progettata, su domini
che il suo elenco non tocca (pressioni, tolleranze meccaniche, valute, tempi).
"""
from __future__ import annotations

import pytest

from verimem.valore_non_nella_fonte import valori_non_nella_fonte


@pytest.mark.parametrize("claim,fonte", [
    # IL CASO DI ws1, verbatim
    ("Il ciclo e' durato 443 secondi.",
     "ESITO: COMPLETATO durata 443.0485324859619 chiamate LLM 8"),
    # arrotondamenti ordinari, domini che l'elenco di ws5 non tocca
    ("La query ha impiegato 2 secondi.", "tempo misurato 2.0031 s"),
    ("Il file pesa 72 MB.", "dimensione 72.4183 MB sul disco"),
    ("La copertura e' 87 per cento.", "coverage 86.9997% sulle righe"),
    ("Il carico medio e' 3.1 richieste.", "media 3.0952380952 richieste/s"),
    ("La pressione era 4.2 bar.", "lettura del sensore 4.2049 bar"),
])
def test_un_numero_ARROTONDATO_e_lo_stesso_numero(claim, fonte):
    """IL CUORE: chi scrive «443» sta riportando 443.0485 con la precisione che
    dichiara, non inventando una cifra."""
    assert not valori_non_nella_fonte(claim, fonte), (
        f"arrotondamento trattato come invenzione: «{claim}»")


@pytest.mark.parametrize("claim,fonte", [
    # ⚠️ LA POPOLAZIONE OPPOSTA, ed è quella che rende consegnabile la cura.
    ("La dose e' di 505 mg.", "posologia: dose 500 mg al giorno"),
    ("Il tasso e' del 4.03 per cento.", "interessi al 4 per cento annuo"),
    ("Il diametro misura 50.4 mm.", "diametro nominale 50.00 mm"),
    ("Il lotto contiene 44 pezzi.", "il ciclo ha richiesto 443.048 secondi"),
    ("Il totale e' 1240 euro.", "importo fatturato 1234.56 euro"),
    ("Sono stati consegnati 40 pezzi.", "consegnati 30 pezzi in due viaggi"),
])
def test_un_numero_DIVERSO_resta_fermato(claim, fonte):
    """⚠️ «505 mg» dove la fonte dice 500 è esattamente ciò che questo prodotto
    esiste per fermare, ed è il caso su cui la tolleranza relativa dell'1%
    cadeva. La precisione dichiarata dal claim lo separa: ±0.5 su un intero non
    arriva a 5."""
    assert valori_non_nella_fonte(claim, fonte), (
        f"numero diverso ammesso: «{claim}» contro «{fonte}»")


def test_la_precisione_la_DICHIARA_chi_scrive_il_numero(mem=None):
    """🔑 IL CUORE DEL CRITERIO, isolato: **la stessa distanza** è dentro
    tolleranza per un numero scritto senza decimali e fuori per uno che ne
    dichiara due. Non è una soglia che abbiamo scelto noi — è quanta precisione
    il claim si attribuisce."""
    fonte = "valore misurato 4.03"
    assert not valori_non_nella_fonte("Il valore e' 4.", fonte)     # ±0.5
    assert valori_non_nella_fonte("Il valore e' 4.00.", fonte)      # ±0.005


def test_un_valore_ASSENTE_resta_assente(mem=None):
    """Il perimetro storico non cambia: un numero che la fonte non contiene
    affatto — né esatto né arrotondabile — resta il difetto che L4.1 cura."""
    fonte = "Verbale: si e' tenuta la riunione trimestrale col fornitore Bianchi."
    assert valori_non_nella_fonte("La riunione e' durata 90 minuti.", fonte)


def test_senza_numeri_o_senza_fonte_il_criterio_TACE(mem=None):
    """Invarianti dichiarate nel modulo: senza uno dei due testi non c'è nulla
    da confrontare, e inventarsi un verdetto è ciò che il modulo esiste per
    impedire."""
    assert not valori_non_nella_fonte("Nessun numero qui.", "nemmeno qui")
    assert not valori_non_nella_fonte("", "durata 443.048")
    assert not valori_non_nella_fonte("Il ciclo e' durato 443 secondi.", "")
