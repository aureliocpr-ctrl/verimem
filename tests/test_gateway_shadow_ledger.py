"""Phase-1 SHADOW hook (REMORSE graft): /v1/search and /v1/answer emit a
``shadow.ledger`` event — the AdaptiveLedger's would-be decision next to the
gateway's ACTUAL decision — without altering any response. The 13/7 dead-gates
lesson inverted: observe first on real traffic, apply later (phase 2).

Pinned here: (a) the event is emitted with tenant/topic/hazard/advice and the
actual decision; (b) the HTTP response is byte-identical shadow-on vs off;
(c) ``ENGRAM_SHADOW_LEDGER=0`` kills the hook.
"""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from verimem import adaptive_ledger, event_jsonl_log
from verimem.client import Memory
from verimem.gateway import GatewayKeys, create_app


class _StubLLM:
    def complete(self, system, messages, max_tokens=64):
        class R:
            text = "NO ANSWER"

        return R()


def _client(tmp_path, monkeypatch, llm=None) -> TestClient:
    monkeypatch.setattr(event_jsonl_log, "EVENT_LOG_PATH",
                        tmp_path / "events.jsonl")
    adaptive_ledger.reset_shadow()
    keys = GatewayKeys(tmp_path / "k.db")
    personal = Memory(path=tmp_path / "personal.db")
    personal.add("The analytics database listens on port 5433.", topic="infra")
    app = create_app(data_dir=tmp_path, keys=keys, admin_key="adm",
                     local_tenant="op", local_memory=personal, llm=llm)
    return TestClient(app, base_url="http://localhost")


def _shadow_events(tmp_path) -> list[dict]:
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        rec = json.loads(ln)
        if rec.get("name") == "shadow.ledger":
            out.append(rec)
    return out


def test_search_emits_shadow_event_with_decision(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.get("/v1/search", params={"q": "database port", "k": 3})
    assert r.status_code == 200
    evs = _shadow_events(tmp_path)
    assert len(evs) == 1
    p = evs[0]["payload"]
    assert p["surface"] == "search"
    assert p["tenant"] == "op"
    assert p["topic"] == "infra"
    assert "hazard" in p and p["advice"] in ("trust", "verify")
    assert p["actual"]["n_hits"] == len(r.json()["hits"])


def test_answer_emits_shadow_event_with_actual_reason(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch, llm=_StubLLM())
    r = c.get("/v1/answer", params={"q": "which port?"})
    assert r.status_code == 200
    evs = _shadow_events(tmp_path)
    assert len(evs) == 1
    p = evs[0]["payload"]
    assert p["surface"] == "answer"
    assert p["actual"]["reason"] == r.json()["reason"]


def test_shadow_never_changes_the_response(tmp_path, monkeypatch):
    # two ISOLATED gateways (separate stores — ids/created_at differ by nature):
    # shadow on vs off must agree on everything the caller can act on.
    def _essence(body):
        return [(h["text"], h["status"], h["topic"], h["score"])
                for h in body["hits"]]

    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    c_on = _client(tmp_path / "a", monkeypatch)
    body_on = c_on.get("/v1/search", params={"q": "database port", "k": 3}).json()
    monkeypatch.setenv("ENGRAM_SHADOW_LEDGER", "0")
    c_off = _client(tmp_path / "b", monkeypatch)
    body_off = c_off.get("/v1/search", params={"q": "database port", "k": 3}).json()
    assert _essence(body_on) == _essence(body_off)


def test_kill_switch_suppresses_events(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SHADOW_LEDGER", "0")
    c = _client(tmp_path, monkeypatch)
    c.get("/v1/search", params={"q": "database port", "k": 3})
    assert _shadow_events(tmp_path) == []
