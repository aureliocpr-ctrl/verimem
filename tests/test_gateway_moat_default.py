"""The moat reaches the GATEWAY, not just the SDK (critic caller-verification,
2026-07-17). POST /v1/memories used ``ground=bool(body.get("ground", False))``,
hard-coding the moat OFF on the gateway even with a judge configured — so the
default flip touched only ``Memory.add``. Now ``ground`` absent → the store's
preset default (ON). A judge-less gateway still fail-opens.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from engram.client import Memory
from engram.gateway import GatewayKeys, create_app


class _StubJudge:
    def complete(self, system, messages, *, model=None, max_tokens=64):
        text = " ".join(m["content"] for m in messages).lower()
        score = 95 if text.count("postgres") >= 2 else 8

        class R:
            pass
        R.text = f"score: {score}"
        return R()


def _client(tmp_path, judge):
    keys = GatewayKeys(tmp_path / "k.db")
    personal = Memory(path=tmp_path / "p.db", llm=judge)
    app = create_app(data_dir=tmp_path, keys=keys, admin_key="adm",
                     local_tenant="op", local_memory=personal)
    return TestClient(app, base_url="http://localhost")


def test_gateway_quarantines_confab_with_judge(tmp_path):
    c = _client(tmp_path, _StubJudge())
    src = "We migrated the analytics store to Postgres last quarter."
    ok = c.post("/v1/memories", json={"content": "Analytics runs on Postgres.",
                                      "source": src})
    assert ok.json()["status"] != "quarantined"
    bad = c.post("/v1/memories", json={"content": "Analytics runs on MongoDB.",
                                       "source": src})
    assert bad.json()["status"] == "quarantined"   # moat ON by default now


def test_gateway_failopen_without_judge(tmp_path):
    c = _client(tmp_path, None)   # no llm → no judge
    bad = c.post("/v1/memories", json={"content": "Analytics runs on MongoDB.",
                                       "source": "We migrated to Postgres."})
    assert bad.json()["stored"] is True
    assert bad.json()["status"] != "quarantined"   # fail-open, unchanged


def test_gateway_explicit_ground_false_opts_out(tmp_path):
    c = _client(tmp_path, _StubJudge())
    r = c.post("/v1/memories", json={"content": "Analytics runs on MongoDB.",
                                     "source": "We migrated to Postgres.",
                                     "ground": False})
    assert r.json()["status"] != "quarantined"
