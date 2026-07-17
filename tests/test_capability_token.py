"""Cycle 368 (2026-05-23) — CAPABILITY TOKEN falsifiable contracts.

5 falsifiable contract clauses for HMAC capability token issuance +
verification + integration with engram_invoke.
"""
from __future__ import annotations

import time

import pytest


def test_issue_and_verify_valid_token() -> None:
    """Contract (a): issue + verify same secret + before expiry → ok=True."""
    from verimem.capability_token import issue_token, verify_token

    tok = issue_token("agent_A", "recall", ttl_sec=60.0, scope="read")
    r = verify_token(tok, expected_op="recall", peer_id_required="agent_A")
    assert r["ok"] is True
    assert r["peer_id"] == "agent_A"
    assert r["op"] == "recall"
    assert r["scope"] == "read"
    assert r["expires_at"] > time.time()
    assert r["blocked_by"] is None


def test_verify_token_op_mismatch_blocks() -> None:
    """Contract (b): op mismatch → blocked_by='op_mismatch'."""
    from verimem.capability_token import issue_token, verify_token
    tok = issue_token("agent_B", "recall", ttl_sec=60.0)
    r = verify_token(tok, expected_op="save")  # asking for different op
    assert r["ok"] is False
    assert r["blocked_by"] == "op_mismatch"
    assert "recall" in r["reason"] and "save" in r["reason"]


def test_verify_token_expired_blocks() -> None:
    """Contract (c): expired token → blocked_by='expired'."""
    from verimem.capability_token import issue_token, verify_token
    # Issue then verify with future 'now' to simulate expiry
    tok = issue_token("agent_C", "mesh_query", ttl_sec=1.0)
    # Verify 10s in future
    r = verify_token(tok, expected_op="mesh_query",
                      now=time.time() + 10.0)
    assert r["ok"] is False
    assert r["blocked_by"] == "expired"


def test_verify_token_tampered_hmac_blocks() -> None:
    """Contract (d): tampered HMAC → blocked_by='hmac_invalid'."""
    from verimem.capability_token import issue_token, verify_token
    tok = issue_token("agent_D", "recall", ttl_sec=60.0)
    # Tamper: flip last byte of hmac hex
    b64, hex_part = tok.rsplit(":", 1)
    tampered_hex = hex_part[:-2] + ("ff" if hex_part[-2:] != "ff" else "00")
    tampered = f"{b64}:{tampered_hex}"
    r = verify_token(tampered, expected_op="recall")
    assert r["ok"] is False
    assert r["blocked_by"] == "hmac_invalid"


def test_verify_token_peer_mismatch_blocks() -> None:
    """Contract (e): wrong peer (when required) → blocked_by='peer_mismatch'."""
    from verimem.capability_token import issue_token, verify_token
    tok = issue_token("agent_E", "recall", ttl_sec=60.0)
    r = verify_token(tok, expected_op="recall",
                      peer_id_required="agent_X_imposter")
    assert r["ok"] is False
    assert r["blocked_by"] == "peer_mismatch"
    assert "agent_E" in r["reason"]
    assert "agent_X_imposter" in r["reason"]


def test_malformed_token_blocked() -> None:
    """Defensive: malformed input → graceful refusal."""
    from verimem.capability_token import verify_token
    for bad in ["", "no_separator", "bad:not_hex_at_all", ":justcolon"]:
        r = verify_token(bad, expected_op="recall")
        assert r["ok"] is False
        assert r["blocked_by"] in ("malformed_token", "hmac_invalid")


def test_syscall_bridge_token_integration(tmp_path, monkeypatch) -> None:
    """Wire test: engram_invoke + capability_token full path.

    (a) call with valid token → ok
    (b) call with require_token=True + no token → blocked_by='missing_capability_token'
    (c) call with require_token=True + tampered token → blocked_by='hmac_invalid'
    """
    from verimem import op_supervisor, syscall_bridge
    from verimem.capability_token import issue_token
    audit = tmp_path / "audit.jsonl"
    monkeypatch.setattr(syscall_bridge, "ENGRAM_AUDIT_LOG", audit)
    monkeypatch.setattr(op_supervisor, "_DEFAULT_SUPERVISOR",
                        op_supervisor.OpSupervisor(max_failures=100))
    syscall_bridge._RATE_BUCKETS.clear()

    # (b) missing token + require_token=True
    r_no_tok = syscall_bridge.engram_invoke(
        "mesh_fetch", {"channel": "test/x"}, actor="agent_test",
        require_token=True,
    )
    assert r_no_tok["ok"] is False
    assert r_no_tok["blocked_by"] == "missing_capability_token"

    # (a) valid token + matching op + peer
    tok = issue_token("agent_test", "mesh_fetch", ttl_sec=60.0)
    r_ok = syscall_bridge.engram_invoke(
        "mesh_fetch", {"channel": "test/x"}, actor="agent_test",
        capability_token=tok, require_token=True,
    )
    assert r_ok["ok"] is True, f"expected ok=True, got {r_ok}"

    # (c) tampered token
    b64, hex_part = tok.rsplit(":", 1)
    tampered = f"{b64}:" + ("0" * len(hex_part))
    r_bad = syscall_bridge.engram_invoke(
        "mesh_fetch", {"channel": "test/x"}, actor="agent_test",
        capability_token=tampered, require_token=True,
    )
    assert r_bad["ok"] is False
    assert r_bad["blocked_by"] == "hmac_invalid"
