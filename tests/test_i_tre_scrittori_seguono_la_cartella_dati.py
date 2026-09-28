"""T208 — tre scrittori mettono file nella HOME anche quando la cartella dati è altrove.

Il prodotto ha UN risolutore della cartella dati (`CONFIG.data_dir`: precedenza
`HIPPO_DATA_DIR` → `ENGRAM_DATA_DIR` → default), e il giornale degli eventi ci
passa da quando lo stesso difetto aveva inquinato le misure di tutti. Tre
scrittori no, e scrivono in `~/.engram` qualunque cosa l'utente abbia scelto:
  - l'audit della sandbox (`sandbox.py`, `DEFAULT_AUDIT_ROOT` fissato all'import);
  - l'audit delle chiamate `sandbox_exec` (`mcp_server._sandbox_replay_audit`);
  - il file di debug del campionamento MCP (`llm.py`, a OGNI risposta).
Letto il 24/09: l'audit della sandbox nella home ha 31 righe del 23/09 che sono
comandi di test (`echo deterministic_payload`, `rm -rf /tmp/should_not_run`…),
lanciati da cartelle temporanee di pytest e da worktree di banco.

⚠️ IL RED NON DEVE SCRIVERE NELLA HOME VERA. Per i due scrittori che leggono
`Path.home()` alla chiamata, `HOME` e `USERPROFILE` puntano a una home FINTA
del test. Per la sandbox, dove il percorso si fissa all'import con la home vera,
la cella chiede solo il PERCORSO (`audit_log_path`) e non scrive niente; il
costruttore fa un `mkdir` della cartella di audit, che sulla home vera esiste
già (sulla macchina di chi misura: dichiarato).

Ogni cella ha due metà: il file NASCE nella cartella dati del test — il
controllo positivo, senza il quale «niente in home» passerebbe anche con uno
scrittore rotto — e NIENTE nasce nella home finta.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def home_finta(tmp_path, monkeypatch):
    casa = tmp_path / "home-finta"
    casa.mkdir()
    monkeypatch.setenv("HOME", str(casa))
    monkeypatch.setenv("USERPROFILE", str(casa))
    monkeypatch.delenv("ENGRAM_SANDBOX_AUDIT_DIR", raising=False)
    assert Path.home() == casa, f"la home finta non ha preso: {Path.home()}"
    return casa


def _cartella_dati() -> Path:
    from verimem.config import CONFIG
    return Path(str(CONFIG.data_dir))


def _file_sotto(radice: Path) -> list[str]:
    return sorted(str(p.relative_to(radice)) for p in radice.rglob("*") if p.is_file())


def test_l_audit_della_sandbox_segue_la_cartella_dati():
    """Solo il percorso: nessuna scrittura (vedi il docstring del modulo)."""
    from verimem.sandbox import SandboxedShell
    dove = SandboxedShell().audit_log_path
    dati = _cartella_dati()
    assert dati in dove.parents, (
        f"l'audit della sandbox andrebbe in {dove}, fuori dalla cartella dati {dati}")


def test_l_audit_delle_chiamate_sandbox_exec_segue_la_cartella_dati(home_finta):
    from verimem.mcp_server import _sandbox_replay_audit
    _sandbox_replay_audit(cmd="echo t208", cwd=None, action="dry_run",
                          matched_rule="", returncode=0, elapsed_s=0.0,
                          stdout="", stderr="", dry_run=True)
    dati = _cartella_dati()
    nella_cartella = [f for f in _file_sotto(dati) if "sandbox-audit" in f]
    assert nella_cartella, (
        f"nessun audit nella cartella dati {dati}; nella home finta: "
        f"{_file_sotto(home_finta)}")
    assert not _file_sotto(home_finta), _file_sotto(home_finta)


def test_il_debug_del_campionamento_segue_la_cartella_dati(home_finta, monkeypatch):
    """Da T213 la traccia è spenta di default: qui si accende, perché la cella
    chiede DOVE finisce quando c'è (`test_il_debug_del_campionamento_e_spento_di_default.py`
    tiene il resto)."""
    monkeypatch.setenv("ENGRAM_SAMPLING_DEBUG_LOG", "1")
    from verimem.llm import MCPSamplingLLM

    class _SessioneFinta:
        async def create_message(self, **kw):  # noqa: ANN003
            return SimpleNamespace(content=SimpleNamespace(text="ok"), model="finto")

    llm = MCPSamplingLLM(loop=None, session=_SessioneFinta())
    asyncio.run(llm._async_complete(
        "sistema", [{"role": "user", "content": "domanda"}],
        temperature=0.0, max_tokens=16, stop_sequences=None))
    dati = _cartella_dati()
    assert (dati / "mcp_sampling_debug.log").is_file(), (
        f"nessun debug nella cartella dati {dati}; nella home finta: "
        f"{_file_sotto(home_finta)}")
    assert not _file_sotto(home_finta), _file_sotto(home_finta)
