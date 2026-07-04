"""G2 (RELEASE_GATE): the MCP stdio server's stdout must be protocol-pure.

Found by the fresh-venv install smoke (2026-07-04): `engram mcp` — the
DOCUMENTED way to run the server — emitted structlog lines on stdout
interleaved with JSON-RPC frames. Root cause: engram/cli.py imports
observability at module top, so structlog configures its default stdout
logger BEFORE mcp_server.py's `os.environ.setdefault("HIPPO_LOG_STDERR", "1")`
can take effect (and cache_logger_on_first_use freezes it). Launching
`python -m engram.mcp_server` directly was fine; the CLI path was not.

This test drives the REAL CLI entrypoint in a subprocess and asserts every
stdout line up to and including the initialize response parses as JSON.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def test_engram_mcp_stdout_is_json_rpc_only() -> None:
    env = dict(os.environ)
    env.pop("HIPPO_LOG_STDERR", None)  # must not rely on the caller setting it
    proc = subprocess.Popen(
        [sys.executable, "-c",
         "import sys; sys.argv=['engram','mcp']; "
         "from engram.cli import app; app()"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, cwd=str(_REPO), env=env)
    try:
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
               "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                          "clientInfo": {"name": "g2", "version": "0"}}}
        proc.stdin.write(json.dumps(req) + "\n")  # type: ignore[union-attr]
        proc.stdin.flush()  # type: ignore[union-attr]
        got_response = False
        for _ in range(50):  # bounded: no unbounded read on a hung server
            line = proc.stdout.readline()  # type: ignore[union-attr]
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)  # any non-JSON stdout line fails HERE
            if msg.get("id") == 1:
                assert "result" in msg, f"initialize failed: {msg}"
                got_response = True
                break
        assert got_response, "no initialize response on stdout"
    finally:
        proc.kill()
        proc.wait(timeout=30)
