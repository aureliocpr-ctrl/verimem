"""Last two red-team findings (F7, F11).

F7 — the gateway took `ground` and `gate_mode` straight from the request body,
so the caller could weaken or skip the very gate the product is built on. "Facts
pass a grounding moat" was opt-OUT by whoever was writing. The server owns the
gate; a client asking to disable it is asking the wrong party.

F11 — the thin client sent its API key over whatever scheme the URL carried, so
`http://memory.example.com` shipped the bearer token in cleartext. Loopback http
is fine (no network hop); anything else must be https unless an operator has
explicitly, knowingly opted out.
"""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from verimem.gateway import GatewayKeys, create_app  # noqa: E402
from verimem.remote import RemoteMemory  # noqa: E402

# ---- F7: the client cannot turn the moat off ------------------------------

@pytest.fixture()
def gw(tmp_path):
    keys = GatewayKeys(tmp_path / "keys.db")
    api_key = keys.create(tenant_id="tenant-moat")
    app = create_app(data_dir=tmp_path / "gwdata", keys=keys)
    return TestClient(app), api_key


def test_client_cannot_disable_the_grounding_gate(gw, monkeypatch):
    client, api_key = gw
    seen: dict = {}
    from verimem.client import Memory
    _orig = Memory.add

    def _spy(self, content=None, **kw):
        seen.update(kw)
        return _orig(self, content, **kw)

    monkeypatch.setattr(Memory, "add", _spy)
    r = client.post("/v1/memories",
                    json={"content": "The reservoir holds 500 liters.",
                          "topic": "moat/t",
                          "ground": False, "gate_mode": "off"},
                    headers={"Authorization": f"Bearer {api_key}"})
    assert r.status_code == 200, r.text
    assert seen.get("ground") is None, "client turned source-grounding off"
    assert seen.get("gate_mode") is None, "client chose the gate mode"


def test_operator_can_still_opt_into_client_control(tmp_path, monkeypatch):
    """A deployment that WANTS caller-chosen gating says so server-side."""
    keys = GatewayKeys(tmp_path / "keys.db")
    api_key = keys.create(tenant_id="tenant-permissive")
    app = create_app(data_dir=tmp_path / "gwdata", keys=keys,
                     allow_client_gate_override=True)
    client = TestClient(app)
    seen: dict = {}
    from verimem.client import Memory
    _orig = Memory.add

    def _spy(self, content=None, **kw):
        seen.update(kw)
        return _orig(self, content, **kw)

    monkeypatch.setattr(Memory, "add", _spy)
    client.post("/v1/memories",
                json={"content": "The reservoir holds 500 liters.",
                      "topic": "moat/t", "ground": False},
                headers={"Authorization": f"Bearer {api_key}"})
    assert seen.get("ground") is False


# ---- F11: never ship the key in cleartext over a network hop --------------

def test_thin_client_refuses_cleartext_http_to_a_remote_host():
    with pytest.raises(ValueError, match="https"):
        RemoteMemory("http://memory.example.com:8377", "vm_secret")


def test_thin_client_allows_http_on_loopback():
    RemoteMemory("http://127.0.0.1:8377", "vm_k")
    RemoteMemory("http://localhost:8377", "vm_k")


def test_thin_client_allows_https_anywhere():
    RemoteMemory("https://memory.example.com", "vm_k")


def test_operator_can_opt_out_of_the_https_requirement(monkeypatch):
    monkeypatch.setenv("VERIMEM_ALLOW_INSECURE_HTTP", "1")
    RemoteMemory("http://memory.example.com:8377", "vm_k")


def test_an_injected_transport_is_not_a_network_hop():
    """A test double / in-process ASGI app crosses no network, so the https
    requirement does not apply to it (it is what the whole gateway suite uses)."""
    RemoteMemory("http://gateway.local", "vm_k", _client=object())
