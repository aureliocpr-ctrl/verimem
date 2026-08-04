"""surface onesta — un default non può essere il nome di una superficie reale.

Misurato da ws4 il 2026-08-04 sul corpus reale: 9603 flow.write → 9357 "sdk",
246 "gateway", ZERO "mcp" — con 438 chiamate MCP di scrittura nello stesso
file. La causa: il default di ``_ambient()`` era la stringa "sdk" e l'unico
setter era mcp_server (che `engram mcp` non raggiunge mai prima che la CLI
abbia già importato). Un cruscotto non distingue un default da un dato.

Il contratto nuovo:
- nessun entrypoint dichiarato → ``surface="unknown"`` (dice la verità);
- ``cli.main`` dichiara "cli" (setdefault: un env esplicito vince);
- ``verimem mcp`` passa DA cli.main, quindi arriva al subcommand con "cli"
  addosso: il valore derivato-dal-percorso cede a "mcp", un valore esplicito
  dell'operatore resta — è esattamente la trappola one-entrypoint-chain
  che produceva zero eventi mcp.
"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

from verimem import flow_events


@pytest.fixture(autouse=True)
def _pulisci_env(monkeypatch):
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    monkeypatch.delenv("VERIMEM_ACTOR", raising=False)
    monkeypatch.delenv("ENGRAM_ACTOR", raising=False)
    flow_events.reset_flow_context()


def test_default_e_unknown_non_sdk():
    assert flow_events._ambient()["surface"] == "unknown", (
        "il default era il nome di una superficie REALE: 97% del corpus "
        "taggato con una scelta che nessuno ha fatto")


def test_env_esplicito_vince(monkeypatch):
    monkeypatch.setenv("ENGRAM_FLOW_SURFACE", "gateway")
    assert flow_events._ambient()["surface"] == "gateway"


def test_cli_main_dichiara_cli():
    """Subprocess vero: cli.main() setta la surface PRIMA di processare il
    comando (--help esce subito, il setdefault è già avvenuto)."""
    code = (
        "import os, sys\n"
        "from verimem.cli import main\n"
        "sys.argv = ['verimem', '--help']\n"
        "try:\n"
        "    main()\n"
        "except SystemExit:\n"
        "    pass\n"
        "print('SURFACE=' + os.environ.get('ENGRAM_FLOW_SURFACE', 'MISSING'))\n"
    )
    env = {k: v for k, v in os.environ.items()
           if k != "ENGRAM_FLOW_SURFACE"}
    out = subprocess.run([sys.executable, "-c", code], env=env,
                         capture_output=True, text=True, timeout=120)
    assert "SURFACE=cli" in out.stdout, out.stdout + out.stderr


def test_comando_mcp_cede_da_cli_a_mcp(monkeypatch):
    """Il comando vero (`verimem mcp`), col server patchato a no-op: il
    valore derivato dal percorso ("cli") cede a "mcp"."""
    from typer.testing import CliRunner

    import verimem.mcp_server as mcp_server
    from verimem.cli import app
    monkeypatch.setattr(mcp_server, "main", lambda: None)
    monkeypatch.setenv("ENGRAM_FLOW_SURFACE", "cli")   # come dopo cli.main
    res = CliRunner().invoke(app, ["mcp"])
    assert res.exit_code == 0, res.output
    assert os.environ.get("ENGRAM_FLOW_SURFACE") == "mcp"


def test_comando_mcp_rispetta_env_operatore(monkeypatch):
    from typer.testing import CliRunner

    import verimem.mcp_server as mcp_server
    from verimem.cli import app
    monkeypatch.setattr(mcp_server, "main", lambda: None)
    monkeypatch.setenv("ENGRAM_FLOW_SURFACE", "lab-bench-7")
    res = CliRunner().invoke(app, ["mcp"])
    assert res.exit_code == 0, res.output
    assert os.environ.get("ENGRAM_FLOW_SURFACE") == "lab-bench-7", (
        "un valore esplicito dell'operatore non si tocca")
