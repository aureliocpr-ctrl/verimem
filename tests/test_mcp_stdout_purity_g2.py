"""G2 (RELEASE_GATE): the MCP stdio server's stdout must be protocol-pure.

Found by the fresh-venv install smoke (2026-07-04): `engram mcp` — the
DOCUMENTED way to run the server — emitted structlog lines on stdout
interleaved with JSON-RPC frames. Root cause: engram/cli.py imports
observability at module top, so structlog configures its default stdout
logger BEFORE mcp_server.py's `os.environ.setdefault("HIPPO_LOG_STDERR", "1")`
can take effect (and cache_logger_on_first_use freezes it). Launching
`python -m verimem.mcp_server` directly was fine; the CLI path was not.

This test drives the REAL CLI entrypoint in a subprocess and asserts every
stdout line up to and including the initialize response parses as JSON.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def test_engram_mcp_stdout_is_json_rpc_only() -> None:
    """⚠️ 2026-08-14 — questo banco poteva accusare il server SBAGLIANDO.

    Se il processo muore all'avvio (un import rotto, un entrypoint spostato),
    ``readline()`` rende subito stringa vuota, il ciclo esce e si legge *«no
    initialize response on stdout»* — cioè **«il server non risponde»**, quando
    il fatto è **«il server non è mai partito»**. Due guasti diversi, con cure
    opposte, sotto lo stesso messaggio.
    🔑 E ``stderr=DEVNULL`` buttava via l'unico posto dove stava il motivo. Ora
    lo stderr va su un file temporaneo — non su ``PIPE``, che su un server
    loquace può riempire il buffer e bloccare tutto — e la sua coda entra nel
    messaggio insieme al codice di uscita.
    """
    env = dict(os.environ)
    env.pop("HIPPO_LOG_STDERR", None)  # must not rely on the caller setting it
    err = tempfile.TemporaryFile(mode="w+")
    proc = subprocess.Popen(
        [sys.executable, "-c",
         "import sys; sys.argv=['engram','mcp']; "
         "from verimem.cli import app; app()"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=err, text=True, cwd=str(_REPO), env=env)
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
        if not got_response:
            # il verdetto del processo PRIMA della diagnosi sul protocollo
            morto = proc.poll()
            err.seek(0)
            coda = err.read()[-500:]
            assert morto is None, (
                f"il server MCP e' MORTO prima di rispondere: "
                f"returncode={morto} — non e' un difetto del protocollo. "
                f"stderr(coda)={coda!r}")
            raise AssertionError(
                f"no initialize response on stdout (il processo e' ancora "
                f"vivo, quindi il difetto e' nel protocollo). "
                f"stderr(coda)={coda!r}")
    finally:
        proc.kill()
        proc.wait(timeout=30)
        err.close()
