"""Admin API + metering: il ponte da 'software' a 'servizio online'.

Per esporre trusted-memory-as-a-service serve: provisioning tenant via HTTP
(non SSH sull'host), contatori d'uso per tenant (fatturazione + abuse
detection), stats con le trust-metrics esposte, e un body-limit anti-DoS.
L'admin key è separata dalle chiavi tenant (env o parametro), mai hashata
insieme a loro, e senza di essa gli endpoint /admin/* NON ESISTONO (404
comportamento di default: un gateway senza admin key resta identico a prima).
"""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from engram.gateway import GatewayKeys, create_app  # noqa: E402

ADMIN = "adm_test_secret_0123456789"


@pytest.fixture()
def gw(tmp_path):
    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    app = create_app(data_dir=tmp_path, keys=keys, admin_key=ADMIN)
    return TestClient(app), keys


def _admin(k: str = ADMIN) -> dict[str, str]:
    return {"X-Admin-Key": k}


def test_admin_endpoints_absent_without_admin_key(tmp_path):
    app = create_app(data_dir=tmp_path)  # nessuna admin key
    client = TestClient(app)
    r = client.post("/admin/tenants", json={"tenant_id": "x"},
                    headers=_admin())
    assert r.status_code == 404, (
        "senza admin key configurata gli endpoint admin non esistono"
    )


def test_admin_key_required_and_constant_time(gw):
    client, _ = gw
    assert client.post("/admin/tenants", json={"tenant_id": "a"}).status_code == 401
    assert client.post("/admin/tenants", json={"tenant_id": "a"},
                       headers=_admin("wrong")).status_code == 401


def test_admin_provisions_tenant_and_key_over_http(gw):
    client, keys = gw
    r = client.post("/admin/tenants", headers=_admin(),
                    json={"tenant_id": "acme", "name": "pilot"})
    assert r.status_code == 200
    api_key = r.json()["api_key"]
    assert api_key.startswith("vm_"), "la chiave si vede UNA volta, qui"
    # la chiave funziona subito sul data plane
    ok = client.post("/v1/memories", headers={"Authorization": f"Bearer {api_key}"},
                     json={"content": "pilot fact", "verified_by": ["doc:x"]})
    assert ok.status_code == 200 and ok.json()["stored"] is True


def test_metering_counts_requests_per_tenant(gw):
    client, keys = gw
    key = client.post("/admin/tenants", headers=_admin(),
                      json={"tenant_id": "acme"}).json()["api_key"]
    h = {"Authorization": f"Bearer {key}"}
    client.post("/v1/memories", headers=h,
                json={"content": "f1", "verified_by": ["d:1"]})
    for _ in range(3):
        client.get("/v1/search", headers=h, params={"q": "f1"})
    stats = client.get("/admin/stats", headers=_admin()).json()
    acme = stats["tenants"]["acme"]
    assert acme["requests"] >= 4, "metering: add + 3 search contati"
    assert acme["writes"] >= 1 and acme["reads"] >= 3
    assert "stored_ok" in acme, "trust metric esposta: scritture ammesse"


def test_stats_requires_admin(gw):
    client, _ = gw
    assert client.get("/admin/stats").status_code == 401


def test_body_size_limit_returns_413(gw):
    client, _ = gw
    key = client.post("/admin/tenants", headers=_admin(),
                      json={"tenant_id": "big"}).json()["api_key"]
    huge = "x" * (2 * 1024 * 1024)  # 2 MB > limite default 1 MB
    r = client.post("/v1/memories",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"content": huge})
    assert r.status_code == 413, "body-limit anti-DoS sul data plane"


# ---- org view: i trust-ring di TUTTI i tenant in una chiamata ----------------

def test_admin_overview_aggregates_trust_per_tenant(gw):
    """La vista SaaS/azienda: per ogni tenant il suo ledger — ciò che
    l'admin console disegna (un ring per tenant). Solo admin key."""
    client, keys = gw
    k1 = keys.create(tenant_id="acme")
    k2 = keys.create(tenant_id="beta")
    client.post("/v1/memories", json={
        "content": "the office is in Milan", "topic": "hq",
        "verified_by": ["hr-doc"]},
        headers={"Authorization": f"Bearer {k1}"})
    client.post("/v1/memories", json={
        "content": "the deployment works and is verified in production"},
        headers={"Authorization": f"Bearer {k2}"})

    r = client.get("/admin/overview", headers=_admin())
    assert r.status_code == 200
    tenants = {t["tenant"]: t for t in r.json()["tenants"]}
    assert tenants["acme"]["ledger"]["admitted"] == 1
    assert tenants["beta"]["ledger"]["quarantined"] == 1
    assert "usage" in tenants["acme"]


def test_admin_overview_requires_admin_key(gw):
    client, _ = gw
    assert client.get("/admin/overview").status_code == 401
    assert client.get("/admin/overview",
                      headers=_admin("wrong")).status_code == 401


# ---- admin console: la pagina org (un ring per tenant) -----------------------

def test_admin_ui_served_only_with_admin_key(gw, tmp_path):
    client, _ = gw
    r = client.get("/admin/ui")
    assert r.status_code == 200, "la pagina è statica e senza dati"
    assert "text/html" in r.headers["content-type"]
    assert "tenant" in r.text.lower()
    js = client.get("/admin/ui/admin.js")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    # senza admin key configurata la pagina NON esiste (come /admin/*)
    from engram.gateway import create_app as _ca
    bare = TestClient(_ca(data_dir=tmp_path / "bare"))
    assert bare.get("/admin/ui").status_code == 404
