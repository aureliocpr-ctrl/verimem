"""Delegate-only servers never pay the moat-CE cold-load on the request thread.

Measured 2026-07-18 (probe, daemon down, HIPPO_ENCODE_DELEGATE_ONLY=1): the
FIRST gated write blocked 30.05s while the CE imported+built under the judge
lock — the exact hang-watchdog signature that froze every MCP tool call that
morning. Fix: in delegate-only mode the load moves to a one-shot background
thread; until warm, try_local_score returns None and the gate degrades to the
honest L4-skipped advisory. SDK processes (no delegate-only) keep the
synchronous one-time load.
"""
from __future__ import annotations

import threading
import time

import verimem.local_grounding as lg


class _SlowBuild:
    """Fake scorer builder: takes `delay` to build, then scores 88."""
    def __init__(self, delay):
        self.delay = delay
        self.built = threading.Event()

    def __call__(self, model_dir, *, max_length=512, **_kw):
        time.sleep(self.delay)
        self.built.set()
        return lambda batch: [88.0] * len(batch)


def _fresh_judge(tmp_path, monkeypatch, delay):
    builder = _SlowBuild(delay)
    monkeypatch.setattr(lg, "make_finetuned_scorer", builder)
    lg.reset_local_judge()
    lg.set_local_judge(lg.LocalGroundingJudge(model_dir=str(tmp_path)))
    return builder


def test_delegate_only_first_score_returns_fast_and_warms_in_background(
        tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    builder = _fresh_judge(tmp_path, monkeypatch, delay=0.6)
    try:
        t0 = time.time()
        out = lg.try_local_score("We use Postgres.", "Analytics on Postgres.")
        dt = time.time() - t0
        assert out is None, "cold CE in delegate-only must degrade, not load inline"
        assert dt < 0.3, f"request thread paid the load anyway: {dt:.2f}s"
        # the background warm converges: soon the SAME call scores normally
        assert builder.built.wait(5), "background warm never ran"
        deadline = time.time() + 5
        scored = None
        while time.time() < deadline:
            scored = lg.try_local_score("We use Postgres.", "Analytics on Postgres.")
            if scored is not None:
                break
            time.sleep(0.05)
        assert scored is not None and scored[0] == 88.0, f"never converged: {scored}"
    finally:
        lg.reset_local_judge()


def test_without_delegate_only_sdk_load_stays_synchronous(tmp_path, monkeypatch):
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    _fresh_judge(tmp_path, monkeypatch, delay=0.1)
    try:
        out = lg.try_local_score("We use Postgres.", "Analytics on Postgres.")
        assert out is not None and out[0] == 88.0, (
            "SDK (non-delegate) must keep the synchronous one-time load")
    finally:
        lg.reset_local_judge()


def test_injected_warm_scorer_unaffected_by_delegate_only(monkeypatch):
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    lg.reset_local_judge()
    lg.set_local_judge(lg.LocalGroundingJudge(
        model_dir="/x", scorer=lambda batch: [77.0] * len(batch)))
    try:
        out = lg.try_local_score("src", "fact")
        assert out is not None and out[0] == 77.0, (
            "an already-warm scorer must keep scoring in delegate-only mode")
    finally:
        lg.reset_local_judge()
