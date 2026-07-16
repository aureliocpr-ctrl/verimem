"""Trust console v2 — il contratto della superficie (2026-07-16).

Mandato Aurelio: "console in tutta la sua interezza perfetta... grafo e
cofano del motore che si aggiornano live davvero". Questa suite fissa i
pezzi SERVER che la v2 ha introdotto, perché non regrediscano:

  1. ``GET /`` → 307 su ``/ui`` (un umano che apre il gateway non deve
     vedere ``{"detail":"Not Found"}`` — visto live 2026-07-16).
  2. i bundle grafo vendored (sigma/graphology, MIT) sono serviti dalla
     allowlist con content-type JS — e la allowlist resta chiusa.
  3. la CSP delle pagine HTML include ``worker-src 'self' blob:`` — il
     layout ForceAtlas2 gira in un Web Worker creato da codice same-origin;
     senza questa direttiva il grafo non ha layout.
  4. ``GET /v1/answer`` emette il SUO evento ``flow.recall kind=answer``
     (grounded/abstained/reason): l'Engine Room mostra il verdetto per ciò
     che è, non un generico recall.
"""
from __future__ import annotations

import json

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from engram import event_jsonl_log  # noqa: E402
from engram.gateway import GatewayKeys, create_app  # noqa: E402


class _FakeResp:
    text = "the target is 4.2M euro"


class _FakeLLM:
    def complete(self, system, messages, max_tokens=64):  # noqa: ARG002
        return _FakeResp()


@pytest.fixture()
def gw(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    client = TestClient(create_app(data_dir=tmp_path, keys=keys,
                                   llm=_FakeLLM()))
    api_key = keys.create(tenant_id="acme")
    return client, {"Authorization": f"Bearer {api_key}"}, tmp_path


def _flow(tmp_path, name):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines()
            if json.loads(ln).get("name") == name]


# ---- 1. root ---------------------------------------------------------------

def test_root_redirects_a_human_to_the_console(gw):
    client, _, _ = gw
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "/ui"


# ---- 2. vendored graph stack ------------------------------------------------

@pytest.mark.parametrize("asset", [
    "vendor-graphology.js", "vendor-graphology-library.js", "vendor-sigma.js"])
def test_vendor_bundle_is_served_as_js(gw, asset):
    client, _, _ = gw
    r = client.get(f"/ui/{asset}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/javascript")
    assert len(r.text) > 10_000          # a real bundle, not a stub


def test_asset_allowlist_stays_closed(gw):
    client, _, _ = gw
    for probe in ("vendor-evil.js", "..%2Fclient.py", "__init__.py"):
        assert client.get(f"/ui/{probe}").status_code == 404


# ---- 3. CSP: the FA2 worker is allowed, nothing else changed ----------------

def test_html_csp_allows_sameorigin_blob_workers(gw):
    client, _, _ = gw
    csp = client.get("/ui").headers["content-security-policy"]
    assert "worker-src 'self' blob:" in csp
    assert "script-src 'self'" in csp    # still no CDN, no inline


# ---- 4. the flow event names the defense that ACTED --------------------------

def test_quarantined_write_carries_its_layers(gw):
    """The Engine Room lights the REAL stage: a quarantined write's flow
    event carries `layers` — same attribution as the ledger's by_layer."""
    client, hdr, tmp_path = gw
    r = client.post("/v1/memories", headers=hdr,
                    json={"content": "the deployment works and is verified "
                                     "in production",
                          "topic": "deploy"})
    assert r.json()["status"] == "quarantined"
    evts = [e for e in _flow(tmp_path, "flow.write")
            if e["payload"].get("status") == "quarantined"]
    assert len(evts) == 1
    layers = evts[0]["payload"]["layers"]
    assert layers and all(isinstance(x, str) and x for x in layers)


# ---- 5. answer emits its own flow event --------------------------------------

def test_answer_emits_flow_recall_kind_answer(gw):
    client, hdr, tmp_path = gw
    client.post("/v1/memories", headers=hdr,
                json={"content": "the Q3 revenue target is 4.2M euro",
                      "topic": "finance"})
    r = client.get("/v1/answer", headers=hdr,
                   params={"q": "what is the Q3 target?", "k": 3})
    assert r.status_code == 200
    evts = [e for e in _flow(tmp_path, "flow.recall")
            if e["payload"].get("kind") == "answer"]
    assert len(evts) == 1
    p = evts[0]["payload"]
    assert p["tenant"] == "acme"
    assert isinstance(p["grounded"], bool)
    assert isinstance(p["abstained"], bool)
    assert p["reason"]                    # mai vuoto: grounded/failopen/...
