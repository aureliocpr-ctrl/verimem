"""L'audit log si puo' leggere senza aprire il codice.

``telemetry_analyzer`` aggrega l'audit JSONL del server MCP in un rapporto per
tool — conteggi, latenze p50/p99/max, esiti, quanti processi diversi l'hanno
chiamato. Era completo e irraggiungibile da ogni superficie, mentre il log
cresceva: sulla macchina di Aurelio, il 2026-07-30, **14.559 chiamate in 1.9 MB**.

Due numeri che si vedono SOLO leggendolo, e che nessuno stava guardando:

    121 tool distinti chiamati, su 244 esposti
    hippo_facts_recall: p50 = 47771 ms

Metà dei tool non e' mai stata invocata, e la mediana di uno dei piu' usati e'
di quarantasette secondi. Un prodotto che espone 244 strumenti e non sa quali
servano sta pagando un costo che non misura — e la latenza mediana e' il
genere di cosa che si scopre quando qualcuno si lamenta, non quando succede.

Sola lettura: il rapporto non tocca il log.
"""
from __future__ import annotations

import json
import re

import pytest
from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@pytest.fixture()
def log(tmp_path, monkeypatch):
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    righe = [
        {"ts": 1.0, "tool": "hippo_recall", "caller_pid": 1,
         "outcome": "ok", "latency_ms": 10.0},
        {"ts": 2.0, "tool": "hippo_recall", "caller_pid": 2,
         "outcome": "ok", "latency_ms": 30.0},
        {"ts": 3.0, "tool": "hippo_remember", "caller_pid": 1,
         "outcome": "rejected_empty", "latency_ms": 5.0},
    ]
    p = tmp_path / "mcp_audit.log"
    p.write_text("\n".join(json.dumps(r) for r in righe) + "\n",
                 encoding="utf-8")
    return p


def _out(args):
    r = runner.invoke(app, args)
    testo = _ANSI.sub("", r.output)
    assert r.exit_code == 0, testo
    return testo


def test_il_comando_esiste_e_conta_le_chiamate(log):
    testo = _out(["telemetry"])
    assert "hippo_recall" in testo, testo
    assert "3" in testo, testo          # total_calls


def test_dice_le_LATENZE_non_solo_i_conteggi(log):
    """Il conteggio dice cosa si usa; la latenza dice cosa fa male."""
    testo = _out(["telemetry"])
    assert "p50" in testo.lower() or "ms" in testo.lower(), testo


def test_dice_gli_ESITI_perche_un_tool_molto_chiamato_e_sempre_in_errore_e_un_difetto(log):
    testo = _out(["telemetry"])
    assert "rejected_empty" in testo or "rejected" in testo, testo


def test_json_per_comporlo_in_uno_script(log):
    testo = _out(["telemetry", "--json"])
    dati = json.loads(testo[testo.index("{"):testo.rindex("}") + 1])
    assert dati["total_calls"] == 3
    assert dati["per_tool"]["hippo_recall"]["count"] == 2


def test_senza_log_lo_dice_invece_di_fingere_zero(tmp_path, monkeypatch):
    """Un rapporto vuoto e un log assente sono due cose diverse: la prima dice
    «nessuno ha chiamato niente», la seconda «non so»."""
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    testo = _out(["telemetry"])
    assert "no audit log" in testo.lower() or "non c" in testo.lower(), testo
