"""Il rumore che lo store misura deve poter dire «non lo so», non solo «di che
tipo di non-so si tratta».

TROVATO dal dogfooding in parallelo il 2026-07-30, e vale contro di me: avevo
collegato `ignorance_map` a SDK, MCP e CLI qualche ora prima senza accorgermi
che il verdetto lo prendeva un solo numero.

    verimem ignorance "Quale versione di Kubernetes usa il cluster di
    produzione di OnlyPaws?"   (risposta inesistente nel corpus, per costruzione)
    -> answerable=1   noise_floor=0.861 (measured)   best=0.8369

Il codice diceva: `top < floor(0.8)` -> ignoranza, altrimenti `answerable`. Il
`noise_floor` MISURATO sullo store entrava solo DENTRO il ramo dell'ignoranza,
per distinguere `no_evidence` da `below_floor`. Quindi con un rumore misurato
(0.861) piu' alto del pavimento statico (0.8) — il caso di questo corpus, banda
e5 compressa — tutta la fascia [0.80, 0.861] risultava rispondibile pur essendo,
per la misura dello store stesso, «a nearest neighbour with nothing to say»
(parole del commento accanto, nel ramo che non veniva raggiunto).

E' la quarta volta in due giorni che la forma e' questa: un meccanismo
costruito, misurato, e attivo solo sul percorso che qualcuno aveva guardato.

CURA: la soglia che decide e' `max(floor, noise_floor)`. Non abbassa mai il
pavimento dichiarato dall'operatore — lo alza solo quando lo store dimostra che
sotto quel livello c'e' rumore. E il report dice QUALE dei due ha deciso,
perche' una soglia che cambia il verdetto dev'essere visibile in esso.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from verimem.ignorance_map import ignorance_map


class _Semantica:
    def __init__(self, fatti):
        self._fatti = fatti

    def get(self, fid):
        return self._fatti.get(fid)

    def all(self):
        return list(self._fatti.values())


class _Memoria:
    """Doppio deterministico: la suite gira con un embedder stub, quindi i
    punteggi veri non sono semantici — qui il punteggio E' il caso di prova."""

    def __init__(self, punteggio, testo="Il bot CAWBOT gira su un VPS."):
        self._p = punteggio
        f = SimpleNamespace(id="f1", proposition=testo, status="verified")
        self.semantic = _Semantica({"f1": f})

    def search(self, query, k=5, **kw):
        return [{"id": "f1", "score": self._p, "text": "Il bot CAWBOT gira su un VPS."}]


def _classe(punteggio, *, floor=0.8, noise_floor=0.861):
    rep = ignorance_map(_Memoria(punteggio), ["Quale versione di Kubernetes usa "
                                              "il cluster di OnlyPaws?"],
                        floor=floor, noise_floor=noise_floor)
    return rep["queries"][0]["class"], rep


def test_un_hit_sotto_il_rumore_misurato_non_e_una_risposta():
    """Il caso esatto trovato sul corpus vero: 0.8369 sopra il pavimento
    statico, sotto il rumore misurato."""
    classe, rep = _classe(0.8369)
    assert classe != "answerable", (
        f"un hit a 0.8369, sotto il rumore misurato {rep['noise_floor']}, "
        f"e' stato dichiarato rispondibile")


def test_il_report_dice_quale_soglia_ha_deciso():
    """Due numeri, uno decide: se non si vede quale, il verdetto non e'
    verificabile da chi lo legge."""
    _, rep = _classe(0.8369)
    assert rep.get("deciding_floor") == pytest.approx(0.861), rep
    assert rep["floor"] == 0.8 and rep["noise_floor"] == pytest.approx(0.861), (
        "i due numeri di partenza restano visibili entrambi")


def test_sopra_il_rumore_resta_rispondibile():
    """La cura non deve trasformare il prodotto in un astensionista: sopra
    entrambe le soglie la risposta si da'."""
    classe, _ = _classe(0.93)
    assert classe == "answerable"


def test_il_pavimento_dell_operatore_non_viene_mai_abbassato():
    """Se il rumore misurato e' PIU BASSO del floor dichiarato, decide il
    floor: un operatore che ha alzato l'asticella non se la vede abbassare da
    una misura automatica."""
    classe, rep = _classe(0.85, floor=0.9, noise_floor=0.2)
    assert rep["deciding_floor"] == pytest.approx(0.9)
    assert classe != "answerable", "0.85 sta sotto il floor dichiarato 0.9"


def test_col_rumore_non_misurabile_il_comportamento_e_quello_di_prima():
    """Store troppo piccolo per misurare il rumore (0.0, la risposta
    deliberata di estimate_relevance_floor): nessun cambiamento."""
    classe, rep = _classe(0.85, floor=0.8, noise_floor=0.0)
    assert rep["deciding_floor"] == pytest.approx(0.8)
    assert classe == "answerable"
