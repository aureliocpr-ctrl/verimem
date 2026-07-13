"""Adversarial break-tests for the SaaS commercial surface (plans / quota / usage /
admin) added 2026-07-13. Each test ATTEMPTS an attack and asserts the SECURE outcome:
cross-tenant isolation, auth on every new endpoint, SQL-injection resistance, no
client-side plan escalation, and an admin plane that is absent without a key and
constant-time gated with one. "Have you tried to break it?" — yes, here.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from engram.gateway import GatewayKeys, create_app

_FACT = {"topic": "t", "verified_by": ["source-doc:d:1"]}


def _auth(k: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {k}"}


def _app(tmp_path, *, admin_key=None):
    keys = GatewayKeys(tmp_path / "k.db")
    ka = keys.create(tenant_id="alpha", name="a", plan="free")
    kb = keys.create(tenant_id="beta", name="b", plan="enterprise")
    return TestClient(create_app(data_dir=tmp_path, keys=keys,
                                 admin_key=admin_key)), ka, kb


def test_usage_and_quota_are_tenant_isolated(tmp_path):
    """Cross-tenant leak (the #1 SaaS risk): beta writes; alpha must see ONLY alpha."""
    client, ka, kb = _app(tmp_path)
    for i in range(3):
        client.post("/v1/memories", headers=_auth(kb),
                    json={"content": f"beta secret {i}.", **_FACT})
    ua = client.get("/v1/usage", headers=_auth(ka)).json()
    assert ua["tenant_id"] == "alpha" and ua["total"]["writes"] == 0   # not beta's
    qa = client.get("/v1/quota", headers=_auth(ka)).json()
    assert qa["plan"] == "free" and qa["facts_used"] == 0             # not beta's facts


def test_one_tenant_cannot_read_anothers_data(tmp_path):
    """The core SaaS guarantee: alpha must never retrieve beta's secret via search or
    explain — different keys, isolated stores."""
    client, ka, kb = _app(tmp_path)
    client.post("/v1/memories", headers=_auth(kb),
                json={"content": "Beta's secret API key is ZZZ-9987.", **_FACT})
    hits = client.get("/v1/search", headers=_auth(ka),
                      params={"q": "secret API key"}).json()["hits"]
    assert all("ZZZ-9987" not in (h.get("text") or "") for h in hits)
    rep = client.get("/v1/explain", headers=_auth(ka),
                     params={"q": "secret API key"}).json()
    assert all("ZZZ-9987" not in (f.get("proposition") or "")
               for f in rep.get("facts", []))


def test_new_endpoints_require_a_valid_key(tmp_path):
    client, _, _ = _app(tmp_path)
    for path in ("/v1/quota", "/v1/usage"):
        assert client.get(path).status_code == 401                   # no key
        assert client.get(path, headers=_auth("vm_forged")).status_code == 401


def test_usage_since_param_is_injection_safe(tmp_path):
    client, ka, _ = _app(tmp_path)
    r = client.get("/v1/usage", headers=_auth(ka),
                   params={"since": "'; DROP TABLE gateway_usage; --"})
    assert r.status_code == 200 and r.json()["total"]["writes"] == 0  # no error, no leak
    client.post("/v1/memories", headers=_auth(ka), json={"content": "ok.", **_FACT})
    assert client.get("/v1/usage", headers=_auth(ka)).json()["total"]["writes"] >= 1


def test_tenant_cannot_self_escalate_plan(tmp_path):
    """A client cannot smuggle a higher tier via the body or a header — the plan is
    server-side, bound to the key."""
    client, ka, _ = _app(tmp_path)
    client.post("/v1/memories",
                headers={**_auth(ka), "X-Plan": "enterprise"},
                json={"content": "x.", "plan": "enterprise", **_FACT})
    assert client.get("/v1/quota", headers=_auth(ka)).json()["plan"] == "free"


def test_admin_plane_absent_without_admin_key(tmp_path):
    client, ka, _ = _app(tmp_path)                                    # no admin_key
    assert client.post("/admin/tenants", headers=_auth(ka),
                       json={"tenant_id": "x"}).status_code == 404    # route not registered


def test_admin_plane_rejects_non_admin_when_enabled(tmp_path):
    client, ka, _ = _app(tmp_path, admin_key="s3cret-admin-key")
    assert client.post("/admin/tenants", headers=_auth(ka),
                       json={"tenant_id": "x"}).status_code in (401, 403)   # tenant key
    assert client.post("/admin/tenants", headers={"X-Admin-Key": "wrong"},
                       json={"tenant_id": "x"}).status_code in (401, 403)   # wrong admin
