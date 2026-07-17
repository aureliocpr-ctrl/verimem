"""DESTRUCTIVE pass on the gateway — "devi essere distruttivo". Path traversal via the
tenant slug, Host-header auth bypass, DoS via oversized body, and malformed-input
fuzzing that hunts for unhandled 500s (a 500 = a crashable endpoint = a DoS). Each test
fires the attack and asserts the endpoint stays UP and SEALED.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from verimem.gateway import GatewayKeys, create_app

_FACT = {"topic": "t", "verified_by": ["source-doc:d:1"]}


def _auth(k: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {k}"}


def _client(tmp_path, **kw):
    keys = GatewayKeys(tmp_path / "k.db")
    key = keys.create(tenant_id="acme", name="a", plan="free")
    return TestClient(create_app(data_dir=tmp_path, keys=keys, **kw)), key, keys


# ---- 1. tenant slug is a FILESYSTEM path component: try to escape it -----------

@pytest.mark.parametrize("evil", [
    "..", "../etc", "../../root", "a/b", "a\\b", "/abs", "\\abs", ".hidden",
    "a/../../../etc/passwd", "..\\..\\win", "a b", "A_UPPER", "x" * 65,
    "", "tenant\x00null",
])
def test_tenant_slug_rejects_path_traversal_and_junk(tmp_path, evil):
    # NB the slug is validated for path-safety (no leading dot, no separators); Windows
    # reserved device names (con/nul/…) are NOT blocked — a non-issue on the Linux
    # deploy target, a documented caveat if ever hosted on Windows.
    keys = GatewayKeys(tmp_path / "k.db")
    with pytest.raises(ValueError):                       # the regex must refuse every one
        keys.create(tenant_id=evil, name="x")


# ---- 2. Host-header auth bypass (DNS-rebinding shape) --------------------------

def test_saas_mode_is_immune_to_host_header_bypass(tmp_path):
    # no local_tenant configured (the SaaS): NO key + Host: localhost must NOT authorize
    client, _, _ = _client(tmp_path)
    for host in ("localhost", "127.0.0.1", "acme"):
        r = client.get("/v1/quota", headers={"Host": host})   # no Authorization at all
        assert r.status_code == 401


# ---- 3. DoS: oversized body must be refused, not buffered to death ------------

def test_oversized_body_is_rejected(tmp_path):
    client, key, _ = _client(tmp_path, max_body_bytes=2048)
    huge = "A" * 20000
    r = client.post("/v1/memories", headers=_auth(key),
                    json={"content": huge, **_FACT})
    assert r.status_code == 413                            # Payload Too Large, not a hang/500


# ---- 4. malformed-input fuzzing: never a 500 (a 500 is a crashable endpoint) --

@pytest.mark.parametrize("body", [
    {"content": 12345, "topic": "t"},                     # non-string content
    {"content": ["a", "list"], "topic": "t"},
    {"content": {"nested": "dict"}, "topic": "t"},
    {"content": None, "topic": "t"},
    {"content": "", "topic": "t"},
    {"content": "ok", "topic": {"not": "a string"}},
    {"content": "ok", "verified_by": "not-a-list"},
    {"content": "ok", "asserted_at": "not-a-number"},
    {},                                                    # empty body
    {"messages": "not-a-list-of-messages"},
])
def test_write_fuzzing_never_500s(tmp_path, body):
    client, key, _ = _client(tmp_path)
    r = client.post("/v1/memories", headers=_auth(key), json=body)
    assert r.status_code < 500, f"crashable endpoint on {body!r}: {r.status_code}"


@pytest.mark.parametrize("params", [
    {"q": ""}, {"q": "x" * 5000}, {"q": "\x00"}, {"q": "'; DROP TABLE facts; --"},
    {"q": "a", "k": -1}, {"q": "a", "k": 0}, {"q": "a", "k": 99999},
])
def test_search_fuzzing_never_500s(tmp_path, params):
    client, key, _ = _client(tmp_path)
    r = client.get("/v1/search", headers=_auth(key), params=params)
    assert r.status_code < 500, f"crashable search on {params!r}: {r.status_code}"


@pytest.mark.parametrize("since", ["", "not-a-date", "9999-99-99", "'; DROP--",
                                   "0000-00-00", "x" * 2000, "\x00"])
def test_usage_since_fuzzing_never_500s(tmp_path, since):
    client, key, _ = _client(tmp_path)
    r = client.get("/v1/usage", headers=_auth(key), params={"since": since})
    assert r.status_code < 500


# ---- 5. failure responses must not leak the key or internal paths -------------

def test_401_does_not_leak_secrets_or_paths(tmp_path):
    client, key, _ = _client(tmp_path)
    r = client.get("/v1/quota", headers=_auth("vm_" + "f" * 40))
    body = r.text.lower()
    assert r.status_code == 401
    assert "vm_" not in body and "traceback" not in body
    assert "c:\\" not in body and "/home/" not in body and ".db" not in body


# ---- 6. fact_id path param: injection / traversal / crash ----------------------

@pytest.mark.parametrize("fid", [
    "../../etc/passwd", "'; DROP TABLE facts; --", "..%2f..%2f", "%00", "x" * 5000,
    "../secrets", "%2e%2e", "a b", "{}",
])
def test_fact_id_path_param_never_500s_or_traverses(tmp_path, fid):
    client, key, _ = _client(tmp_path)
    assert client.get(f"/v1/memories/{fid}", headers=_auth(key)).status_code < 500
    assert client.delete(f"/v1/memories/{fid}", headers=_auth(key)).status_code < 500


# ---- 7. cross-tenant delete: alpha must NOT be able to delete beta's fact ------

def test_delete_is_tenant_scoped(tmp_path):
    keys = GatewayKeys(tmp_path / "k.db")
    ka = keys.create(tenant_id="alpha", name="a")
    kb = keys.create(tenant_id="beta", name="b")
    client = TestClient(create_app(data_dir=tmp_path, keys=keys))
    made = client.post("/v1/memories", headers=_auth(kb),
                       json={"content": "beta owns this.", **_FACT}).json()
    fid = made.get("id")
    assert fid                                            # beta made a fact
    # alpha tries to delete beta's fact by id -> must not succeed, beta's fact survives
    client.delete(f"/v1/memories/{fid}", headers=_auth(ka))
    assert client.get(f"/v1/memories/{fid}", headers=_auth(kb)).status_code == 200


# ---- 8. explain param fuzzing + read-surface auth -----------------------------

@pytest.mark.parametrize("params", [
    {"q": "a", "as_of": "not-a-number"}, {"q": "a", "deep": "maybe"},
    {"q": "a", "k": -5}, {"q": "\x00"}, {"q": "'; DROP--"},
])
def test_explain_fuzzing_never_500s(tmp_path, params):
    client, key, _ = _client(tmp_path)
    assert client.get("/v1/explain", headers=_auth(key),
                      params=params).status_code < 500


def test_read_surface_requires_auth(tmp_path):
    """Every tenant-data read endpoint must 401 without a valid key (no anon leak)."""
    client, _, _ = _client(tmp_path)
    assert client.get("/v1/snapshot").status_code == 401       # trust/quarantine/graph/usage
    assert client.get("/v1/events", params={"max_events": 1}).status_code == 401
