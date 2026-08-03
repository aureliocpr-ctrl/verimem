"""`below_floor` non può uscire con la configurazione di default.

Non è un'ipotesi sul comportamento: è l'ordine di due numeri. Si entra nel
blocco «non rispondibile» solo se

    top < soglia                (soglia = pavimento DICHIARATO, default 0.8)

e dentro, il primo ramo utile scatta se

    top <= noise_floor          (rumore che lo store MISURA su se stesso)

quindi `below_floor` richiede  ``noise_floor < top < soglia`` — un intervallo
**vuoto** ogni volta che il rumore misurato sta sopra il pavimento dichiarato.

MISURATO SUL CORPUS DI PRODUZIONE il 2026-08-04: rumore 0.8772, pavimento 0.8.
Venti domande vere, `below_floor` uscito **zero volte**; e zero anche alzando il
pavimento a 0.95, cioè il controesempio previsto non si verifica nemmeno. In
compenso 19 top su 20 (0.819 … 0.877) stanno SOTTO il rumore misurato, quindi il
`caveat` si accende quasi sempre: un avvertimento che scatta 19 volte su 20 non
avverte più di niente.

PERCHÉ IL PRESIDIO ESISTENTE NON LO VEDE. `test_verimem_ignorance_noise.
test_genuinely_weak_evidence_is_still_below_floor` prova la classe con
``floor=0.999``: un pavimento che nessuno userebbe, scelto proprio perché apre
l'intervallo. Il test passa, la classe resta irraggiungibile nell'uso reale. È
la forma già pagata due volte in questi giorni — un presidio che sembra
proteggere e non protegge — e la si vede solo chiedendo «con quali numeri passa,
e sono quelli che il prodotto usa?».

LA RADICE, misurata prima di arrivare qui, e le due strade che NON sono:
  - NON è la scala: il pavimento è piatto fra 2 e 180 fatti (0.8589 → 0.8834),
    e a 2 fatti è più BASSO che a 180;
  - NON è l'omogeneità: stesso topic 0.8476 contro topic diversi 0.8572,
    differenza minima e nella direzione opposta;
  - la lunghezza conta (margine col testo identico: +0.038 a 9 parole, +0.102 a
    40 — 2,7 volte) ma è secondaria, perché con DOMANDE vere il margine crolla a
    +0.0090 / +0.0212 mentre riformulare costa +0.0687 / +0.0726: da tre a otto
    volte lo spazio disponibile.

Quindi il numero prodotto da `estimate_relevance_floor` sta sistematicamente
SOPRA i punteggi delle domande legittime, e ogni uso di quel numero come
discriminante eredita il difetto.

⛔ LA CURA NON È RIALZARE LA SOGLIA. Già scritta, misurata e RITIRATA
(`6a9a5e16`): con ``max(floor, noise_floor)`` sette domande su otto che il
corpus sa rispondere uscivano come ignoranza, e le `answerable` erano ZERO.

Questo file NON cura: **presidia**. Fissa la condizione di raggiungibilità come
proprietà del codice, così chi un domani tocca l'ordine dei rami se ne accorge,
e chi cura il criterio vede accendersi il test che dichiara il caso vuoto.

Deterministico e senza embedder: i punteggi arrivano dal doppio, come in
`test_il_rumore_misurato_decide_anche_lui`. La suite gira con un embedder stub,
quindi un test che misurasse i punteggi veri misurerebbe l'AMBIENTE — errore già
pagato due volte.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from verimem.ignorance_map import ignorance_map

#: Il rumore che lo store misura su se stesso sul corpus di produzione.
RUMORE_VERO = 0.8772
#: Il pavimento che il prodotto dichiara quando nessuno ne passa uno.
PAVIMENTO_DI_DEFAULT = 0.8


class _Semantica:
    def __init__(self, fatti):
        self._fatti = fatti

    def get(self, fid):
        return self._fatti.get(fid)

    def all(self):
        return list(self._fatti.values())


class _Memoria:
    """Il punteggio E' il caso di prova: nessuna dipendenza dall'embedder."""

    def __init__(self, punteggio, testo="Roma è una città."):
        self._p = punteggio
        f = SimpleNamespace(id="f1", proposition=testo, status="verified")
        self.semantic = _Semantica({"f1": f})

    def search(self, query, k=5, **kw):
        return [{"id": "f1", "score": self._p, "text": "Roma è una città."}]


def _classe(punteggio, *, floor, noise_floor):
    return ignorance_map(_Memoria(punteggio), ["Che cos'è Roma?"],
                         floor=floor, noise_floor=noise_floor)["queries"][0]


def test_con_i_numeri_VERI_del_prodotto_la_classe_non_esce():
    """Il caso di default: pavimento 0.8, rumore misurato 0.8772.

    Qualunque punteggio si provi sotto il pavimento — cioè qualunque punteggio
    che porti nel blocco dell'ignoranza — la classe che esce non è mai
    `below_floor`, perché l'intervallo che la richiede è vuoto."""
    assert RUMORE_VERO > PAVIMENTO_DI_DEFAULT, (
        "questo file presuppone il caso misurato sul corpus vero: se il rumore "
        "misurato è sceso sotto il pavimento dichiarato, rimisura e riscrivi")
    usciti = {
        p: _classe(p, floor=PAVIMENTO_DI_DEFAULT,
                   noise_floor=RUMORE_VERO)["class"]
        for p in (0.10, 0.40, 0.60, 0.75, 0.799)
    }
    assert "below_floor" not in usciti.values(), (
        f"la classe è diventata raggiungibile col pavimento di default: "
        f"{usciti}. Se è una cura, aggiorna questo file con la nuova misura "
        f"sul corpus vero; se è un caso, l'ordine dei rami è cambiato")


def test_e_raggiungibile_solo_se_il_pavimento_sta_SOPRA_il_rumore():
    """La condizione esatta, in positivo: appena l'intervallo si apre, la classe
    esce. Serve a distinguere «classe rotta» da «classe irraggiungibile in
    questa configurazione» — è la seconda."""
    r = _classe(0.85, floor=0.90, noise_floor=0.80)
    assert r["class"] == "below_floor", (
        f"con noise_floor(0.80) < top(0.85) < floor(0.90) l'intervallo è "
        f"aperto e la classe deve uscire, invece: {r}")
    assert "0.90" in r["what_would_help"] or "0.9" in r["what_would_help"]


def test_il_presidio_esistente_passa_con_un_pavimento_che_nessuno_userebbe():
    """Perché nessuno se n'era accorto.

    `test_genuinely_weak_evidence_is_still_below_floor` prova la classe con
    ``floor=0.999``. Qui si mostra che è QUELLO a farla uscire: con lo stesso
    punteggio e il pavimento di default la classe cambia."""
    con_pavimento_assurdo = _classe(0.85, floor=0.999, noise_floor=0.80)["class"]
    con_pavimento_vero = _classe(0.85, floor=PAVIMENTO_DI_DEFAULT,
                                 noise_floor=RUMORE_VERO)["class"]
    assert con_pavimento_assurdo == "below_floor"
    assert con_pavimento_vero != "below_floor"
    assert con_pavimento_assurdo != con_pavimento_vero, (
        "il pavimento del test non cambia più l'esito: se il criterio è stato "
        "curato, questo file va riscritto sulla nuova forma")


@pytest.mark.parametrize("top", [0.819, 0.836, 0.848, 0.865, 0.877])
def test_i_punteggi_veri_delle_domande_stanno_sotto_il_rumore(top):
    """I cinque punteggi sono presi dalle venti domande misurate sul corpus di
    produzione. Stanno tutti sopra il pavimento dichiarato e sotto il rumore
    misurato: la risposta si dà, col caveat. Il presidio è che quella fascia
    resti RISPONDIBILE — è il difetto che la cura ritirata aveva introdotto."""
    r = _classe(top, floor=PAVIMENTO_DI_DEFAULT, noise_floor=RUMORE_VERO)
    assert r["class"] == "answerable", (
        f"un punteggio misurato su una domanda vera del corpus ({top}) è "
        f"diventato ignoranza: è la regressione di `6a9a5e16`, {r}")
    assert r.get("caveat"), "la fascia sotto il rumore va dichiarata"


def test_il_caveat_si_accende_su_DICIANNOVE_domande_su_venti():
    """Il numero che rende il caveat poco utile, fissato perché non passi
    inosservato: 19 dei 20 top misurati stanno sotto il rumore.

    Non è un difetto del caveat — senza, quella fascia tornerebbe ad essere
    dichiarata rispondibile senza riserve. È la misura di quanto il rumore
    stimato stia sopra il segnale."""
    TOP_MISURATI = [0.819, 0.819, 0.823, 0.823, 0.830, 0.832, 0.836, 0.837,
                    0.839, 0.839, 0.841, 0.845, 0.847, 0.848, 0.859, 0.861,
                    0.865, 0.870, 0.877, 0.908]
    con_caveat = sum(
        1 for t in TOP_MISURATI
        if _classe(t, floor=PAVIMENTO_DI_DEFAULT,
                   noise_floor=RUMORE_VERO).get("caveat"))
    assert con_caveat == 19, (
        f"{con_caveat}/20 invece di 19/20: se il criterio del caveat è "
        f"cambiato, rimisura sul corpus vero e aggiorna il numero qui")
