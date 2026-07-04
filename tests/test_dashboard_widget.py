"""Cycle 367 (2026-05-23) — DASHBOARD WIDGET falsifiable contracts.

Contracts:
  (a) collect_state returns required keys
  (b) render_text contains all 5 stack layers
  (c) render_json roundtrips through json.loads
  (d) After engram_invoke, summary reflects the call
"""
from __future__ import annotations

import json

import pytest


def test_collect_state_returns_required_keys() -> None:
    """Contract (a): all documented keys present."""
    from engram.dashboard_widget import collect_state
    s = collect_state(tail_n=10)
    required = {
        "timestamp", "audit_tail_recent", "audit_summary_by_op",
        "circuit_states", "rate_limit_recent", "manifest_ops",
        "stack_layers",
    }
    assert required.issubset(set(s.keys()))
    assert isinstance(s["timestamp"], float)
    assert isinstance(s["manifest_ops"], list)
    assert "recall" in s["manifest_ops"]


def test_render_text_contains_all_5_stack_layers() -> None:
    """Contract (b): all 5 layers cycle 362-368 mentioned."""
    from engram.dashboard_widget import collect_state, render_text
    s = collect_state(tail_n=5)
    text = render_text(s)
    for layer_keyword in ("mesh_memory", "resonant_merge", "syscall_bridge",
                          "op_supervisor", "capability_token"):
        assert layer_keyword in text, (
            f"render_text missing '{layer_keyword}' layer marker"
        )
    assert "ENGRAM DASHBOARD" in text


def test_render_json_roundtrips() -> None:
    """Contract (c): render_json output is valid JSON."""
    from engram.dashboard_widget import collect_state, render_json
    s = collect_state(tail_n=5)
    text = render_json(s)
    parsed = json.loads(text)
    assert parsed["manifest_ops"] == s["manifest_ops"]
    assert parsed["timestamp"] == s["timestamp"]


def test_dashboard_reflects_engram_invoke_call(tmp_path, monkeypatch) -> None:
    """Contract (d): after engram_invoke, dashboard summary shows the call."""
    if not _vec_bus_available():
        pytest.skip("vec_bus not available")
    from engram import op_supervisor, syscall_bridge
    from engram.dashboard_widget import collect_state

    audit = tmp_path / "audit.jsonl"
    monkeypatch.setattr(syscall_bridge, "ENGRAM_AUDIT_LOG", audit)
    monkeypatch.setattr(op_supervisor, "_DEFAULT_SUPERVISOR",
                        op_supervisor.OpSupervisor(max_failures=100))
    syscall_bridge._RATE_BUCKETS.clear()

    # Invoke 3 ops (mesh_fetch is cheap)
    for i in range(3):
        syscall_bridge.engram_invoke(
            "mesh_fetch", {"channel": f"test/dash/{i}"},
            actor="dash_test",
        )

    # Also one hallucinated op (blocked)
    syscall_bridge.engram_invoke(
        "fake_op_inventato", {}, actor="dash_test",
    )

    s = collect_state(tail_n=10)
    # mesh_fetch should appear with ok=3
    assert "mesh_fetch" in s["audit_summary_by_op"]
    assert s["audit_summary_by_op"]["mesh_fetch"].get("ok", 0) == 3
    # fake_op_inventato should appear with not_in_manifest=1
    assert "fake_op_inventato" in s["audit_summary_by_op"]
    assert s["audit_summary_by_op"]["fake_op_inventato"].get(
        "not_in_manifest", 0
    ) == 1
    # mesh_fetch circuit should be tracked + closed (no failures)
    assert "mesh_fetch" in s["circuit_states"]
    assert s["circuit_states"]["mesh_fetch"]["circuit"] == "closed"


def _vec_bus_available() -> bool:
    try:
        from clp.agentos import vec_bus  # noqa: F401
        return True
    except ImportError:
        return False
