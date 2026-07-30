"""Il rumore che lo store misura si DICHIARA, ma non decide da solo.

Questo file ha avuto due vite nello stesso giorno, e la seconda e' la lezione.

PRIMA VITA (mattina). Il dogfooding in parallelo aveva trovato che una domanda
senza risposta usciva `answerable`:

    verimem ignorance "Quale versione di Kubernetes usa il cluster di OnlyPaws?"
    -> answerable=1   noise_floor=0.861 (measured)   best=0.8369

Il verdetto era `top < floor(0.8)` -> ignoranza, altrimenti `answerable`, e il
`noise_floor` MISURATO entrava solo dentro il ramo dell'ignoranza. Con un rumore
piu' alto del pavimento statico, la fascia fra i due era rispondibile per
costruzione. La mia cura: far decidere `max(floor, noise_floor)`.

SECONDA VITA (pomeriggio). Quella cura e' SBAGLIATA, e l'ho misurata sul corpus
vero prima di lasciarla in piedi. Con la soglia `max`, su otto domande che il
corpus sa rispondere — il moat, il grounding score, le regole di Aurelio, la
pubblicazione su PyPI, il critic orchestrator — SETTE uscivano come ignoranza e
le `answerable` erano ZERO. Una mappa che dice «non lo so» su tutto e' inutile
quanto una che dice «lo so» su tutto.

L'errore concettuale, che si vede solo misurando: `estimate_relevance_floor` e'
il 95o percentile dei MASSIMI di sonde scramblate. Su un corpus grande qualche
sonda casuale becca sempre qualcosa, quindi quel numero e' alto per costruzione
(0.87 sul corpus vero) e NON e' «il livello sotto cui non c'e' informazione».
Usarlo come soglia di risposta taglia i match semantici veri: una domanda che
RIFORMULA un fatto vale ~0.78 e sta sotto. Misurato anche su store piccoli: con
2 fatti il floor stimato e' 0.9187, e mangia i fatti appena scritti.

FORMA CORRETTA: decide il pavimento dichiarato; quando il top sta sotto il
rumore misurato la risposta si da' lo stesso, con un `caveat` esplicito. Il
difetto originale non torna — quella fascia non e' piu' dichiarata rispondibile
SENZA RISERVE — e il prodotto non diventa muto.
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


def _riga(punteggio, *, floor=0.8, noise_floor=0.861):
    rep = ignorance_map(_Memoria(punteggio), ["Quale versione di Kubernetes usa "
                                              "il cluster di OnlyPaws?"],
                        floor=floor, noise_floor=noise_floor)
    return rep["queries"][0], rep


def test_un_hit_sotto_il_rumore_risponde_MA_LO_DICE():
    """Il caso trovato sul corpus vero: 0.8369 sopra il pavimento dichiarato,
    sotto il rumore misurato. Non e' ignoranza — e non e' nemmeno una risposta
    da dare senza riserve."""
    r, _ = _riga(0.8369)
    assert r["class"] == "answerable", r
    assert r.get("caveat"), (
        "la fascia sotto il rumore misurato viene dichiarata rispondibile "
        "senza alcuna riserva: e' il difetto originale")
    assert "noise" in r["caveat"].lower()


def test_una_domanda_che_il_corpus_SA_rispondere_non_diventa_ignoranza():
    """La regressione che la prima cura aveva introdotto: sette domande su
    otto, sul corpus vero, erano diventate ignoranza."""
    r, _ = _riga(0.93, noise_floor=0.95)
    assert r["class"] == "answerable", (
        f"un hit forte e' stato classificato come ignoranza perche' il rumore "
        f"misurato e' alto: {r}")


def test_sopra_il_rumore_nessuna_riserva():
    r, _ = _riga(0.93, noise_floor=0.861)
    assert r["class"] == "answerable" and not r.get("caveat"), r


def test_decide_il_pavimento_dichiarato():
    """Sotto il floor dell'operatore e' ignoranza, qualunque cosa dica la
    misura del rumore."""
    r, rep = _riga(0.75, floor=0.8, noise_floor=0.2)
    assert rep["deciding_floor"] == pytest.approx(0.8)
    assert r["class"] != "answerable", r


def test_i_due_numeri_restano_visibili_entrambi():
    _, rep = _riga(0.8369)
    assert rep["floor"] == 0.8
    assert rep["noise_floor"] == pytest.approx(0.861)
    assert rep["noise_floor_source"] == "caller"
