"""FLOW EVENTS AL CORE — la Live Engine Room vede OGNI superficie.

Mandato Aurelio 2026-07-15: "guardarla dall'interno dell'app mentre lavori
live... e tramite la CLI? e gli altri agenti degli altri fornitori?".
Il gateway già emetteva flow.*; questo blocco sposta l'emissione nel CORE
(`Memory.add/search/explain`) così gateway, MCP server, SDK e QUALUNQUE
agente di qualunque fornitore che monta l'MCP scrivono gli stessi eventi
su events.jsonl — un pannello unico.

Tagging: ``surface`` (sdk|mcp|gateway, da env ENGRAM_FLOW_SURFACE o context),
``actor`` (da env VERIMEM_ACTOR/ENGRAM_ACTOR — l'etichetta dell'agente),
``tenant`` (solo gateway, via set_flow_context). Best-effort: l'osservabilità
non rompe MAI il write/read path.
"""
from __future__ import annotations

import json

import pytest

from verimem import event_jsonl_log, flow_events
from verimem.client import Memory

_UNSUPPORTED = "the deployment works and is verified in production"
_GROUNDED = "the office headquarters are in Milan"


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.delenv("VERIMEM_ACTOR", raising=False)
    monkeypatch.delenv("ENGRAM_ACTOR", raising=False)
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    flow_events.reset_flow_context()
    m = Memory(tmp_path / "memory.db")
    return m, tmp_path


def _flow(tmp_path, name=None):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        rec = json.loads(ln)
        if str(rec.get("name", "")).startswith("flow.") and (
                name is None or rec["name"] == name):
            out.append(rec)
    return out


# ---- write path --------------------------------------------------------------

def test_sdk_add_emits_flow_write_admitted(mem):
    m, tmp = mem
    res = m.add(_GROUNDED, topic="hq", verified_by=["hr-doc"])
    assert res["stored"] is True
    evts = _flow(tmp, "flow.write")
    assert len(evts) == 1
    p = evts[0]["payload"]
    assert p["status"] == res["status"]
    assert p["fact_id"] == res["id"]
    assert p["topic"] == "hq"
    assert p["surface"] == "sdk"           # default: direct SDK use
    assert "tenant" not in p               # no gateway → no tenant field


def test_sdk_add_emits_flow_write_quarantined(mem):
    m, tmp = mem
    res = m.add(_UNSUPPORTED, topic="deploy")
    assert res["status"] == "quarantined"
    p = _flow(tmp, "flow.write")[0]["payload"]
    assert p["status"] == "quarantined"


# ---- read path ---------------------------------------------------------------

def test_sdk_search_emits_flow_recall(mem):
    m, tmp = mem
    m.add(_GROUNDED, topic="hq", verified_by=["hr-doc"])
    hits = m.search("where are the headquarters", k=3)
    evts = _flow(tmp, "flow.recall")
    assert len(evts) == 1
    p = evts[0]["payload"]
    assert p["kind"] == "search"
    assert p["n"] == len(hits)
    assert 0.0 <= p["best"] <= 1.0


def test_sdk_explain_emits_flow_recall_with_abstained(mem):
    m, tmp = mem
    report = m.explain("what did the CEO say in the private 1:1",
                       min_relevance=0.99)
    evts = _flow(tmp, "flow.recall")
    assert len(evts) == 1
    p = evts[0]["payload"]
    assert p["kind"] == "explain"
    assert p["abstained"] == bool(report.get("abstained"))


# ---- tagging: actor (multi-vendor agents) + surface + tenant ------------------

def test_actor_env_labels_the_agent(mem, monkeypatch):
    """Un agente di un altro fornitore setta VERIMEM_ACTOR nel suo config MCP
    e ogni suo evento arriva etichettato — il pannello unico multi-agente."""
    m, tmp = mem
    monkeypatch.setenv("VERIMEM_ACTOR", "codex")
    m.add(_GROUNDED, topic="hq", verified_by=["hr-doc"])
    p = _flow(tmp, "flow.write")[0]["payload"]
    assert p["actor"] == "codex"


def test_surface_env_overrides_default(mem, monkeypatch):
    m, tmp = mem
    monkeypatch.setenv("ENGRAM_FLOW_SURFACE", "mcp")
    m.add(_GROUNDED, topic="hq", verified_by=["hr-doc"])
    assert _flow(tmp, "flow.write")[0]["payload"]["surface"] == "mcp"


def test_flow_context_merges_tenant(mem):
    """Il gateway setta tenant+surface via context: il core li include."""
    m, tmp = mem
    tok = flow_events.set_flow_context(tenant="acme", surface="gateway")
    try:
        m.add(_GROUNDED, topic="hq", verified_by=["hr-doc"])
    finally:
        flow_events.reset_flow_context(tok)
    p = _flow(tmp, "flow.write")[0]["payload"]
    assert p["tenant"] == "acme"
    assert p["surface"] == "gateway"
    # e DOPO il reset il contesto non "sanguina" sulla chiamata successiva
    m.add("the office cafeteria is on floor 2", topic="hq",
          verified_by=["hr-doc"])
    p2 = _flow(tmp, "flow.write")[1]["payload"]
    assert "tenant" not in p2
