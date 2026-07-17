"""Hang watchdog: when a tool call exceeds a budget, dump ALL thread stacks to
~/.engram/hang-traces/ so an intermittent multi-minute hang becomes diagnosable
(shows the exact blocking frame). OBSERVABILITY ONLY — never changes behaviour,
never raises, never cancels the call. Fast calls leave NO file.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

import verimem._hang_watchdog as hw


def _trace_files(d: Path):
    return list(d.glob("hang-*.txt")) if d.exists() else []


def test_slow_body_leaves_a_stack_dump(tmp_path, monkeypatch):
    monkeypatch.setattr(hw, "_TRACE_DIR", tmp_path)
    with hw.hang_trace("slow_tool", budget_s=0.3):
        time.sleep(1.2)  # exceeds the 0.3s budget → watchdog must fire + dump
    files = _trace_files(tmp_path)
    assert len(files) == 1, f"expected 1 hang trace, got {files}"
    body = files[0].read_text(encoding="utf-8")
    assert "slow_tool" in body
    assert "Traceback" in body or "File " in body, "dump must contain a stack"


def test_fast_body_leaves_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(hw, "_TRACE_DIR", tmp_path)
    with hw.hang_trace("fast_tool", budget_s=5):
        pass  # completes instantly → no dump → file cleaned up
    assert _trace_files(tmp_path) == [], "fast call must not leave a trace file"


def test_never_raises_on_unwritable_dir(monkeypatch):
    # A broken trace dir must NOT break the wrapped call (observability is best-effort).
    monkeypatch.setattr(hw, "_TRACE_DIR", Path("Z:/nonexistent/cannot/create/here"))
    ran = {"v": False}
    with hw.hang_trace("tool", budget_s=0.2):
        ran["v"] = True
    assert ran["v"], "the wrapped body must always run even if tracing fails"


def test_concurrent_arm_does_not_error(tmp_path, monkeypatch):
    # faulthandler's timer is process-global; a nested arm must skip cleanly,
    # never raise, and still run the inner body.
    monkeypatch.setattr(hw, "_TRACE_DIR", tmp_path)
    inner_ran = {"v": False}
    with hw.hang_trace("outer", budget_s=5):
        with hw.hang_trace("inner", budget_s=5):
            inner_ran["v"] = True
    assert inner_ran["v"]
