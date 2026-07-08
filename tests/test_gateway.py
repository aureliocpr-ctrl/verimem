"""Self-host gateway REST (roadmap #3, scenario B "server di team").

Il gap dichiarato (fact 805158d9a8ee): il motore è multi-client-ready (SQLite
WAL, 500 processi) ma l'unico transport era MCP stdio locale + dashboard
loopback. Questo gateway espone l'SDK Memory via HTTP con:

  * auth API-key (chiavi hashate sha256 su SQLite, revocabili, mai in chiaro
    a riposo — la chiave si vede UNA volta alla creazione);
  * isolamento per tenant: un DB SQLite per tenant sotto data_dir/tenants/
    (lo sharding naturale del design); il tenant deriva SOLO dalla chiave,
    mai dalla richiesta;
  * gli endpoint core: add / search / explain / get / delete / health.
"""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from engram.gateway import GatewayKeys, create_app  # noqa: E402


@pytest.fixture()
def gw(tmp_path):
    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    key_a = keys.create(tenant_id="team-alpha", name="ci")
    key_b = keys.create(tenant_id="team-beta", name="laptop")
    app = create_app(data_dir=tmp_path, keys=keys)
    return TestClient(app), key_a, key_b, keys


def _auth(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


def test_health_needs_no_auth(gw):
    client, *_ = gw
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_missing_or_invalid_key_is_401(gw):
    client, *_ = gw
    assert client.get("/v1/search", params={"q": "x"}).status_code == 401
    r = client.get("/v1/search", params={"q": "x"},
                   headers=_auth("vm_definitely_not_a_key"))
    assert r.status_code == 401


def test_add_and_search_roundtrip_with_provenance(gw):
    client, key_a, *_ = gw
    r = client.post("/v1/memories", headers=_auth(key_a),
                    json={"content": "The deploy pipeline is green",
                          "verified_by": ["ci:main:green"]})
    assert r.status_code == 200
    body = r.json()
    assert body["stored"] is True and body["id"]

    r = client.get("/v1/search", headers=_auth(key_a),
                   params={"q": "deploy pipeline status", "k": 3})
    assert r.status_code == 200
    hits = r.json()["hits"]
    assert hits, "il fatto appena scritto deve tornare dal search"
    assert "status" in hits[0] and "text" in hits[0], "provenance sul read path"


def test_tenant_isolation(gw):
    client, key_a, key_b, _ = gw
    client.post("/v1/memories", headers=_auth(key_a),
                json={"content": "alpha secret roadmap milestone",
                      "verified_by": ["doc:alpha"]})
    r = client.get("/v1/search", headers=_auth(key_b),
                   params={"q": "alpha secret roadmap milestone"})
    assert r.status_code == 200
    texts = [h["text"] for h in r.json()["hits"]]
    assert all("alpha secret" not in t for t in texts), (
        "un tenant non deve MAI vedere i fatti di un altro"
    )


def test_revoked_key_is_401(gw):
    client, key_a, _, keys = gw
    [rec] = [k for k in keys.list() if k["tenant_id"] == "team-alpha"]
    keys.revoke(rec["key_id"])
    r = client.get("/v1/search", headers=_auth(key_a), params={"q": "x"})
    assert r.status_code == 401


def test_delete_with_purge(gw):
    client, key_a, *_ = gw
    fid = client.post("/v1/memories", headers=_auth(key_a),
                      json={"content": "temporary personal datum",
                            "verified_by": ["note:tmp"]}).json()["id"]
    r = client.delete(f"/v1/memories/{fid}", headers=_auth(key_a),
                      params={"purge_history": "true"})
    assert r.status_code == 200 and r.json()["removed"] is True
    assert client.get(f"/v1/memories/{fid}",
                      headers=_auth(key_a)).status_code == 404


def test_conversation_add_without_server_llm_is_400(gw):
    client, key_a, *_ = gw
    r = client.post("/v1/memories", headers=_auth(key_a),
                    json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 400
    assert "llm" in r.json()["detail"].lower()


def test_explain_returns_report(gw):
    client, key_a, *_ = gw
    r = client.get("/v1/explain", headers=_auth(key_a),
                   params={"q": "anything known?"})
    assert r.status_code == 200
    assert isinstance(r.json(), dict) and r.json(), "trust report json"


def test_rate_limit_per_key(tmp_path):
    """Fase 1 del design datacenter (docs/DATACENTER_DESIGN.md): rate-limit
    per chiave — oltre il tetto la risposta è 429 (con Retry-After), le altre
    chiavi NON sono toccate (isolamento anche sul limite)."""
    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    key_a = keys.create(tenant_id="team-alpha", name="ci")
    key_b = keys.create(tenant_id="team-beta", name="ci")
    app = create_app(data_dir=tmp_path, keys=keys, rate_limit_per_minute=3)
    client = TestClient(app)
    for _ in range(3):
        assert client.get("/v1/search", params={"q": "x"},
                          headers=_auth(key_a)).status_code == 200
    r = client.get("/v1/search", params={"q": "x"}, headers=_auth(key_a))
    assert r.status_code == 429
    assert "retry-after" in {k.lower() for k in r.headers}
    # un'altra chiave non è rate-limitata dal consumo della prima
    assert client.get("/v1/search", params={"q": "x"},
                      headers=_auth(key_b)).status_code == 200
    # health resta libero (liveness non autenticata, mai limitata)
    assert client.get("/v1/health").status_code == 200


def test_rate_limit_disabled_by_default(gw):
    client, key_a, *_ = gw
    for _ in range(30):
        assert client.get("/v1/search", params={"q": "x"},
                          headers=_auth(key_a)).status_code == 200


def test_key_is_hashed_at_rest(gw, tmp_path):
    _, key_a, _, keys = gw
    import sqlite3
    rows = sqlite3.connect(tmp_path / "gateway_keys.db").execute(
        "SELECT key_hash FROM gateway_keys").fetchall()
    assert rows and all(key_a not in r[0] for r in rows), (
        "la chiave in chiaro non deve MAI stare su disco"
    )
