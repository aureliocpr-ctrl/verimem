"""GET /v1/answer — the gateway surface for grounding-verified answering.

Critic caller_verification (job ab1cf798738847a1, 2026-07-16) found the gap:
``Memory.answer()`` (trust-conditioned, measured 0.17→0.92 on the case-B bench)
was SDK-only — no REST endpoint, so gateway tenants (console, MCP-over-HTTP,
curl users) could not reach the anti-hallucination read-path at all. This wires
it like /v1/search: tenant-scoped store, flow context, meter, and an explicit
400 (not a crash) when the gateway was started without a server-side llm.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from verimem.client import _ANSWER_TRUST_SYSTEM, Memory
from verimem.gateway import GatewayKeys, create_app


class _StubLLM:
    def __init__(self, reply: str):
        self.reply = reply
        self.systems: list[str] = []

    def complete(self, system, messages, max_tokens=64):
        self.systems.append(system)

        class R:
            text = self.reply

        return R()


def _client(tmp_path, llm=None) -> TestClient:
    keys = GatewayKeys(tmp_path / "k.db")
    personal = Memory(path=tmp_path / "personal.db")
    personal.add("The main office is in Turin.")
    app = create_app(data_dir=tmp_path, keys=keys, admin_key="adm",
                     local_tenant="op", local_memory=personal, llm=llm)
    # personal mode authenticates by loopback Host — base_url supplies it
    return TestClient(app, base_url="http://localhost")


def test_answer_without_server_llm_is_explicit_400(tmp_path):
    c = _client(tmp_path, llm=None)
    r = c.get("/v1/answer", params={"q": "Where is the office?"})
    assert r.status_code == 400
    assert "llm" in r.text.lower()


def test_answer_model_abstention_flows_through(tmp_path):
    c = _client(tmp_path, llm=_StubLLM("NO ANSWER"))
    r = c.get("/v1/answer", params={"q": "Where is the office?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "NO ANSWER"
    assert body["reason"] == "model_abstained"


def test_answer_uses_trust_conditioning_by_default(tmp_path):
    llm = _StubLLM("NO ANSWER")
    c = _client(tmp_path, llm=llm)
    c.get("/v1/answer", params={"q": "Where is the office?"})
    assert llm.systems == [_ANSWER_TRUST_SYSTEM]


def test_answer_no_facts_reason(tmp_path):
    # empty store → the honest no_facts abstention, still HTTP 200
    keys = GatewayKeys(tmp_path / "k.db")
    personal = Memory(path=tmp_path / "empty.db")
    app = create_app(data_dir=tmp_path, keys=keys, admin_key="adm",
                     local_tenant="op", local_memory=personal,
                     llm=_StubLLM("whatever"))
    c = TestClient(app, base_url="http://localhost")
    r = c.get("/v1/answer", params={"q": "anything at all?"})
    assert r.status_code == 200
    assert r.json()["reason"] == "no_facts"
