"""CYCLE #26 — test audit_tail module (pure-function).

Bug pre-fix: engram.audit_tail non esisteva. import in
mcp_server.py:5409 falliva con ImportError, catturato silently.
"""
from __future__ import annotations

import json

from engram.audit_tail import audit_tail


def test_audit_tail_missing_file_returns_empty(tmp_path):
    nonexistent = tmp_path / "missing.log"
    out = audit_tail(n=10, path=nonexistent)
    assert out["entries"] == []
    assert out["exists"] is False
    assert out["n_returned"] == 0


def test_audit_tail_reads_jsonl(tmp_path):
    log = tmp_path / "audit.log"
    records = [
        {"ts": 1.0, "tool": "a", "outcome": "ok"},
        {"ts": 2.0, "tool": "b", "outcome": "ok"},
        {"ts": 3.0, "tool": "c", "outcome": "exception"},
    ]
    log.write_text("\n".join(json.dumps(r) for r in records) + "\n",
                    encoding="utf-8")
    out = audit_tail(n=10, path=log)
    assert out["exists"] is True
    assert out["n_returned"] == 3
    assert [e["tool"] for e in out["entries"]] == ["a", "b", "c"]


def test_audit_tail_respects_n(tmp_path):
    log = tmp_path / "a.log"
    lines = "\n".join(json.dumps({"ts": i, "tool": f"t{i}"}) for i in range(100))
    log.write_text(lines + "\n", encoding="utf-8")
    out = audit_tail(n=5, path=log)
    assert out["n_returned"] == 5
    # Tail = ultimi 5 record (95..99)
    tools = [e["tool"] for e in out["entries"]]
    assert tools == ["t95", "t96", "t97", "t98", "t99"]


def test_audit_tail_handles_malformed_lines(tmp_path):
    log = tmp_path / "bad.log"
    log.write_text(
        json.dumps({"tool": "good1"}) + "\n"
        + "this is not json\n"
        + json.dumps({"tool": "good2"}) + "\n",
        encoding="utf-8",
    )
    out = audit_tail(n=10, path=log)
    assert out["n_returned"] == 3
    # Riga malformata → _raw fallback
    raws = [e for e in out["entries"] if "_raw" in e]
    assert len(raws) == 1


def test_audit_tail_n_clamped(tmp_path):
    log = tmp_path / "c.log"
    log.write_text(json.dumps({"x": 1}) + "\n", encoding="utf-8")
    # n=0 → clamp a 1
    out = audit_tail(n=0, path=log)
    assert out["n_requested"] == 1
    # n troppo grande → clamp a 10000
    out = audit_tail(n=10_000_000, path=log)
    assert out["n_requested"] == 10_000


def test_audit_tail_unblocks_introspect_state():
    """Regression: hippo_introspect_state importava questo modulo che
    NON esisteva. ImportError silently caught → recent_audit=[] sempre.
    Ora il modulo esiste e l'introspect_state restituisce dati reali."""
    from engram import audit_tail as mod
    assert callable(mod.audit_tail)
    # Smoke test: chiamabile senza args sull'audit log corrente
    result = mod.audit_tail()
    assert "entries" in result
    assert "path" in result
    assert "exists" in result
