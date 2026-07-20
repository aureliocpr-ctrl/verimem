"""The moat reaches the GATEWAY, not just the SDK (critic caller-verification,
2026-07-17). POST /v1/memories used ``ground=bool(body.get("ground", False))``,
hard-coding the moat OFF on the gateway even with a judge configured — so the
default flip touched only ``Memory.add``. Now ``ground`` absent → the store's
preset default (ON). A judge-less gateway still fail-opens.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from verimem.client import Memory
from verimem.gateway import GatewayKeys, create_app


class _StubJudge:
    def complete(self, system, messages, *, model=None, max_tokens=64):
        text = " ".join(m["content"] for m in messages).lower()
        score = 95 if text.count("postgres") >= 2 else 8

        class R:
            pass
        R.text = f"score: {score}"
        return R()


def _client(tmp_path, judge, **app_kw):
    keys = GatewayKeys(tmp_path / "k.db")
    personal = Memory(path=tmp_path / "p.db", llm=judge)
    app = create_app(data_dir=tmp_path, keys=keys, admin_key="adm",
                     local_tenant="op", local_memory=personal, **app_kw)
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


def test_gateway_failopen_with_NO_judge_at_all(tmp_path, monkeypatch):
    # NO judge AT ALL — no llm AND no local CE. Force the CE absent (0.6.0 makes
    # it the default judge otherwise). Then the gateway admits as before.
    monkeypatch.setattr("verimem.local_grounding.local_ce_available", lambda: False)
    c = _client(tmp_path, None)   # no llm
    bad = c.post("/v1/memories", json={"content": "Analytics runs on MongoDB.",
                                       "source": "We migrated to Postgres."})
    assert bad.json()["stored"] is True
    assert bad.json()["status"] != "quarantined"   # fail-open: no llm AND no CE


def test_gateway_moat_ON_with_local_CE_no_llm(tmp_path):
    # 0.6.0 behavior change: the gateway's moat is ON via the local CE even with
    # no llm — a tenant confab is quarantined out-of-the-box. Skips if CE absent.
    import pytest

    from verimem.local_grounding import local_ce_available
    if not local_ce_available():
        pytest.skip("local CE model not installed in this environment")
    c = _client(tmp_path, None)
    bad = c.post("/v1/memories", json={
        "content": "Analytics runs on MongoDB.",
        "source": "We migrated the analytics store to Postgres last quarter."})
    assert bad.json()["status"] == "quarantined"


def test_gateway_ignores_client_ground_false_by_default(tmp_path):
    # Audit F7 (2026-07-20): the SERVER owns the gate. The writer asking to
    # skip the moat is the exact party the moat exists to check, so the
    # request-body `ground` knob is ignored unless the operator opted in.
    c = _client(tmp_path, _StubJudge())
    r = c.post("/v1/memories", json={"content": "Analytics runs on MongoDB.",
                                     "source": "We migrated to Postgres.",
                                     "ground": False})
    assert r.json()["status"] == "quarantined"


def test_gateway_ground_false_honored_with_operator_optin(tmp_path):
    c = _client(tmp_path, _StubJudge(), allow_client_gate_override=True)
    r = c.post("/v1/memories", json={"content": "Analytics runs on MongoDB.",
                                     "source": "We migrated to Postgres.",
                                     "ground": False})
    assert r.json()["status"] != "quarantined"
