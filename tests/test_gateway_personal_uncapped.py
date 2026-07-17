"""Personal mode (verimem console) must be UNCAPPED — found live 2026-07-16.

Real-traffic e2e (console on the operator's own store, 4499 facts): POST
/v1/memories returned **402 "fact quota exceeded for plan 'free'"** — the
single-user loopback console was billing-gated like a SaaS tenant, so any
self-host user with >1000 facts silently loses the ability to write from
their own console. The local tenant is the OPERATOR on their OWN machine:
plan quotas exist to protect the SaaS, not to cap the owner. Personal mode
therefore resolves to the uncapped ``self_host`` plan (write path AND the
/v1/quota self-service view, which must tell the same story).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from verimem.client import Memory
from verimem.gateway import GatewayKeys, create_app
from verimem.semantic import SemanticMemory


def _app(tmp_path, monkeypatch) -> TestClient:
    personal = Memory(path=tmp_path / "personal.db")
    # simulate a well-used store (>free cap) without 1001 real writes
    monkeypatch.setattr(SemanticMemory, "count", lambda self: 5000)
    app = create_app(data_dir=tmp_path, keys=GatewayKeys(tmp_path / "k.db"),
                     admin_key="adm", local_tenant="op", local_memory=personal)
    return TestClient(app, base_url="http://localhost")


def test_personal_write_never_402s_on_own_store(tmp_path, monkeypatch):
    c = _app(tmp_path, monkeypatch)
    r = c.post("/v1/memories",
               json={"content": "self-host fact past the free cap",
                     "topic": "infra"})
    assert r.status_code != 402, f"personal console billing-gated: {r.text}"
    assert r.status_code == 200


def test_personal_quota_view_reports_uncapped_self_host(tmp_path, monkeypatch):
    c = _app(tmp_path, monkeypatch)
    r = c.get("/v1/quota")
    assert r.status_code == 200
    q = r.json()
    assert q["plan"] == "self_host"
    assert q["facts_limit"] is None
    assert q["facts_over_limit"] is False
