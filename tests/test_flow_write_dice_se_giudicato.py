"""Nel feed, «ammesso» e «verificato» non sono la stessa cosa.

`flow.write` portava `stored`, `status`, `topic` e le difese che hanno agito
— non il verdetto del moat. Quindi nella Engine Room un fatto giudicato
99.9 e un fatto MAI GIUDICATO comparivano identici: entrambi `ADMITTED`.

E i fatti mai giudicati esistono davvero: ws5 ha isolato il 2026-08-05 che
le scritture arrivate mentre il giudice si scalda entrano non giudicate —
lo dice `verimem doctor`, che in tre giorni non aveva lanciato nessuno di
noi cinque. Con `flow.warmup` quella finestra ora è visibile; questo evento
dice se la singola scrittura ci è caduta dentro.

Il prodotto stesso avverte che ``null`` significa MAI GIUDICATO, non
«giudicato e bocciato». Per questo l'evento porta anche `judged` esplicito:
un `grounding_score: null` in JSON si legge distrattamente come zero, e uno
zero è un verdetto — il contrario dell'assenza di verdetto.
"""
from __future__ import annotations

import json

import pytest

from verimem import event_jsonl_log, flow_events
from verimem.client import Memory

_GROUNDED = "the office headquarters are in Milan"
_FONTE = "Company handbook: our head office is located in Milan, Italy."


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    flow_events.reset_flow_context()
    return Memory(tmp_path / "memory.db"), tmp_path


def _write(tmp_path):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln)["payload"]
            for ln in p.read_text(encoding="utf-8").splitlines()
            if json.loads(ln).get("name") == "flow.write"]


def test_una_scrittura_con_fonte_dichiara_il_verdetto(mem):
    m, tmp = mem
    r = m.add(_GROUNDED, topic="hq", source=_FONTE)
    p = _write(tmp)[-1]
    assert p["judged"] is True, p
    assert p["grounding_score"] == r["grounding_score"]
    assert isinstance(p["grounding_score"], (int, float))


def test_una_scrittura_MAI_giudicata_lo_dichiara(mem):
    """Senza fonte il moat non gira: il fatto entra come claim, e il feed
    deve dirlo invece di mostrarlo uguale a uno verificato."""
    m, tmp = mem
    r = m.add(_GROUNDED, topic="hq", verified_by=["hr-doc"])
    assert r.get("grounding_score") is None, r
    p = _write(tmp)[-1]
    assert p["judged"] is False, p
    assert p["grounding_score"] is None, p


def test_judged_non_e_lo_stesso_di_ammesso(mem):
    """La proprietà in una riga: due scritture entrambe ammesse, una
    giudicata e una no — nel feed devono essere distinguibili."""
    m, tmp = mem
    m.add("the warehouse is in Turin", topic="wh", source=
          "Logistics sheet: the warehouse operates in Turin.")
    m.add("the branch is in Rome", topic="br", verified_by=["doc"])
    eventi = _write(tmp)
    ammessi = [p for p in eventi if p["stored"]]
    assert len(ammessi) == 2
    assert {p["judged"] for p in ammessi} == {True, False}, ammessi
