"""La scansione dei conflitti dice quanti ne ha trovati.

Ultima riga al buio della mappa camere. `scan_corpus` gira in due modi —
dalla manutenzione automatica ogni 4 ore e a mano da MCP — e non emetteva
niente: il numero di conflitti REGISTRATI cresceva senza che nessuna
superficie viva lo dicesse.

Perché conta adesso: la manutenzione **agisce** su quello che la
scansione registra (`heal_contradictions` supersede il lato debole, 5
fatti nella passata delle 23:07 del 2026-08-05), e ws4 ha campionato 25
contraddizioni a mano trovandone **zero vere**. Con l'evento, il tasso a
cui il rilevatore produce righe si vede mentre succede, invece che in una
query fatta apposta da qualcuno che sospettava.

⚠️ L'evento NON dice se un conflitto è vero: quello è il lavoro di ws4 e
non lo tocco. Dice quante righe ha prodotto la scansione e di che tipo —
`already_known` a parte, perché una scansione che ritrova 2495 conflitti
noti e ne aggiunge 31 sta facendo una cosa diversa da una che ne trova 31
su un corpus pulito.
"""
from __future__ import annotations

import json

import pytest

from verimem import event_jsonl_log, flow_events
from verimem.client import Memory


@pytest.fixture()
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    flow_events.reset_flow_context()
    return Memory(tmp_path / "m.db"), tmp_path


def _flow(tmp_path, name="flow.conflict"):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines()
            if json.loads(ln).get("name") == name]


def test_una_scansione_esce_sul_canale(banco):
    m, tmp = banco
    m.add("the warehouse holds 120 pallets", topic="log")
    m.add("the warehouse holds 340 pallets", topic="log2")

    from verimem.contradiction import scan_corpus
    out = scan_corpus(m.semantic, time_budget_s=5.0)

    evts = _flow(tmp)
    assert len(evts) == 1, "la scansione che alimenta i ritiri non puo' tacere"
    p = evts[0]["payload"]
    assert p["scanned_facts"] == out["scanned_facts"]
    assert p["new_detected"] == out["new_detected"]
    assert p["already_known"] == out["already_known"]


def test_porta_i_TIPI_non_solo_il_totale(banco):
    """Il totale da solo non dice niente: `numeric_clash` e
    `boolean_clash` si curano in modi diversi, e sul corpus reale sono
    2526 tutti dello stesso tipo — un dato che il totale nasconde."""
    m, tmp = banco
    m.add("the warehouse holds 120 pallets", topic="log")
    m.add("the warehouse holds 340 pallets", topic="log2")

    from verimem.contradiction import scan_corpus
    scan_corpus(m.semantic, time_budget_s=5.0)

    p = _flow(tmp)[-1]["payload"]
    assert isinstance(p["kinds"], dict), p


def test_l_evento_non_porta_il_testo_dei_fatti(banco):
    m, tmp = banco
    m.add("the warehouse holds 120 pallets", topic="log")
    m.add("the warehouse holds 340 pallets", topic="log2")

    from verimem.contradiction import scan_corpus
    scan_corpus(m.semantic, time_budget_s=5.0)

    testo = json.dumps(_flow(tmp)[-1]["payload"])
    assert "warehouse" not in testo and "pallets" not in testo


def test_una_scansione_su_corpus_vuoto_non_emette(banco):
    """Zero fatti guardati, zero notizie: un evento per una scansione a
    vuoto e' rumore, e la manutenzione la lancia ogni quattro ore."""
    m, tmp = banco
    from verimem.contradiction import scan_corpus
    scan_corpus(m.semantic, time_budget_s=5.0)
    assert _flow(tmp) == []
