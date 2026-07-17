"""ENGRAM_LOG_LEVEL: a datacenter operator must be able to quiet the per-request
flow logs (one INFO line per write/recall) without patching code. Found by the
gateway load probe (2026-07-17): the level was hardcoded INFO and the env var
silently did nothing — the exact "declared-but-off" class the mandate bans.

Runs in a subprocess: structlog config is process-global and import-time.
"""
from __future__ import annotations

import subprocess
import sys

_PROG = (
    "from verimem.observability import log; "
    "log.info('info-line-marker'); log.warning('warning-line-marker')"
)


def _run(level: str | None) -> str:
    env = {"PYTHONIOENCODING": "utf-8"}
    import os
    env = {**os.environ, **env}
    env.pop("ENGRAM_LOG_LEVEL", None)
    if level is not None:
        env["ENGRAM_LOG_LEVEL"] = level
    r = subprocess.run([sys.executable, "-c", _PROG], env=env,
                       capture_output=True, text=True, timeout=120)
    return r.stdout + r.stderr


def test_default_keeps_info():
    out = _run(None)
    assert "info-line-marker" in out
    assert "warning-line-marker" in out


def test_warning_level_drops_info_keeps_warning():
    out = _run("warning")
    assert "info-line-marker" not in out
    assert "warning-line-marker" in out


def test_bogus_level_falls_back_to_info():
    out = _run("banana")
    assert "info-line-marker" in out  # never crash, never silence everything
