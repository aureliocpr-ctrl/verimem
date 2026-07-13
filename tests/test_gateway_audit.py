"""Access-audit log — enterprise compliance trail (2026-07-13).

Every HTTP request leaves ONE structured JSONL record (who/what/when/status) and
NEVER leaks the auth token, query string, or body. These tests assert the record
is emitted for success + error + the body-limit 413, is tenant-attributed, is
secret-free, and can be turned off.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

from fastapi.testclient import TestClient

from engram.gateway import GatewayKeys, create_app

_FACT = {"topic": "t", "verified_by": ["source-doc:d:1"]}


def _auth(k: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {k}"}


def _app(tmp_path, *, audit_log=True, **kw):
    keys = GatewayKeys(tmp_path / "k.db")
    k = keys.create(tenant_id="alpha", name="a", plan="free")
    app = create_app(data_dir=tmp_path, keys=keys, audit_log=audit_log, **kw)
    return TestClient(app), k


def _records(tmp_path):
    lines = []
    for f in sorted(glob.glob(str(Path(tmp_path) / "audit" / "*.jsonl"))):
        with open(f, encoding="utf-8") as fh:
            lines += [json.loads(ln) for ln in fh if ln.strip()]
    return lines


def test_request_produces_an_audit_record(tmp_path):
    client, k = _app(tmp_path)
    client.get("/v1/stats", headers=_auth(k))
    recs = _records(tmp_path)
    hit = [r for r in recs if r["path"] == "/v1/stats"]
    assert hit, f"no audit record for /v1/stats in {recs}"
    r = hit[-1]
    assert r["method"] == "GET" and r["status"] == 200
    assert r["tenant"] == "alpha"                       # attributed to the caller
    assert isinstance(r["latency_ms"], (int, float)) and r["request_id"]
    assert r["ts"].endswith("Z")


def test_audit_never_logs_the_secret_or_query(tmp_path):
    client, k = _app(tmp_path)
    client.get("/v1/search", headers=_auth(k),
               params={"q": "super secret query terms"})
    blob = "\n".join(json.dumps(r) for r in _records(tmp_path))
    assert k not in blob                                # the bearer token is never written
    assert "super secret query terms" not in blob      # the query string is never written


def test_error_responses_are_audited(tmp_path):
    client, _ = _app(tmp_path)
    client.get("/v1/quota")                             # no key -> 401
    recs = _records(tmp_path)
    assert any(r["path"] == "/v1/quota" and r["status"] == 401 and r["tenant"] is None
               for r in recs)


def test_body_limit_413_is_audited(tmp_path):
    client, k = _app(tmp_path, max_body_bytes=64)
    client.post("/v1/memories", headers=_auth(k),
                json={"content": "x" * 500, **_FACT})
    recs = _records(tmp_path)
    assert any(r["path"] == "/v1/memories" and r["status"] == 413 for r in recs)


def test_unauthenticated_health_is_audited_without_tenant(tmp_path):
    client, _ = _app(tmp_path)
    client.get("/v1/health")
    recs = _records(tmp_path)
    assert any(r["path"] == "/v1/health" and r["status"] == 200 and r["tenant"] is None
               for r in recs)


def test_audit_can_be_disabled(tmp_path):
    client, k = _app(tmp_path, audit_log=False)
    client.get("/v1/stats", headers=_auth(k))
    assert _records(tmp_path) == []                     # no directory / no records
