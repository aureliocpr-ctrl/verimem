"""Il governo si accende da solo, e questo test lo pretende.

ws3 ha censito il 2026-08-07 la classe «dichiarato ma spento»: il routing
temporale di ws5 esisteva, funzionava, e non si accendeva mai — e il
censimento ha preso anche `explain`, che era una cura a metà. ws2 l'ha
trovata pure nel tier episodi (la salienza si calcola, si persiste, si
mostra… e non si usa).

Ho censito il mio perimetro e la risposta è che **non c'è nessun
interruttore**: `observability.emit` scrive sempre, `append_event` non ha
gate, la rotta SSE non ne ha uno, e l'audit del gateway è una scelta
DICHIARATA (ON per un servizio, OFF per la console personale, col motivo
scritto).

Ma «l'ho guardato» non è una garanzia: è una fotografia. Questo test è la
garanzia — azzera ogni variabile `ENGRAM_*` / `HIPPO_*` e pretende che le
quattro azioni di governo escano comunque sul canale. Il giorno in cui
qualcuno mette la telemetria dietro un flag, cade qui invece che in
produzione, dove il sintomo sarebbe «la sala motore è vuota» e la causa
sarebbe cercata ovunque tranne che in un default.
"""
from __future__ import annotations

import json
import os

import pytest

from verimem import event_jsonl_log, flow_events
from verimem.client import Memory

_AMBIENTE = ("ENGRAM_", "HIPPO_", "VERIMEM_")


@pytest.fixture()
def nudo(tmp_path, monkeypatch):
    """Un processo SENZA configurazione: nessuna variabile del prodotto."""
    for k in [k for k in os.environ if k.startswith(_AMBIENTE)]:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    flow_events.reset_flow_context()
    return Memory(tmp_path / "m.db"), tmp_path


def _nomi(tmp_path) -> list[str]:
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln).get("name")
            for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_le_quattro_azioni_di_governo_escono_senza_configurare_niente(nudo):
    m, tmp = nudo
    a = m.add("the depot holds 10 crates", topic="log/a")["id"]
    b = m.add("the depot holds 20 crates", topic="log/b")["id"]
    c = m.add("the yard holds 5 pallets", topic="y/c")["id"]

    m.semantic.supersede(a, b, principal="test", reason="banco")
    m.semantic.quarantine_fact(c, reason="banco")
    m.semantic.delete(c, principal="test", action="forget")

    nomi = set(_nomi(tmp))
    for atteso in ("flow.write", "flow.supersession", "flow.quarantine",
                   "flow.forget"):
        assert atteso in nomi, f"{atteso} non e' uscito: {sorted(nomi)}"


def test_l_evento_di_scrittura_porta_il_verdetto_anche_senza_configurazione(
        nudo):
    """Non basta che l'evento esca: deve uscire COMPLETO. Un campo di
    governo che compare solo con una variabile impostata è la stessa
    classe, un piano più in basso."""
    m, tmp = nudo
    m.add("the depot holds 10 crates", topic="log/a")

    p = json.loads([ln for ln in
                    (tmp / "events.jsonl").read_text(encoding="utf-8")
                    .splitlines()
                    if json.loads(ln).get("name") == "flow.write"][-1])["payload"]
    for campo in ("status", "judged", "grounding_score",
                  "withheld_despite_judge"):
        assert campo in p, f"manca {campo}: {sorted(p)}"


def test_le_query_di_governo_rispondono_senza_configurazione(nudo):
    """Le viste read-only non devono chiedere nulla all'ambiente: chi apre
    un corpus altrui non ha le variabili di chi l'ha scritto."""
    from verimem.retirement_log import (
        quarantine_breakdown,
        retirement_breakdown,
        survivability_counts,
    )

    m, _ = nudo
    a = m.add("the depot holds 10 crates", topic="log/a")["id"]
    b = m.add("the depot holds 20 crates", topic="log/b")["id"]
    m.semantic.supersede(a, b, principal="test", reason="banco")

    assert survivability_counts(m.semantic)["retired"] == 1
    assert retirement_breakdown(m.semantic)["total_retired"] == 1
    assert quarantine_breakdown(m.semantic)["quarantined"] == 0
