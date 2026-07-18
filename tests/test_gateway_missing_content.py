"""Silent-drop guard on POST /v1/memories (vertical probe 2026-07-18).

The write endpoint reads the fact from ``content`` (string) or ``messages``
(list). A client that POSTs a plausible-but-wrong field name — ``{"text":
"..."}`` — hit neither branch, so ``content`` defaulted to "" and the write
returned ``200 {stored:false, status:"empty", advice:"empty text"}``. From the
caller's side that is SILENT DATA LOSS: a 2xx, an "empty text" reason that
contradicts the non-empty payload sent, and the fact simply gone.

Enterprise ingest ("how are inbound data handled") must not drop a write
silently. A body carrying NEITHER ``content`` NOR ``messages`` is a client
schema error → 400 that names the correct fields (and points at the unknown
content-like key when present). A genuinely empty ``content:""`` is unchanged.
"""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from verimem.gateway import GatewayKeys, create_app  # noqa: E402


@pytest.fixture()
def gw(tmp_path):
    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    key = keys.create(tenant_id="t", name="ci")
    app = create_app(data_dir=tmp_path, keys=keys)
    return TestClient(app, raise_server_exceptions=False), key


def _auth(key):
    return {"Authorization": f"Bearer {key}"}


def test_wrong_field_name_is_400_not_silent_drop(gw):
    client, key = gw
    r = client.post("/v1/memories",
                    json={"text": "Alice vive a Berlino dal marzo 2024.",
                          "topic": "people"},
                    headers=_auth(key))
    assert r.status_code == 400, (
        f"a body with a content-like unknown field must be a 400 schema error, "
        f"not a silent 200 drop — got {r.status_code}: {r.text}"
    )
    detail = str(r.json().get("detail", "")).lower()
    assert "content" in detail and "messages" in detail, (
        f"the 400 must name the correct fields, got: {detail}"
    )
    assert "text" in detail, (
        f"the 400 should point at the unknown content-like key 'text', got: {detail}"
    )


def test_completely_empty_body_is_400(gw):
    client, key = gw
    r = client.post("/v1/memories", json={}, headers=_auth(key))
    assert r.status_code == 400, (
        f"an empty body provides no fact — must be 400, got {r.status_code}"
    )


def test_explicit_empty_content_unchanged(gw):
    """Contract preserved: content present but empty stays a 200 no-op (the
    caller DID address the field; this is not a schema error)."""
    client, key = gw
    r = client.post("/v1/memories", json={"content": "", "topic": "t"},
                    headers=_auth(key))
    assert r.status_code == 200, r.text
    assert r.json().get("stored") is False


def test_valid_content_still_works(gw):
    """The happy path must be untouched."""
    client, key = gw
    r = client.post("/v1/memories",
                    json={"content": "Deploy pipeline verde.",
                          "verified_by": ["ci:main:green"], "topic": "ops"},
                    headers=_auth(key))
    assert r.status_code == 200, r.text
    assert r.json().get("stored") is True
