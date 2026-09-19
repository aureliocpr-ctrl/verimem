"""Cycle 365 (2026-05-23) — OPERATION SUPERVISOR falsifiable contracts.

Tests circuit-breaker semantics + per-op isolation + half-open probe.
Contracts:
  (a) 3 consecutive failures → circuit opens, blocked_by='circuit_breaker_open'
  (b) Per-op isolation: failures on op_X don't open op_Y
  (c) reset_window elapsed → circuit half_open + 1 probe allowed
  (d) Success in half_open → circuit closes
  (e) Failure in half_open → circuit re-opens immediately
"""
from __future__ import annotations

import pytest


def _supervisor_with_fast_reset():
    from verimem.op_supervisor import OpSupervisor
    return OpSupervisor(
        max_failures=3,
        failure_window_sec=30.0,
        reset_window_sec=0.05,  # 50ms for fast tests
        half_open_probe_count=1,
    )


def test_circuit_opens_after_threshold() -> None:
    """Contract (a): N=3 failures consecutive → circuit_open."""
    sup = _supervisor_with_fast_reset()
    op = "recall"
    # 2 failures: still closed
    sup.record_failure(op, "err1")
    assert sup.check(op)["state"]["circuit"] == "closed"
    sup.record_failure(op, "err2")
    assert sup.check(op)["state"]["circuit"] == "closed"
    # 3rd failure: opens
    sup.record_failure(op, "err3")
    ck = sup.check(op)
    assert ck["allowed"] is False
    assert ck["blocked_by"] == "circuit_breaker_open"
    assert ck["state"]["circuit"] == "open"
    assert ck["state"]["n_total_failures"] == 3


def test_per_op_isolation() -> None:
    """Contract (b): failures on op_X don't affect op_Y."""
    sup = _supervisor_with_fast_reset()
    # Open recall circuit
    for _ in range(3):
        sup.record_failure("recall", "boom")
    assert sup.check("recall")["allowed"] is False
    # mesh_query should still be closed (independent)
    ck = sup.check("mesh_query")
    assert ck["allowed"] is True
    assert ck["state"]["circuit"] == "closed"


def test_reset_window_transitions_to_half_open() -> None:
    """Contract (c): after reset_window → half_open + 1 probe."""
    import time
    sup = _supervisor_with_fast_reset()
    op = "resonant_merge"
    for _ in range(3):
        sup.record_failure(op, "boom")
    assert sup.check(op)["state"]["circuit"] == "open"
    # Wait for reset_window (50ms)
    time.sleep(0.07)
    ck = sup.check(op)
    assert ck["allowed"] is True, (
        f"after reset_window expected half_open allowed; got {ck}"
    )
    assert ck["state"]["circuit"] == "half_open"
    # Next call without success/failure should be blocked (probe exhausted)
    ck2 = sup.check(op)
    assert ck2["allowed"] is False
    assert ck2["blocked_by"] == "circuit_breaker_half_open_exhausted"


def test_half_open_success_closes_circuit() -> None:
    """Contract (d): success during half_open → circuit closed."""
    import time
    sup = _supervisor_with_fast_reset()
    op = "topk_embeddings"
    for _ in range(3):
        sup.record_failure(op, "boom")
    time.sleep(0.07)
    # First check transitions to half_open + consumes probe
    sup.check(op)
    # Record success: should close circuit
    sup.record_success(op)
    ck = sup.check(op)
    assert ck["state"]["circuit"] == "closed"
    assert ck["allowed"] is True
    # Counter reset
    assert ck["state"]["n_consecutive_failures"] == 0


def test_half_open_failure_reopens() -> None:
    """Contract (e): failure during half_open → circuit re-opens."""
    import time
    sup = _supervisor_with_fast_reset()
    op = "mesh_fetch"
    for _ in range(3):
        sup.record_failure(op, "boom")
    time.sleep(0.07)
    sup.check(op)  # transitions to half_open, consumes probe
    # Failure: re-opens
    sup.record_failure(op, "still broken")
    ck = sup.check(op)
    assert ck["state"]["circuit"] == "open"
    assert ck["allowed"] is False
    assert ck["state"]["half_open_probes_remaining"] == 0


def test_escalate_open_circuits_cycle377(monkeypatch) -> None:
    """Cycle 377: circuits open longer than threshold trigger vec_bus alert.

    Falsifiable:
      (a) Circuit closed/half_open → not escalated
      (b) Circuit open < threshold → not escalated
      (c) Circuit open >= threshold → escalated, alert msg published
      (d) Already-escalated circuits stay escalable (idempotent)
    """
    from verimem.op_supervisor import OpSupervisor

    sup = OpSupervisor(max_failures=2, reset_window_sec=300.0)

    # Mock vec_bus.vec_send to capture calls without filesystem side effects
    sent: list[dict] = []
    class _MockVB:
        @staticmethod
        def vec_send(channel, text_or_vec, sender=None, origin_hint=None,
                      intent_tag=None):
            msg = {
                "ok": True,
                "msg_id": f"mock-{len(sent):04d}",
                "channel": channel,
                "text": text_or_vec if isinstance(text_or_vec, str) else "",
                "sender": sender,
                "intent_tag": intent_tag,
            }
            sent.append(msg)
            return msg

    # Patch vec_bus import path
    import sys
    import types
    fake_module = types.ModuleType("clp.agentos.vec_bus")
    fake_module.vec_send = _MockVB.vec_send
    fake_pkg = types.ModuleType("clp.agentos")
    fake_pkg.vec_bus = fake_module
    fake_root = types.ModuleType("clp")
    fake_root.agentos = fake_pkg
    monkeypatch.setitem(sys.modules, "clp", fake_root)
    monkeypatch.setitem(sys.modules, "clp.agentos", fake_pkg)
    monkeypatch.setitem(sys.modules, "clp.agentos.vec_bus", fake_module)

    # (a) No open circuits → no escalation
    out = sup.escalate_open_circuits(min_open_sec=60.0)
    assert out == []
    assert sent == []

    # Open circuit on op_X
    for _ in range(2):
        sup.record_failure("op_X", "boom")
    # Just opened: open_dur ~0, below threshold → not escalated
    out = sup.escalate_open_circuits(min_open_sec=60.0)
    assert out == []

    # Backdate last_open_at to simulate 70s ago
    import time as _t
    sup._state["op_X"]["last_open_at"] = _t.time() - 70.0
    out = sup.escalate_open_circuits(min_open_sec=60.0)
    assert len(out) == 1
    assert out[0]["op"] == "op_X"
    assert out[0]["open_duration_sec"] >= 60.0
    assert len(sent) == 1
    assert sent[0]["intent_tag"] == "engram-alert-circuit-open"
    assert "op_X" in sent[0]["text"]

    # (d) Idempotent — second call still escalates (no de-dup; ambient
    # daemon may decide its own dedup logic externally)
    out2 = sup.escalate_open_circuits(min_open_sec=60.0)
    assert len(out2) == 1
    assert len(sent) == 2


def test_syscall_bridge_supervisor_integration_blocks_after_3_exceptions(
    tmp_path,
    monkeypatch,
) -> None:
    """Wire test: 3 handler exceptions on op X → engram_invoke returns
    blocked_by='circuit_breaker_open' on the 4th call.

    Falsifiable integration contract for cycle 364 + cycle 365 wired.
    """
    from verimem import op_supervisor, syscall_bridge
    audit = tmp_path / "audit.jsonl"
    monkeypatch.setattr(syscall_bridge, "ENGRAM_AUDIT_LOG", audit)
    monkeypatch.setattr(op_supervisor, "_DEFAULT_SUPERVISOR",
                        op_supervisor.OpSupervisor(max_failures=3))
    syscall_bridge._RATE_BUCKETS.clear()

    def _crash(args):
        raise RuntimeError("synthetic")
    monkeypatch.setitem(syscall_bridge.ENGRAM_OPS_MANIFEST,
                        "crash_op", _crash)

    # 3 calls all fail with exception
    for i in range(3):
        r = syscall_bridge.engram_invoke(
            "crash_op", {}, actor=f"test{i}", rate_limit=100.0,
        )
        assert r["ok"] is False
        assert r["blocked_by"] == "exception", (
            f"call {i}: expected exception, got {r['blocked_by']}"
        )

    # 4th call: circuit should be open
    r4 = syscall_bridge.engram_invoke(
        "crash_op", {}, actor="test4", rate_limit=100.0,
    )
    assert r4["ok"] is False
    assert r4["blocked_by"] == "circuit_breaker_open", (
        f"expected circuit_breaker_open, got {r4['blocked_by']}"
    )
    assert r4["circuit_state"] == "open"
