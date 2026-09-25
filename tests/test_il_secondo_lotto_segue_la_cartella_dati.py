"""T208, secondo lotto — gli altri file che il prodotto metteva nella HOME.

LA PROMESSA. `CONFIG.data_dir` e' l'unico risolutore della cartella dati: il README
(«Memory() … the library, the CLI and the MCP server all open the SAME store») e
`docs/GOVERNANCE.md` («Where the log lives … the log follows the store the caller
chose»). Il primo lotto (#136) ha portato li' l'audit della sandbox, l'audit di
`sandbox_exec` e il debug del campionamento. Qui gli altri sei, trovati dallo sweep:

  - le tracce dei blocchi (`_hang_watchdog.py`, fissate all'import su `Path.home()`);
  - i lotti del giudice interattivo (`interactive_judge.DATA_DIR`, idem);
  - lo stato del resonator (`resonator_cli`, default di argparse fissati all'import);
  - lo store che `syscall_bridge` interroga se non gli si passa `db_path`;
  - le statistiche del briefing e il modello di se' lette dal server MCP con
    `_env_data_dir() or ~/.engram`, che senza variabili NON e' la cartella del
    prodotto (su un'installazione nuova il prodotto usa `~/.verimem`);
  - l'hook che scrive `briefing.jsonl` (`docs/hooks/hippo_proactive_briefing.py`), che
    leggeva ENGRAM prima di HIPPO, ignorava VERIMEM e ricadeva sulla home.

COSA VEDE L'UTENTE. Sceglie una cartella dati, e trova tracce, lotti, stato e registri
nella sua home; o legge statistiche e modello di se' di uno store che non e' il suo.

⚠️ NIENTE SI SCRIVE NELLA HOME VERA. Dove il vecchio codice fissava il percorso
all'import, la cella chiede solo il PERCORSO; dove scrive, lo fa in un processo nuovo
con la home finta, o con una home finta del test.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]


def _cartella_dati() -> Path:
    from verimem.config import CONFIG
    return Path(str(CONFIG.data_dir))


def _dentro(percorso: Path, cartella: Path) -> bool:
    return Path(percorso).resolve().is_relative_to(Path(cartella).resolve())


@pytest.fixture
def home_finta(tmp_path, monkeypatch):
    casa = tmp_path / "home-finta"
    casa.mkdir()
    monkeypatch.setenv("HOME", str(casa))
    monkeypatch.setenv("USERPROFILE", str(casa))
    assert Path.home() == casa
    return casa


def test_le_tracce_dei_blocchi_vanno_nella_cartella_dati(monkeypatch):
    """Solo il percorso: il vecchio codice lo fissava all'import sulla home vera."""
    from verimem import _hang_watchdog as w
    monkeypatch.delenv("HIPPO_HANG_TRACE_DIR", raising=False)
    dove = w._cartella_tracce() if hasattr(w, "_cartella_tracce") else Path(w._TRACE_DIR)
    assert _dentro(dove, _cartella_dati()), (
        f"le tracce dei blocchi andrebbero in {dove}, fuori dalla cartella dati")


def test_i_lotti_del_giudice_interattivo_vanno_nella_cartella_dati():
    from verimem.interactive_judge import InteractiveJudge

    class _Trasporto:
        visti: list[dict] = []

        def ensure_session(self) -> str:
            return "finta"

        def run_batch(self, batch_md, items, timeout_s):  # noqa: ANN001
            self.visti.extend(items)
            return None

    t = _Trasporto()
    assert InteractiveJudge(transport=t).score_batch([("fonte", "fatto")]) is None
    assert t.visti, "il trasporto finto non e' stato chiamato: la cella non misura"
    risposta = Path(t.visti[0]["response_path"])
    assert _dentro(risposta, _cartella_dati()), (
        f"la risposta del giudice interattivo andrebbe in {risposta}, fuori dalla "
        f"cartella dati")


def test_lo_stato_del_resonator_va_nella_cartella_dati(tmp_path):
    """Il comando in un processo nuovo, con la home finta dall'avvio."""
    casa, dati = tmp_path / "casa", tmp_path / "dati"
    casa.mkdir()
    dati.mkdir()
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env.update({"HOME": str(casa), "USERPROFILE": str(casa), "HIPPO_DATA_DIR": str(dati),
                "ENGRAM_DATA_DIR": str(dati), "VERIMEM_DATA_DIR": str(dati),
                "ENGRAM_EVENT_LOG": str(tmp_path / "eventi.jsonl")})
    uscita = subprocess.run(
        [sys.executable, "-m", "verimem.resonator_cli", "remember", "una prova"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=RADICE, env=env, timeout=300)
    assert uscita.returncode == 0, uscita.stderr[-800:]
    nella_cartella = sorted(p.name for p in (dati / "resonator").glob("*")) \
        if (dati / "resonator").exists() else []
    nella_casa = sorted(str(p.relative_to(casa)) for p in casa.rglob("*") if p.is_file())
    assert nella_cartella, (
        f"nessuno stato del resonator nella cartella dati; nella home finta: {nella_casa}")
    assert not [f for f in nella_casa if "resonator" in f], nella_casa


def test_syscall_bridge_interroga_lo_store_della_cartella_dati(monkeypatch):
    from verimem import mesh_memory, syscall_bridge
    aperti: list[Path] = []
    monkeypatch.setattr(mesh_memory, "local_topk_embeddings",
                        lambda db, q, k=5: aperti.append(Path(db)) or [])
    r = syscall_bridge._op_topk_embeddings({"query_vec_bytes": b"\x00" * 1536, "k": 1})
    assert r.get("ok") and aperti, r
    assert _dentro(aperti[0], _cartella_dati()), (
        f"syscall_bridge interroga {aperti[0]}, fuori dalla cartella dati")


def test_il_server_mcp_legge_il_briefing_della_cartella_dati(home_finta, monkeypatch):
    """Senza variabili d'ambiente, il server deve leggere la cartella del PRODOTTO."""
    from verimem.mcp_server import call_tool
    dati = _cartella_dati()
    registro = dati / "audit" / "briefing.jsonl"
    registro.parent.mkdir(parents=True, exist_ok=True)
    registro.write_text(json.dumps({"ts": 1.0, "n_hits": 1, "n_keywords": 2,
                                    "latency_ms": 5.0, "top_matched": 1}) + "\n",
                        encoding="utf-8")
    for alias in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.delenv(alias, raising=False)
    risposta = asyncio.run(call_tool("hippo_briefing_stats", {}))
    esito = json.loads(risposta[0].text)
    assert esito.get("n_firings") == 1, (
        f"il server non ha letto il briefing della cartella dati {dati}: {esito}")


def _hook():
    spec = importlib.util.spec_from_file_location(
        "hook_briefing_t208", RADICE / "docs" / "hooks" / "hippo_proactive_briefing.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_l_hook_del_briefing_scrive_nella_cartella_scelta_nell_ordine_del_prodotto(
        home_finta, tmp_path, monkeypatch):
    a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
    for d in (a, b, c):
        (d / "semantic").mkdir(parents=True)
    for alias in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.delenv(alias, raising=False)
    hook = _hook()
    monkeypatch.setenv("HIPPO_DATA_DIR", str(a))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(b))
    assert hook._find_data_dir() == a, "l'hook non segue l'ordine del prodotto (HIPPO per primo)"
    monkeypatch.delenv("HIPPO_DATA_DIR")
    monkeypatch.delenv("ENGRAM_DATA_DIR")
    monkeypatch.setenv("VERIMEM_DATA_DIR", str(c))
    assert hook._find_data_dir() == c, "l'hook ignora VERIMEM_DATA_DIR"
