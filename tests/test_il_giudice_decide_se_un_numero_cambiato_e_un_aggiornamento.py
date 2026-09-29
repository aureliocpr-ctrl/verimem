"""T216 — il giudice decide se un numero cambiato è un aggiornamento.

La regola numerica (T175: (a') più le guardie sugli indici, sui codici e sui
percorsi) trova il CANDIDATO, due fatti con una sola quantità diversa della
stessa unità. Il giudice NLI decide (lead, 28-29/09): contraddizione, il nuovo
supera; neutrale, coesistono. Senza giudice decide la regola, e la ricevuta lo
dice.

Misurato su 281 coppie vere il 28-29/09: la catena ritira 0 dei 251 ritiri
sbagliati del heal, 0 di 12 negativi e 14 di 18 positivi; la regola da sola 0,
2 e 15. Qui il giudice è finto, così le celle misurano la CATENA e non il
modello, e danno lo stesso esito con o senza il modello sulla macchina.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

import verimem.local_relation as lr
import verimem.validate_claim as vc
from verimem.client import Memory

VECCHIO = "Il contatore segna 10 impulsi."
NUOVO = "Il contatore segna 20 impulsi."
PROBABILITA = {
    "contraddizione": {"contradiction": 0.9, "entailment": 0.05, "neutral": 0.05},
    "neutrale": {"contradiction": 0.1, "entailment": 0.1, "neutral": 0.8},
}


@dataclass
class _Fatto:
    id: str
    proposition: str
    topic: str = "banco/t216"
    confidence: float = 0.9
    source_episodes: list[str] = field(default_factory=list)


class _Semantica:
    def __init__(self, fatti):
        self._fatti = fatti

    def search_facts(self, query, *, limit=20, topic=None):
        return list(self._fatti)


class _Agente:
    def __init__(self, fatti):
        self.semantic = _Semantica(fatti)


def _giudice(monkeypatch, relazione: str) -> None:
    probs = PROBABILITA[relazione]
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "enforce")
    monkeypatch.setattr(lr, "_judge", lr.LocalRelationJudge(
        classifier=lambda coppie: [dict(probs) for _ in coppie]))


def _senza_giudice(monkeypatch) -> None:
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "0")


def _verdetto(vecchio: str = VECCHIO, nuovo: str = NUOVO) -> dict:
    return vc.validate_claim(_Agente([_Fatto("vecchio", vecchio)]), nuovo)


def _ritira(r: dict) -> bool:
    return r.get("verdict") == "contradicted" and "vecchio" in (r.get("evidence_facts") or [])


def test_il_giudice_dice_contraddizione_e_il_nuovo_supera(monkeypatch):
    _giudice(monkeypatch, "contraddizione")
    r = _verdetto()
    assert _ritira(r), r
    assert r.get("numeric_decided_by") == "judge", r


def test_il_giudice_dice_neutrale_e_i_due_fatti_coesistono(monkeypatch):
    """Anche davanti al giudice di entailment che nega sempre il sostegno: senza
    la cura sarebbe lui a ritirare la coppia che il giudice NLI dice di due
    soggetti."""
    _giudice(monkeypatch, "neutrale")
    monkeypatch.setattr(vc, "_giudice_contraddice", lambda a, b: True)
    r = _verdetto()
    assert not _ritira(r), r


def test_senza_giudice_decide_la_regola_e_lo_dice(monkeypatch):
    _senza_giudice(monkeypatch)
    r = _verdetto()
    assert _ritira(r), r
    assert r.get("numeric_decided_by") == "rule", r
    assert vc.NOTA_DECISO_DALLA_REGOLA in str(r.get("advice")), r


@pytest.mark.parametrize("chi", ["rule", "judge"])
def test_la_ricevuta_di_scrittura_dice_chi_ha_deciso(tmp_path, monkeypatch, chi):
    if chi == "rule":
        _senza_giudice(monkeypatch)
    else:
        _giudice(monkeypatch, "contraddizione")
    m = Memory(str(tmp_path / "m.db"), principal="anna")
    m.add("Il magazzino K-77 di Rovigo ha 4200 metri quadrati.", topic="az/mag")
    ric = m.add("Il magazzino K-77 di Rovigo ha 5100 metri quadrati.", topic="az/mag")
    avvisi = [w for w in (ric.get("warnings") or [])
              if w.get("layer") == "L3-supersession"]
    assert avvisi, f"nessun ritiro annunciato: {ric.get('warnings')}"
    assert avvisi[0].get("decided_by") == chi, avvisi
    nota = vc.NOTA_DECISO_DALLA_REGOLA in str(avvisi[0].get("advice"))
    assert nota is (chi == "rule"), avvisi
