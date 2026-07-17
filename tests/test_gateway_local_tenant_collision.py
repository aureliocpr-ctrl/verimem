"""opus tenant-pass MED-2: a provisioned tenant_id == local_tenant would resolve
onto the operator's PERSONAL store (pre-seeded in the cache) — a cross-store leak.
Provisioning must refuse the reserved personal id; normal tenants still work.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from verimem.client import Memory
from verimem.gateway import GatewayKeys, create_app

ADMIN = "admin-secret-xyz"


def _h(k: str = ADMIN) -> dict[str, str]:
    return {"X-Admin-Key": k}


def _app(tmp_path):
    keys = GatewayKeys(tmp_path / "k.db")
    personal = Memory(path=tmp_path / "personal.db")
    app = create_app(data_dir=tmp_path, keys=keys, admin_key=ADMIN,
                     local_tenant="operator", local_memory=personal)
    return TestClient(app)


def test_cannot_provision_reserved_local_tenant(tmp_path):
    c = _app(tmp_path)
    r = c.post("/admin/tenants", headers=_h(), json={"tenant_id": "operator"})
    assert r.status_code == 400, f"reserved local_tenant was provisioned: {r.text}"
    assert "reserved" in r.text.lower()


def test_normal_tenant_still_provisions(tmp_path):
    c = _app(tmp_path)
    r = c.post("/admin/tenants", headers=_h(), json={"tenant_id": "acme"})
    assert r.status_code == 200
    assert r.json()["api_key"].startswith("vm_")


def test_host_only_parses_ipv6_loopback():
    # opus LOW-6: rsplit(":",1)[0] broke IPv6; the loopback client must resolve.
    from verimem.gateway import _LOCAL_HOSTS, _host_only
    assert _host_only("[::1]") == "[::1]"
    assert _host_only("[::1]:8080") == "[::1]"
    assert _host_only("127.0.0.1:8377") == "127.0.0.1"
    assert _host_only("::1") == "::1"
    assert _host_only("[::1]").lower() in _LOCAL_HOSTS
    assert _host_only("::1").lower() in _LOCAL_HOSTS
