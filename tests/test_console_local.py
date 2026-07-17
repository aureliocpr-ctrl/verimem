"""``verimem console`` — la trust console per l'UTENTE SINGOLO, zero config.

Visione Aurelio 2026-07-10: il sistema visivo deve esserci SEMPRE — SaaS,
azienda, utente singolo. Il buco era l'utente singolo: chi fa solo
``pip install verimem`` non ha gateway, chiavi, tenant — ma la sua memoria
lavora uguale e deve poterla VEDERE.

Modalità personale del gateway: ``create_app(local_tenant=..., local_memory=
...)`` — le richieste SENZA chiave risolvono al tenant locale, montato sul
suo store ESISTENTE (non un tenants/ nuovo). Sicurezza del modello "jupyter
locale": il comando binda SOLO 127.0.0.1 e l'header Host deve essere
localhost (anti DNS-rebinding); una chiave presentata vince sempre sul
fallback locale; senza ``local_tenant`` il gateway multi-tenant è
byte-identico a prima (401).
"""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from verimem.client import Memory  # noqa: E402
from verimem.gateway import GatewayKeys, create_app  # noqa: E402

_UNSUPPORTED = "the deployment works and is verified in production"


@pytest.fixture()
def local(tmp_path):
    mem = Memory(tmp_path / "my_store.db")
    mem.add("the office is in Milan", topic="hq", verified_by=["hr-doc"])
    mem.add(_UNSUPPORTED)
    app = create_app(data_dir=tmp_path / "gw",
                     keys=GatewayKeys(tmp_path / "gw" / "keys.db"),
                     local_tenant="local", local_memory=mem)
    return TestClient(app, base_url="http://127.0.0.1")


def test_local_mode_stats_without_key(local):
    r = local.get("/v1/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant"] == "local"
    assert body["trust"]["ledger"]["admitted"] == 1
    assert body["trust"]["ledger"]["quarantined"] == 1


def test_local_mode_quarantine_and_graph_without_key(local):
    q = local.get("/v1/quarantine")
    assert q.status_code == 200
    assert any(i["proposition"] == _UNSUPPORTED for i in q.json()["items"])
    g = local.get("/v1/graph")
    assert g.status_code == 200
    assert "nodes" in g.json(), "il KG deriva dallo store locale"


def test_local_mode_rejects_non_localhost_host_header(tmp_path):
    """Anti DNS-rebinding: evil.example che punta a 127.0.0.1 NON entra."""
    mem = Memory(tmp_path / "m.db")
    app = create_app(data_dir=tmp_path / "gw",
                     keys=GatewayKeys(tmp_path / "gw" / "keys.db"),
                     local_tenant="local", local_memory=mem)
    evil = TestClient(app, base_url="http://evil.example")
    assert evil.get("/v1/stats").status_code == 401


def test_presented_key_wins_over_local_fallback(tmp_path):
    """Una chiave valida risolve al SUO tenant anche in modalità locale."""
    keys = GatewayKeys(tmp_path / "gw" / "keys.db")
    mem = Memory(tmp_path / "m.db")
    app = create_app(data_dir=tmp_path / "gw", keys=keys,
                     local_tenant="local", local_memory=mem)
    c = TestClient(app, base_url="http://127.0.0.1")
    key = keys.create(tenant_id="acme")
    r = c.get("/v1/stats", headers={"Authorization": f"Bearer {key}"})
    assert r.json()["tenant"] == "acme"


def test_without_local_tenant_gateway_unchanged(tmp_path):
    app = create_app(data_dir=tmp_path / "gw",
                     keys=GatewayKeys(tmp_path / "gw" / "keys.db"))
    c = TestClient(app, base_url="http://127.0.0.1")
    assert c.get("/v1/stats").status_code == 401, (
        "multi-tenant puro: nessun fallback senza chiave")


# ---- l'occhio per l'AI: tutto lo stato in UNA chiamata -----------------------

def test_snapshot_returns_everything_in_one_call(local):
    r = local.get("/v1/snapshot")
    assert r.status_code == 200
    b = r.json()
    assert b["tenant"] == "local"
    assert b["trust"]["ledger"]["admitted"] == 1
    assert any(i["proposition"] == _UNSUPPORTED for i in b["quarantine"])
    assert "nodes" in b["graph"] and "edges" in b["graph"]
    assert "usage" in b


# ---- SSE: vedere la memoria LAVORARE, non solo com'era -----------------------

def test_events_stream_emits_initial_ledger(local):
    """``max_events=1``: lo stream si CHIUDE dopo il primo evento — il test
    è deterministico (uno stream infinito che ignora il disconnect
    impiantava pytest: bug reale trovato da questo test, 2026-07-10)."""
    import json as _j
    r = local.get("/v1/events?max_events=1")
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    data_lines = [ln for ln in r.text.splitlines() if ln.startswith("data: ")]
    assert len(data_lines) == 1
    payload = _j.loads(data_lines[0][len("data: "):])
    assert payload["ledger"]["admitted"] == 1
    assert payload["ledger"]["quarantined"] == 1


def test_events_requires_auth_in_multitenant_mode(tmp_path):
    app = create_app(data_dir=tmp_path / "gw",
                     keys=GatewayKeys(tmp_path / "gw" / "keys.db"))
    c = TestClient(app, base_url="http://127.0.0.1")
    assert c.get("/v1/events").status_code == 401
