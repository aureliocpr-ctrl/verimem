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
    # ⚠️ `encoding="utf-8"` NON e' cosmesi, ed e' il motivo per cui questo test
    # cadeva SOLO in CI. Meccanismo provato il 20/08, non congetturato:
    #   1. Click/Typer su Windows scrive il riquadro dell'aiuto in UTF-8 anche
    #      verso una pipe (`─ ┐ │` = e2 94 80 / e2 94 90 / e2 94 82).
    #   2. `text=True` senza `encoding` decodifica con la codepage ANSI del
    #      GENITORE. In CI e' cp1252, dove `0x90` non esiste.
    #   3. La decodifica esplode DENTRO il thread lettore di `subprocess`
    #      (`subprocess.py:_readerthread`), che muore senza appendere nulla.
    #   4. `subprocess.py` chiude con `stdout = stdout[0] if stdout else None`:
    #      lista vuota ⇒ **stdout diventa `None` in SILENZIO**, con
    #      `returncode=0` e `stderr=''`. Nessun `TimeoutExpired`, nessun errore.
    # 🔑 Il guasto e' del BANCO, non del prodotto: i 7146 byte prodotti sono
    #    corretti, e' il lettore che li interpreta con la tabella sbagliata.
    # 🔬 A/B nella stessa esecuzione, SHA `c2805129` fermo prima e dopo:
    #    `PYTHONUTF8=0` -> 1 failed  ·  `PYTHONUTF8=1` -> 5 passed.
    #    Non si vedeva in locale perche' la macchina aveva `PYTHONUTF8=1`.
    # `errors="replace"` e' la seconda meta': un byte inatteso non deve piu'
    # poter uccidere la misura in silenzio: al massimo sporca il testo.
    out = subprocess.run([sys.executable, "-c", code], env=env,
                         capture_output=True, encoding="utf-8",
                         errors="replace", timeout=120)
    # 🔑 Stesso difetto gia' curato in `test_la_ricevuta_non_diceva_quale_cifra
    # _mancava.py` (07675ac6): il fallimento del banco MASCHERA quello che il
    # banco esiste per mostrare.
    # 📌 Nel run 31609651506 questo era l'UNICO file rosso su Windows e su
    # nessun'altra piattaforma — 20 file cadono ovunque, questo solo li'.
    # ⚠️ L'ESITO DEL PROCESSO ENTRA NEL MESSAGGIO, e non e' cosmesi: con
    # `stdout` vuoto, un processo MORTO e un processo VIVO che non ha stampato
    # si leggono uguali. `rc=` li separa in un colpo d'occhio — ed e' la forma
    # che `test_nessun_banco_nuovo_ignora_l_esito_del_subprocess.py` pretende.
    _uscita = (f"rc={out.returncode} "
               + (out.stdout or "") + (out.stderr or ""))
    assert "SURFACE=cli" in (out.stdout or ""), _uscita


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
