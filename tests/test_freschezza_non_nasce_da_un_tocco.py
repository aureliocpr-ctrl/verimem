"""Il dossier di fiducia contava la freschezza da un campo che non
registra una verifica.

ws5, 2026-08-07, misurato e poi CORRETTO da lei stessa entro dieci minuti
— la correzione è il pezzo che conta:

    fatti con last_verified_at > created_at : 2762
      di questi, con un grounding_score     :    0   (zero)

La correlazione col verdetto è perfettamente inversa: il campo avanza —
fino a 87 giorni dopo la scrittura — esattamente sui fatti che un
giudizio non l'hanno mai avuto, ed è plausibilmente il passaggio di una
migrazione o di un re-embedding. Un TOCCO, non un GIUDIZIO.

ws5 aveva proposto di esporlo nel recall e ha ritirato la proposta:
«porterebbe la bugia dal DB all'interfaccia». Ma all'interfaccia c'era
già, e in una superficie di governo: `trust_report._fact_evidence`
calcolava `age_days` da quel campo, e da `age_days` nasce `freshness`.
Misurato sul corpus reale:

    fatti mostrati `live` che da created_at sarebbero `dormant`,
    e che NON hanno un verdetto:  990

Cioè il dossier che risponde a «come fa la memoria a saperlo» presentava
990 fatti mai verificati come freschi, perché qualcosa li aveva toccati.

⛔ Non tocco lo schema né chi scrive quel campo (perimetro altrui). Cambio
da dove nasce il numero: `last_verified_at` conta come verifica SOLO se
c'è un verdetto a sostenerlo. È più forte che ignorarlo — il giorno in cui
una ri-verifica vera esisterà, questa la userà; e finché non esiste, non
regala freschezza a nessuno.
"""
from __future__ import annotations

import time

import pytest

from verimem.client import Memory
from verimem.trust_report import _fact_evidence

_GIORNO = 86400.0


class _Fatto:
    """Il minimo che il dossier legge — evita di dipendere dal write path
    per costruire lo stato che serve (un fatto vecchio e toccato)."""

    def __init__(self, *, created_at, last_verified_at, grounding_score):
        self.id = "f1"
        self.proposition = "the head office is in Milan"
        self.topic = "hq"
        self.status = "provisional"
        self.confidence = 0.5
        self.source_episodes = []
        self.writer_role = None
        self.verified_by = None
        self.grounding_score = grounding_score
        self.asserted_at = None
        self.created_at = created_at
        self.last_verified_at = last_verified_at


@pytest.fixture()
def sm(tmp_path):
    return Memory(tmp_path / "m.db").semantic


def _ev(sm, fatto):
    return _fact_evidence(sm, fatto, None)


def test_un_tocco_senza_verdetto_non_ringiovanisce_il_fatto(sm):
    """Il caso dei 990: scritto 80 giorni fa, toccato ieri, mai giudicato.
    Il dossier lo dava `live`."""
    ora = time.time()
    ev = _ev(sm, _Fatto(created_at=ora - 80 * _GIORNO,
                        last_verified_at=ora - 1 * _GIORNO,
                        grounding_score=None))

    assert ev["age_days"] > 45, ev
    assert ev["freshness"] == "dormant", ev


def test_un_tocco_CON_un_verdetto_conta_eccome(sm):
    """Non sto ignorando il campo: se un verdetto c'è, la ri-verifica è
    sostenuta da qualcosa e il fatto è davvero più fresco. Oggi sul corpus
    reale questo caso non esiste (zero su 2762), ma il giorno in cui una
    ri-verifica vera arriverà, questa la userà senza altre modifiche."""
    ora = time.time()
    ev = _ev(sm, _Fatto(created_at=ora - 80 * _GIORNO,
                        last_verified_at=ora - 1 * _GIORNO,
                        grounding_score=97.0))

    assert ev["age_days"] < 2, ev
    assert ev["freshness"] == "live", ev


def test_senza_il_campo_si_conta_dalla_creazione_come_prima(sm):
    ora = time.time()
    ev = _ev(sm, _Fatto(created_at=ora - 10 * _GIORNO,
                        last_verified_at=None, grounding_score=None))
    assert 9 < ev["age_days"] < 11, ev
    assert ev["freshness"] == "live", ev


def test_il_dossier_DICE_da_quale_timestamp_nasce_il_numero(sm):
    """Un numero senza la sua definizione è il difetto che questo ramo
    cura da due giorni: `age_days` da solo non dice se conta dalla
    scrittura o dall'ultima verifica, e le due cose differiscono di 87
    giorni su un terzo del corpus."""
    ora = time.time()
    senza = _ev(sm, _Fatto(created_at=ora - 80 * _GIORNO,
                           last_verified_at=ora - 1 * _GIORNO,
                           grounding_score=None))
    con = _ev(sm, _Fatto(created_at=ora - 80 * _GIORNO,
                         last_verified_at=ora - 1 * _GIORNO,
                         grounding_score=97.0))

    assert senza["age_basis"] == "created_at", senza
    assert con["age_basis"] == "last_verified_at", con


def test_il_campo_grezzo_resta_visibile_senza_promettere_una_verifica(sm):
    """Toglierlo sarebbe nascondere un dato vero: il campo ESISTE e su
    8091 fatti su 8335 è valorizzato. Resta nel dossier — quello che non
    fa più è produrre da solo un giudizio di freschezza."""
    ora = time.time()
    ev = _ev(sm, _Fatto(created_at=ora - 80 * _GIORNO,
                        last_verified_at=ora - 1 * _GIORNO,
                        grounding_score=None))
    assert ev["last_verified_at"] is not None, ev
