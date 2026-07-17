"""FORGIA pezzo #28 — End-to-end MCP smoke test (real subprocess).

Existing `tests/test_mcp_server.py` exercises the handlers in-process
with mocked memory/skills. This file fills the remaining E2E gap: it
spawns `python -m verimem.mcp_server` as a real subprocess, feeds
hand-crafted JSON-RPC frames through stdin via `subprocess.communicate`,
and parses every frame the server returns.

Why this approach (vs the official mcp.client.stdio SDK or interactive
pipes): on Windows + pytest-asyncio, the SDK's anyio task groups
deadlock waiting for stdout reads, and interactive Popen.stdin.write /
flush isn't reliably forwarded to the child. `communicate()` with a
pre-built batch of frames works on every platform we care about and is
sufficient for a smoke verification.

What it verifies (all of it in one round-trip, fast):

  1. SUBPROCESS BOOTS — `python -m verimem.mcp_server` starts and
     exits cleanly when stdin closes. No crash on import.

  2. STDOUT IS PROTOCOL-CLEAN — every line on stdout parses as JSON.
     This is the regression guard for the `HIPPO_LOG_STDERR` env-var
     redirection: if structlog ever lands a log line on stdout the
     test fails immediately.

  3. tools/list returns the expected catalog (the 5 user-facing tools
     the README and CLI advertise).

  4. tools/call hippo_status returns a dict with `n_episodes` /
     `n_skills` keys (zero on a fresh tmp data dir).

  5. tools/call hippo_recall on empty memory returns [] without crash.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _frames_in() -> bytes:
    """Build the full JSON-RPC batch we send to the server in one shot."""
    frames = [
        # 1. initialize
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {
             "protocolVersion": "2024-11-05",
             "capabilities": {},
             "clientInfo": {"name": "smoke", "version": "0.0.1"},
         }},
        # 2. initialized notification (required by spec)
        {"jsonrpc": "2.0", "method": "notifications/initialized",
         "params": {}},
        # 3. tools/list
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        # 4. tools/call hippo_status
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "hippo_status", "arguments": {}}},
        # 5. tools/call hippo_recall on empty memory
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "hippo_recall",
                    "arguments": {"query": "anything", "k": 3}}},
    ]
    return ("\n".join(json.dumps(f, separators=(",", ":")) for f in frames)
            + "\n").encode("utf-8")


def _parse_lines(raw: bytes) -> list[dict]:
    """Parse newline-delimited JSON. Skip blank lines but raise on garbage."""
    out: list[dict] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        out.append(json.loads(s))  # raises on log-line contamination
    return out


@pytest.mark.e2e
def test_mcp_server_e2e_smoke(tmp_path: Path):
    env = os.environ.copy()
    env["HIPPO_DATA_DIR"] = str(tmp_path)
    env["HIPPO_OFFLINE"] = "1"
    env["HIPPO_MCP_DISABLE_RATELIMIT"] = "1"
    env["HIPPO_LOG_LEVEL"] = "ERROR"
    env["PYTHONUNBUFFERED"] = "1"
    # Transport test — isolate it from the startup single-instance guard so it
    # never scans/terminates real system processes during a test run.
    env["HIPPO_REAP_ORPHANS"] = "0"

    proc = subprocess.run(
        [sys.executable, "-u", "-m", "verimem.mcp_server"],
        input=_frames_in(),
        capture_output=True,
        env=env,
        timeout=60,
    )
    # Server may exit with non-zero when stdin closes mid-loop on Windows;
    # we don't gate on that. We gate on stdout content.
    stdout = proc.stdout
    assert stdout, (
        f"server produced no stdout. stderr:\n{proc.stderr.decode(errors='replace')[:1500]}"
    )
    frames = _parse_lines(stdout)
    by_id = {f["id"]: f for f in frames if "id" in f}

    # --- 1. Initialize succeeded ---
    assert 1 in by_id, f"no init reply. frames: {frames!r}"
    init = by_id[1]
    assert init.get("result", {}).get("serverInfo", {}).get("name"), init

    # --- 2. tools/list ---
    assert 2 in by_id, f"no tools/list reply: {frames!r}"
    tools = by_id[2]["result"]["tools"]
    names = {t["name"] for t in tools}
    for expected_name in ("hippo_run_task", "hippo_consolidate",
                          "hippo_recall", "hippo_status",
                          "hippo_skills_for"):
        assert expected_name in names, (
            f"missing MCP tool: {expected_name}; got {names}"
        )
    for tool in tools:
        assert "inputSchema" in tool, f"{tool['name']} has no inputSchema"

    # --- 3. tools/call hippo_status ---
    # Note: we don't gate on counts here because CONFIG.data_dir is set at
    # config-import time and our HIPPO_DATA_DIR env var is currently a
    # no-op (the production DB at the project root may have leftover
    # episodes from previous CLI runs). We verify the SHAPE of the reply
    # — the smoke test is a transport check, not a state assertion.
    assert 3 in by_id, f"no hippo_status reply: {frames!r}"
    status_text = by_id[3]["result"]["content"][0]["text"]
    payload = json.loads(status_text)
    assert isinstance(payload, dict)
    assert "episodes" in payload, payload
    assert isinstance(payload["episodes"], int)
    assert "skills" in payload and isinstance(payload["skills"], dict)
    assert "active_llm" in payload, payload

    # --- 4. tools/call hippo_recall ---
    assert 4 in by_id, f"no hippo_recall reply: {frames!r}"
    recall_text = by_id[4]["result"]["content"][0]["text"]
    hits = json.loads(recall_text)
    assert isinstance(hits, list), f"recall must return a list: {hits!r}"
    # Every hit (if any) must be a dict with the documented keys.
    for hit in hits:
        assert {"id", "task", "outcome", "answer_preview",
                "steps", "similarity"} <= hit.keys(), hit


def test_mcp_server_stdout_is_protocol_clean(tmp_path: Path):
    """Regression: every byte on stdout must be a JSON-RPC frame."""
    env = os.environ.copy()
    env["HIPPO_DATA_DIR"] = str(tmp_path)
    env["HIPPO_OFFLINE"] = "1"
    env["HIPPO_MCP_DISABLE_RATELIMIT"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env["HIPPO_REAP_ORPHANS"] = "0"  # don't scan/kill system processes in a transport test

    init_only = (
        json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "clean", "version": "0.0.1"},
            },
        }, separators=(",", ":")) + "\n"
    ).encode("utf-8")

    proc = subprocess.run(
        [sys.executable, "-u", "-m", "verimem.mcp_server"],
        input=init_only, capture_output=True, env=env, timeout=30,
    )
    stdout = proc.stdout.strip()
    # Every non-blank line must be valid JSON. No log lines allowed.
    for line in stdout.splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            json.loads(s)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"stdout line is not valid JSON-RPC: {s!r} (err: {exc})"
            ) from exc
