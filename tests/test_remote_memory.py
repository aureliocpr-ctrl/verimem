"""RemoteMemory — the thin client that makes N sessions share ONE memory server.

Architecture A (2026-07-20): multi-client on one SQLite file does not scale
(measured: throughput plateaus ~11 ops/s past 5 clients; every extra process
loads its own models). The fix is topological: ONE server process owns the
models + the store (the existing hardened gateway), and every other consumer
is a THIN client — no model load, no SQLite handle, just HTTP.

These tests run the REAL gateway in-process (FastAPI TestClient — no network,
no ports): the client is tested against the true production surface, not a
mock of our own imagination.
"""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from verimem.gateway import GatewayKeys, create_app  # noqa: E402
from verimem.remote import RemoteMemory  # noqa: E402


@pytest.fixture()
def gw(tmp_path):
    keys = GatewayKeys(tmp_path / "keys.db")
    api_key = keys.create(tenant_id="tenant-a")
    app = create_app(data_dir=tmp_path / "gwdata", keys=keys)
    client = TestClient(app)
    return client, api_key


def _remote(gw_fixture) -> RemoteMemory:
    client, api_key = gw_fixture
    return RemoteMemory("http://gateway.local", api_key, _client=client)


def test_health_probe(gw):
    rm = _remote(gw)
    assert rm.health() is True


def test_add_and_search_round_trip(gw):
    rm = _remote(gw)
    r = rm.add("The reserve tank holds 500 liters.", topic="ops/tank")
    assert r.get("stored") is True and r.get("id")
    hits = rm.search("reserve tank capacity", k=5)
    assert isinstance(hits, list) and hits
    texts = " ".join(str(h.get("text", "")) for h in hits)
    assert "500" in texts


def test_add_forwards_provenance_fields(gw):
    rm = _remote(gw)
    r = rm.add("Orion ships on version 4.0.0.", topic="eng/orion",
               verified_by=["source-doc:rel:1"], source="release notes v4",
               asserted_at=1784500000.0)
    assert r.get("stored") is True


def test_get_and_delete(gw):
    rm = _remote(gw)
    r = rm.add("Delete-me fact about widgets.", topic="tmp")
    fid = r["id"]
    got = rm.get(fid)
    assert got and got.get("id") == fid
    assert rm.delete(fid) is True
    assert rm.get(fid) is None


def test_wrong_key_raises_permission_error(gw):
    client, _good = gw
    rm = RemoteMemory("http://gateway.local", "vm_wrongkey", _client=client)
    with pytest.raises(PermissionError):
        rm.add("should not land", topic="x")


def test_server_down_raises_connection_error():
    rm = RemoteMemory("http://127.0.0.1:1", "vm_x", timeout_s=0.3)
    with pytest.raises(ConnectionError):
        rm.health(raise_on_down=True)
    assert rm.health() is False          # non-raising probe form


# ---- open_memory factory: env-driven thin-client switch -------------------

def test_open_memory_embedded_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("VERIMEM_SERVER_URL", raising=False)
    from verimem.client import Memory, open_memory
    m = open_memory(tmp_path / "m.db")
    assert isinstance(m, Memory)          # no server configured -> embedded


def test_open_memory_returns_thin_client_when_server_configured(monkeypatch):
    from verimem import client as C
    monkeypatch.setenv("VERIMEM_SERVER_URL", "http://memhost:8077")
    monkeypatch.setenv("VERIMEM_SERVER_KEY", "vm_abc")
    seen = {}

    class _FakeRemote:
        def __init__(self, url, key, timeout_s=None):
            seen["url"], seen["key"] = url, key
        def health(self, raise_on_down=False):
            return True
    monkeypatch.setattr(C, "_remote_cls", lambda: _FakeRemote)
    m = C.open_memory()
    assert isinstance(m, _FakeRemote)
    assert seen["url"] == "http://memhost:8077" and seen["key"] == "vm_abc"


def test_open_memory_falls_back_embedded_when_server_down(tmp_path, monkeypatch):
    from verimem import client as C
    monkeypatch.setenv("VERIMEM_SERVER_URL", "http://memhost:8077")
    monkeypatch.setenv("VERIMEM_SERVER_KEY", "vm_abc")

    class _DeadRemote:
        def __init__(self, url, key, timeout_s=None): ...
        def health(self, raise_on_down=False):
            return False
    monkeypatch.setattr(C, "_remote_cls", lambda: _DeadRemote)
    m = C.open_memory(tmp_path / "m.db")
    from verimem.client import Memory
    assert isinstance(m, Memory)          # fail-soft: never strand the caller
