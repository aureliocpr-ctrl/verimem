"""Cycle 364 (2026-05-23) — ENGRAM SYSCALL BRIDGE falsifiable contracts.

A3 honest scope: this is engineering integration (clp os boundary +
engram ops), NOT a singolarità claim. Tests validate the 4 falsifiable
contract clauses:
  (a) Hallucinated op name → blocked_by='not_in_manifest'
  (b) Real op success → audit JSONL row written + ok=True
  (c) Rate limit triggers blocked_by='rate_limit_exceeded'
  (d) Handler exception → blocked_by='exception'
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest


def _vec_bus_available() -> bool:
    try:
        from clp.agentos import vec_bus  # noqa: F401
        return True
    except ImportError:
        return False


def test_engram_invoke_blocks_hallucinated_op(tmp_path: Path,
                                                monkeypatch) -> None:
    """Falsifiable contract (a): op not in manifest → blocked."""
    from engram import syscall_bridge
    # Redirect audit log to tmp
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setattr(syscall_bridge, "ENGRAM_AUDIT_LOG", audit_path)

    r = syscall_bridge.engram_invoke("recall_magic_inventato", {}, actor="test")
    assert r["ok"] is False
    assert r["blocked_by"] == "not_in_manifest"
    assert "available_ops" in r
    assert "recall" in r["available_ops"]
    # Audit row written
    assert audit_path.exists()
    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    record = json.loads(lines[-1])
    assert record["op"] == "recall_magic_inventato"
    assert record["blocked_by"] == "not_in_manifest"
    assert record["actor"] == "test"


def test_engram_invoke_rate_limit_triggers(tmp_path: Path,
                                            monkeypatch) -> None:
    """Falsifiable contract (c): >limit calls/sec → blocked."""
    if not _vec_bus_available():
        pytest.skip("vec_bus not available")
    from engram import syscall_bridge
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setattr(syscall_bridge, "ENGRAM_AUDIT_LOG", audit_path)
    # Reset rate buckets
    syscall_bridge._RATE_BUCKETS.clear()

    # Use mesh_fetch (cheap op, won't hit other failures)
    rate_limit = 3.0  # allow only 3/sec
    ok_count, blocked_count = 0, 0
    for _ in range(10):
        r = syscall_bridge.engram_invoke(
            "mesh_fetch",
            {"channel": f"test/rate/{os.getpid()}", "since_ts": 0.0},
            actor="rate_test", rate_limit=rate_limit,
        )
        if r["ok"]:
            ok_count += 1
        elif r["blocked_by"] == "rate_limit_exceeded":
            blocked_count += 1

    assert ok_count >= 1, "no successful calls — rate limit may be off"
    assert blocked_count >= 1, (
        f"rate limit never triggered: ok={ok_count}, blocked={blocked_count}"
    )
    # All blocked calls audited
    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    blocked_records = [
        json.loads(line) for line in lines
        if line and json.loads(line).get("blocked_by") == "rate_limit_exceeded"
    ]
    assert len(blocked_records) == blocked_count


def test_engram_invoke_handler_exception_blocked(tmp_path: Path,
                                                   monkeypatch) -> None:
    """Falsifiable contract (d): handler raises → blocked_by='exception'."""
    from engram import syscall_bridge
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setattr(syscall_bridge, "ENGRAM_AUDIT_LOG", audit_path)
    syscall_bridge._RATE_BUCKETS.clear()

    # Inject a broken op into the manifest
    def _broken_handler(args):
        raise RuntimeError("synthetic failure for contract test")
    monkeypatch.setitem(syscall_bridge.ENGRAM_OPS_MANIFEST,
                        "broken_op", _broken_handler)

    r = syscall_bridge.engram_invoke("broken_op", {}, actor="test")
    assert r["ok"] is False
    assert r["blocked_by"] == "exception"
    assert r["exception"] == "RuntimeError"
    # Audit captured the exception
    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    rec = json.loads(lines[-1])
    assert rec["blocked_by"] == "exception"
    assert "synthetic" in rec.get("message", "")


def test_engram_invoke_real_recall_success(tmp_path: Path,
                                             monkeypatch) -> None:
    """Falsifiable contract (b): real recall op → ok + audited."""
    if not _vec_bus_available():
        pytest.skip("vec_bus not available")
    from engram import syscall_bridge
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setattr(syscall_bridge, "ENGRAM_AUDIT_LOG", audit_path)
    syscall_bridge._RATE_BUCKETS.clear()

    # Build a tiny corpus
    import sqlite3

    from clp.agentos.vec_bus import embed_text
    db = tmp_path / "test_corpus.db"
    conn = sqlite3.connect(str(db))
    try:
        conn.execute("""
            CREATE TABLE facts (id TEXT PRIMARY KEY, topic TEXT,
                proposition TEXT, embedding BLOB, lineage_to TEXT,
                superseded_by TEXT, status TEXT)
        """)
        for i, prop in enumerate(["apple is red", "rust is fast",
                                    "python is dynamic"]):
            conn.execute(
                "INSERT INTO facts (id, proposition, embedding) "
                "VALUES (?, ?, ?)",
                (f"f{i}", prop, embed_text(prop)),
            )
        conn.commit()
    finally:
        conn.close()

    r = syscall_bridge.engram_invoke(
        "recall",
        {"query": "what programming language", "k": 2, "db_path": str(db)},
        actor="test",
    )
    assert r["ok"] is True
    assert r["blocked_by"] is None
    assert "hits" in r["result"]
    hits = r["result"]["hits"]
    assert len(hits) == 2
    # The Python fact should outrank apple for "programming language" query
    top_id = hits[0][0]
    assert top_id == "f2", f"expected f2 (python), got {top_id} hits={hits}"

    # Audit row written
    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    rec = json.loads(lines[-1])
    assert rec["op"] == "recall"
    assert rec["ok"] is True
    assert "hits" in rec.get("result_keys", []) or rec.get("ok")


def test_engram_available_ops_manifest_introspection() -> None:
    """Manifest is introspectable for cross-LLM planning (anti-hallucination)."""
    from engram import syscall_bridge
    ops = syscall_bridge.engram_available_ops()
    assert isinstance(ops, list)
    assert "recall" in ops
    assert "mesh_query" in ops
    assert "resonant_merge" in ops
    # No hallucinated ops in the public list
    assert "recall_magic_inventato" not in ops
