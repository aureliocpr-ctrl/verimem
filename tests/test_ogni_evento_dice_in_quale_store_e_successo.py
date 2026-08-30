"""Ogni riga del journal deve dire in QUALE memoria e' successa.

`flow_events.emit_flow` aggiunge i tag ambient — `surface`, `store`,
`build` — ma `observability.emit` no, e la seconda e' la via che usano
quasi tutti: misurato il 30/08, **99 tipi di evento su 115 non dicono in
quale store sono successi**. Chi legge il journal per contare qualcosa
mescola casa e banchi senza accorgersene, ed e' il difetto che ha gia'
falsato tre indagini.

La cura NON e' su `emit`: e' sul punto UNICO dove entrambe le vie
atterrano, ``append_event``. Cosi' nessun chiamante cambia e i 115 tipi
sono coperti insieme — e chi porta gia' il tag se lo tiene: si aggiunge
solo cio' che manca.

Terza forma dello stesso difetto (`W2-100` l'import, `W2-115` il path
esplicito, `W2-119` questa) e la piu' larga delle tre.
"""
from __future__ import annotations

import json

import pytest

from verimem import event_jsonl_log, observability


@pytest.fixture()
def journal(tmp_path, monkeypatch):
    p = tmp_path / "events.jsonl"
    monkeypatch.setattr(event_jsonl_log, "EVENT_LOG_PATH", p)
    return p


def _righe(p):
    if not p.exists():
        return []
    return [json.loads(riga)
            for riga in p.read_text(encoding="utf-8").splitlines()
            if riga.strip().startswith("{")]


def test_un_evento_emesso_SENZA_ambient_dice_lo_stesso_quale_store(journal):
    """La via che usano quasi tutti: `observability.emit` diretta."""
    observability.emit("banco.prova", quanti=3)
    righe = _righe(journal)
    assert righe, "nessuna riga scritta"
    assert righe[-1]["payload"].get("store"), righe[-1]["payload"]


def test_chi_porta_GIA_il_tag_se_lo_tiene(journal):
    """La cura e' additiva: `emit_flow` ha gia' l'impronta giusta e non
    va sovrascritta, altrimenti la cura del ramo curato lo scurerebbe."""
    observability.emit("banco.prova", store="IMPRONTA-SUA", quanti=1)
    assert _righe(journal)[-1]["payload"]["store"] == "IMPRONTA-SUA"


def test_il_journal_resta_leggibile_riga_per_riga(journal):
    """Il presidio contro la cura invadente: aggiungere un campo non deve
    rompere la forma del record (`name`, `payload`, `ts`)."""
    observability.emit("banco.prova", quanti=2)
    r = _righe(journal)[-1]
    assert set(r) >= {"name", "payload", "ts"}, r
    assert r["name"] == "banco.prova"
    assert r["payload"]["quanti"] == 2
