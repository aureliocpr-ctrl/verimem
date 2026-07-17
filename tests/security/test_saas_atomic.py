"""ATOMIC destructive pass — every remaining vector, one assertion each. Conversation
ingest fuzzing (found a 500 -> DoS, now 400), stored-content XSS on the rendered UI,
admin-plane payload fuzzing, JSON-depth DoS, numeric-param abuse, and CRLF header
injection. "Vai atomico."
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from verimem.gateway import GatewayKeys, create_app

_VB = {"topic": "t", "verified_by": ["source-doc:d:1"]}


def _auth(k):
    return {"Authorization": f"Bearer {k}"}


def _client(tmp_path, *, admin_key=None, llm=None):
    keys = GatewayKeys(tmp_path / "k.db")
    key = keys.create(tenant_id="acme", name="a", plan="enterprise")
    return TestClient(create_app(data_dir=tmp_path, keys=keys, admin_key=admin_key,
                                 llm=llm), raise_server_exceptions=False), key


# ---- conversation ingest: malformed message shapes must be 400, never 500 -----

@pytest.mark.parametrize("messages", [
    [123], [None], [[]], [{"role": "user"}], [{"content": "hi"}],
    [{"role": 1, "content": 2}], [{"role": "user", "content": {"nested": 1}}],
    ["a raw string not an object"], [{"role": "user", "content": None}],
])
def test_conversation_ingest_fuzzing_never_500s(tmp_path, messages):
    client, key = _client(tmp_path, llm=lambda *a, **k: "extracted")
    r = client.post("/v1/memories", headers=_auth(key),
                    json={"messages": messages, "topic": "t"})
    assert r.status_code < 500, f"crashable conversation path on {messages!r}"


# ---- stored-content XSS: a <script> fact must not render raw in the UI --------

def test_stored_script_is_not_reflected_raw_in_ui(tmp_path):
    client, key = _client(tmp_path)
    xss = "<script>alert(document.cookie)</script>"
    client.post("/v1/memories", headers=_auth(key),
                json={"content": f"Motto: {xss}", "topic": "brand", **_VB})
    for path in ("/dashboard", "/ui"):
        r = client.get(path, headers=_auth(key))
        assert r.status_code == 200
        assert xss not in r.text            # never echoed as live markup into HTML


# ---- admin-plane payload fuzzing: never 500 (400/422 for junk) ----------------

@pytest.mark.parametrize("body", [
    {}, {"tenant_id": {"x": 1}}, {"tenant_id": "../esc"}, {"tenant_id": "a" * 200},
    {"x": "y"}, {"tenant_id": ""}, {"tenant_id": "UPPER"},
])
def test_admin_create_tenant_fuzzing_never_500s(tmp_path, body):
    client, _ = _client(tmp_path, admin_key="ADMKEY")
    r = client.post("/admin/tenants", headers={"X-Admin-Key": "ADMKEY"}, json=body)
    assert r.status_code < 500


# ---- JSON-depth DoS + numeric-param abuse + CRLF header -----------------------

def test_deeply_nested_json_does_not_crash(tmp_path):
    client, key = _client(tmp_path)
    nest: object = {"content": "x", "topic": "t"}
    for _ in range(300):
        nest = {"a": nest}
    assert client.post("/v1/memories", headers=_auth(key), json=nest).status_code < 500


@pytest.mark.parametrize("params", [
    {"max_nodes": -1}, {"max_nodes": 99999999}, {"max_edges": -5},
    {"quarantine_limit": 0},
])
def test_numeric_params_are_bounded_not_500(tmp_path, params):
    client, key = _client(tmp_path)
    assert client.get("/v1/snapshot", headers=_auth(key),
                      params=params).status_code in (200, 422)


def test_crlf_in_auth_header_is_rejected(tmp_path):
    client, _ = _client(tmp_path)
    r = client.get("/v1/quota",
                   headers={"Authorization": "Bearer x\r\nX-Injected: 1"})
    assert r.status_code == 401                  # no auth, no header smuggling
