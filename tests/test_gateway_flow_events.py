"""LIVE ENGINE ROOM — il flusso VERO del motore, osservabile in diretta.

Mandato Aurelio 2026-07-15: "immaginati di vedere le informazioni live che
entrano ed escono e come entrano ed escono davvero". Questa suite copre il
canale che lo rende possibile, senza inventare nulla:

  1. ogni write dal gateway emette ``flow.write``  (status, stored, tenant)
  2. ogni read  dal gateway emette ``flow.recall`` (kind, n, best, abstained)
  3. ``GET /v1/events/flow`` — SSE che rigioca/streamma SOLO gli eventi del
     proprio tenant (privacy multi-tenant), con ``replay`` + ``max_events``
     per stream deterministici nei test (lezione 2026-07-10: uno stream
     infinito che ignora il disconnect IMPIANTA pytest).

Trasporto: observability.emit → event_jsonl_log (cross-process, già rotato).
"""
from __future__ import annotations

import json

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from verimem import event_jsonl_log  # noqa: E402
from verimem.gateway import GatewayKeys, create_app  # noqa: E402

# frase che il gate L1 storico declassa a quarantined (nessuna evidenza)
_UNSUPPORTED = "the deployment works and is verified in production"
_GROUNDED = "the Q3 revenue target is 4.2M euro"


@pytest.fixture()
def gw(tmp_path, monkeypatch):
    # jsonl isolato per test: il flow stream legge ESATTAMENTE questo file
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    client = TestClient(create_app(data_dir=tmp_path, keys=keys))
    api_key = keys.create(tenant_id="acme")
    hdr = {"Authorization": f"Bearer {api_key}"}
    return client, hdr, keys, tmp_path


def _flow_lines(tmp_path) -> list[dict]:
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        rec = json.loads(ln)
        if str(rec.get("name", "")).startswith("flow."):
            out.append(rec)
    return out


# ---- 1. write → flow.write --------------------------------------------------

def test_write_emits_flow_event_with_status_and_tenant(gw):
    client, hdr, _, tmp_path = gw
    r = client.post("/v1/memories", headers=hdr,
                    json={"content": _GROUNDED, "topic": "finance"})
    assert r.status_code == 200
    evts = [e for e in _flow_lines(tmp_path) if e["name"] == "flow.write"]
    assert len(evts) == 1
    p = evts[0]["payload"]
    assert p["tenant"] == "acme"
    assert p["stored"] is True
    assert p["status"]  # es. "model_claim"/"verified" — mai vuoto
    assert p["fact_id"]


def test_quarantined_write_emits_flow_event_with_quarantined_status(gw):
    """NB: un fatto quarantinato È scritto (nel ledger, escluso dal recall) —
    stored resta True; è lo STATUS che racconta il verdetto del gate."""
    client, hdr, _, tmp_path = gw
    r = client.post("/v1/memories", headers=hdr,
                    json={"content": _UNSUPPORTED, "topic": "deploy"})
    assert r.status_code == 200
    assert r.json()["status"] == "quarantined"      # stesso contratto di /ui
    evts = [e for e in _flow_lines(tmp_path) if e["name"] == "flow.write"]
    assert len(evts) == 1
    p = evts[0]["payload"]
    assert p["status"] == "quarantined"
    assert isinstance(p["stored"], bool)


# ---- 2. read → flow.recall --------------------------------------------------

def test_search_emits_flow_recall(gw):
    client, hdr, _, tmp_path = gw
    client.post("/v1/memories", headers=hdr,
                json={"content": _GROUNDED, "topic": "finance"})
    r = client.get("/v1/search", headers=hdr,
                   params={"q": "Q3 revenue target", "k": 3})
    assert r.status_code == 200
    evts = [e for e in _flow_lines(tmp_path) if e["name"] == "flow.recall"]
    assert len(evts) == 1
    p = evts[0]["payload"]
    assert p["tenant"] == "acme"
    assert p["kind"] == "search"
    assert p["n"] >= 1
    assert 0.0 <= p["best"] <= 1.0


def test_explain_emits_flow_recall_with_abstained_flag(gw):
    client, hdr, _, tmp_path = gw
    r = client.get("/v1/explain", headers=hdr,
                   params={"q": "what did the CEO say in the private 1:1"})
    assert r.status_code == 200
    evts = [e for e in _flow_lines(tmp_path) if e["name"] == "flow.recall"]
    assert len(evts) == 1
    p = evts[0]["payload"]
    assert p["kind"] == "explain"
    assert isinstance(p["abstained"], bool)   # empty store + floor → True


# ---- 3. SSE /v1/events/flow --------------------------------------------------

def test_flow_stream_requires_auth(gw):
    client, _, _, _ = gw
    assert client.get("/v1/events/flow").status_code == 401


def test_flow_stream_replays_own_tenant_events_only(gw):
    client, hdr, keys, tmp_path = gw
    # tenant estraneo scrive: il suo evento NON deve comparire nel mio stream
    other_hdr = {"Authorization": f"Bearer {keys.create(tenant_id='beta')}"}
    client.post("/v1/memories", headers=other_hdr,
                json={"content": _GROUNDED, "topic": "finance"})
    client.post("/v1/memories", headers=hdr,
                json={"content": _GROUNDED, "topic": "finance"})

    lines: list[dict] = []
    with client.stream("GET", "/v1/events/flow",
                       params={"replay": 10, "max_events": 1},
                       headers=hdr) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        for raw in resp.iter_lines():
            if raw.startswith("data: "):
                lines.append(json.loads(raw[len("data: "):]))
    assert len(lines) == 1
    evt = lines[0]
    assert evt["name"] == "flow.write"
    assert evt["payload"]["tenant"] == "acme"      # mai il tenant 'beta'


def test_flow_stream_serves_engine_page(gw):
    """La pagina live è servita dalla webui del gateway: /ui/engine."""
    client, _, _, _ = gw
    r = client.get("/ui/engine")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Engine Room" in r.text


def test_personal_console_sees_local_untenanted_events(tmp_path, monkeypatch):
    """`verimem console` (personal mode, loopback, no keys): il local tenant
    vede anche gli eventi flow SENZA tenant — cioè l'attività sdk/mcp della
    macchina (Claude Code, codex, ...). In multi-tenant il filtro resta
    stretto (test sopra): un tenant vero non vede MAI eventi altrui."""
    from verimem.client import Memory
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    # un evento come lo emette l'SDK/MCP: nessun campo tenant
    event_jsonl_log.append_event(
        "flow.write", {"stored": True, "status": "model_claim",
                       "fact_id": "abc12345", "topic": "hq",
                       "surface": "mcp", "actor": "claude-code"})
    mem = Memory(tmp_path / "own.db")
    app = create_app(data_dir=tmp_path / "console",
                     local_tenant="local", local_memory=mem)
    client = TestClient(app)
    lines: list[dict] = []
    with client.stream("GET", "/v1/events/flow",
                       params={"replay": 5, "max_events": 1},
                       headers={"host": "127.0.0.1"}) as resp:   # loopback guard
        assert resp.status_code == 200
        for raw in resp.iter_lines():
            if raw.startswith("data: "):
                lines.append(json.loads(raw[len("data: "):]))
    assert len(lines) == 1
    assert lines[0]["payload"]["actor"] == "claude-code"
