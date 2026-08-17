"""«Pavimento spento» e «pavimento chiesto e non ottenuto» non sono la stessa cosa.

Il guardiano si astiene quando il punteggio migliore sta sotto il pavimento, e
salta il controllo quando il pavimento vale zero. Ma zero arrivava da due strade
opposte e indistinguibili:

    min_relevance=None / 0 / "off"   zero VOLUTO — chi usa il prodotto ha scelto
                                     di non filtrare
    min_relevance="auto"  -> 0.0     zero NON voluto — la calibrazione non ha
                                     prodotto una soglia

Il secondo capita su un corpus troppo piccolo per calibrarsi (misurato: 1 fatto
→ 0.0, 6 fatti → 0.9166), cioè **sul primo fatto di un tenant nuovo** — e il
gateway passa `"auto"` per impostazione predefinita, con l'intento dichiarato nel
codice di far astenere l'API di default.

Quello che questo collaudo NON pretende: che il prodotto scelga una soglia al
posto di chi lo governa. Su un corpus piccolo, servire troppo e astenersi troppo
sono due prodotti diversi. Pretende solo che la risposta DICA in quale dei due
casi si trova.
"""
from __future__ import annotations

from typing import Any

import pytest

from verimem.guardian import correct_read


class _FattoFinto:
    def __init__(self, testo: str) -> None:
        self.proposition = testo
        self.status = "model_claim"
        self.epistemic = None
        self.id = "f1"


class _SemanticFinta:
    def __init__(self, fatto: _FattoFinto) -> None:
        self._f = fatto

    def get(self, _id: str) -> Any:
        return self._f


class _MemoriaFinta:
    """Uno store con un fatto solo e un pavimento auto-calibrato che vale zero."""

    def __init__(self, pavimento_auto: float) -> None:
        self._pav = pavimento_auto
        self.semantic = _SemanticFinta(_FattoFinto("Il pacchetto pesa tre chilobyte."))

    def search(self, _query: str, **_kw: Any) -> list[dict[str, Any]]:
        return [{"id": "f1", "score": 0.75}]

    def _auto_relevance_floor(self) -> float:
        return self._pav


def test_auto_senza_calibrazione_lo_dice():
    """Il caso del primo fatto: il pavimento è stato chiesto e non c'era."""
    esito = correct_read(_MemoriaFinta(0.0), "una domanda", min_relevance="auto")
    assert esito["verdict"] != "ABSTAIN", (
        "senza pavimento la risposta viene servita: è il comportamento che questo "
        "collaudo NON cambia — cambia solo che venga dichiarato")
    assert esito.get("floor_note") == "relevance_floor_requested_but_uncalibrated", (
        f"è stato chiesto `auto`, la calibrazione ha dato 0.0 e la risposta è stata "
        f"servita senza pavimento: la nota deve dirlo, invece vale "
        f"{esito.get('floor_note')!r}. Senza, chi legge non distingue questo caso da "
        f"un pavimento spento di proposito.")


def test_pavimento_spento_di_proposito_non_avvisa():
    """Chi ha scelto di non filtrare non deve ricevere un avviso su una sua scelta."""
    for scelta in (None, 0.0):
        esito = correct_read(_MemoriaFinta(0.0), "una domanda", min_relevance=scelta)
        assert esito.get("floor_note") is None, (
            f"con min_relevance={scelta!r} il pavimento è spento per volontà di chi usa "
            f"il prodotto: avvisarlo trasformerebbe la nota in rumore, e una nota che "
            f"compare sempre non segnala più nulla")


def test_pavimento_calibrato_non_avvisa():
    """Quando la calibrazione riesce non c'è niente da segnalare."""
    esito = correct_read(_MemoriaFinta(0.60), "una domanda", min_relevance="auto")
    assert esito.get("floor_note") is None, (
        "il pavimento è stato chiesto E ottenuto (0.60), il punteggio lo supera (0.75): "
        "non c'è nessuna degradazione da dichiarare")


def test_su_un_astensione_la_nota_non_compare():
    """Se non è stato servito nulla, non c'è nulla che sia stato servito senza pavimento."""
    esito = correct_read(_MemoriaFinta(0.90), "una domanda", min_relevance="auto")
    assert esito["verdict"] == "ABSTAIN"
    assert esito.get("floor_note") is None, (
        "il pavimento ha funzionato e ha fatto astenere: una nota qui direbbe il "
        "contrario di quello che è successo")


@pytest.mark.parametrize("pavimento_auto", [0.0, -1.0])
def test_anche_un_pavimento_negativo_conta_come_non_calibrato(pavimento_auto):
    """Un valore non positivo non è una soglia: non filtra e va dichiarato uguale."""
    esito = correct_read(_MemoriaFinta(pavimento_auto), "una domanda", min_relevance="auto")
    assert esito.get("floor_note") == "relevance_floor_requested_but_uncalibrated"
