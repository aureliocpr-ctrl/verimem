"""GET /v1/correct — the guardian's gateway surface (critic gap, 2026-07-17).

The mod.3 critic's caller-verification worker found `guardian.correct_read` had
ZERO production callers — README/receipt #8 said "read-path guardian" but no
runtime path invoked it (SDK/tests/docs only). Same anti-fuffa pattern as
answer() the day before: either the claim goes down or the wire goes in. This
is the wire: tenant-scoped, flow context, meter, no LLM needed (the guardian is
deterministic) — so it works on the personal console too.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from engram.client import Memory
from engram.gateway import GatewayKeys, create_app


def _client(tmp_path) -> TestClient:
    keys = GatewayKeys(tmp_path / "k.db")
    personal = Memory(path=tmp_path / "personal.db")
    app = create_app(data_dir=tmp_path, keys=keys, admin_key="adm",
                     local_tenant="op", local_memory=personal)
    return TestClient(app, base_url="http://localhost"), personal


def test_correct_accept_on_unchallenged_fact(tmp_path):
    c, mem = _client(tmp_path)
    mem.add("Rex is a labrador.", topic="pets",
            verified_by=["source-doc:alice:t1"])
    r = c.get("/v1/correct", params={"q": "What breed is Rex?"})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "ACCEPT"
    assert "labrador" in body["answer"]


def test_correct_abstains_on_real_conflict(tmp_path):
    c, mem = _client(tmp_path)
    mem.add("Rex is a labrador.", topic="pets",
            verified_by=["source-doc:alice:t1"])
    mem.add("Rex is a poodle.", topic="pets",
            verified_by=["source-doc:bob:t1"])
    r = c.get("/v1/correct", params={"q": "What breed is Rex?"})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "ABSTAIN"
    assert body["answer"] is None
    assert len(body["evidence"]) == 2          # the conflict is SHOWN


def test_correct_empty_store_abstains(tmp_path):
    c, _ = _client(tmp_path)
    r = c.get("/v1/correct", params={"q": "anything?"})
    assert r.status_code == 200
    assert r.json()["verdict"] == "ABSTAIN"
    assert r.json()["reason"] == "no_support"
