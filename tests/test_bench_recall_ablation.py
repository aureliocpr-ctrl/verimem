"""FORGIA pezzo #67 — smoke test for `scripts/bench_recall_ablation.py`.

The ablation runs in-process (no LLM) and writes a JSON to
`data/bench_recall_ablation.json`. We just check it exits 0 and
produces a non-empty JSON list.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "bench_recall_ablation.py"
)


@pytest.mark.e2e
def test_ablation_runs_and_writes_json(tmp_path: Path):
    env = os.environ.copy()
    # ⚠️ TUTTI E TRE GLI ALIAS, non il solo `HIPPO_`: le fixture del conftest
    # hanno gia' puntato `ENGRAM_DATA_DIR` e `VERIMEM_DATA_DIR` a un'ALTRA tmp,
    # e `os.environ.copy()` se li porta dietro. Il figlio allora avvisa «DATA_DIR
    # aliases disagree» — innocuo di suo, ma vedi il commento sullo stderr qui
    # sotto per il danno che ha fatto.
    for alias in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR",
                  "ENGRAM_DIR"):
        env[alias] = str(tmp_path)
    # ⚠️ E I PIN DEL MODELLO VANNO TOLTI, PER SUFFISSO. `conftest.py:11` pinna
    # `paraphrase-multilingual-MiniLM-L12-v2`, che e' il modello della SUITE; il
    # PRODOTTO usa `intfloat/multilingual-e5-base` (config.py:74) ed e' quello
    # che i workflow scaldano (`ci.yml` e `presidi-lenti.yml`). Ereditando il
    # pin, il figlio in CI cercava un modello che nessuno aveva scaricato e
    # moriva con::
    #
    #     OSError: We couldn't connect to 'https://huggingface.co' to load the
    #     files, and couldn't find them in the cached files.
    #
    # (run 32475919020 su `93d5e379`, 2026-08-21). Per SUFFISSO perche'
    # `_compat.py:136` propaga ogni `HIPPO_*` su `ENGRAM_*` e `VERIMEM_*`
    # all'import: togliendo il solo nome intero, il figlio ricostruisce il pin
    # dagli alias — misurato lo stesso giorno sul presidio multilingue.
    for chiave in [k for k in env
                   if k.endswith(("EMBEDDING_MODEL", "EMBEDDING_DIM"))]:
        env.pop(chiave, None)
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        # 120 s bastavano col modello a 384 dim gia' in cache; col modello del
        # prodotto c'e' anche il cold load (~17 s sui runner, misurato nel
        # warmup dello stesso run).
        env=env, capture_output=True, text=True, timeout=300,
    )
    # ⚠️ LA CODA DELLO STDERR, NON LA TESTA — e non e' un dettaglio di stile.
    # Con `stderr[:500]` i 500 caratteri erano tutti occupati dal warning
    # innocuo sugli alias DATA_DIR, e l'OSError vera restava FUORI: il referto
    # accusava la cosa sbagliata, e chi lo leggeva perdeva il tempo a curare un
    # avviso mentre il difetto era un altro. Le eccezioni stanno in FONDO a uno
    # stderr, i log rumorosi in cima.
    assert proc.returncode == 0, (
        f"ablation failed (rc={proc.returncode})\n"
        f"stdout (coda):\n{proc.stdout[-1000:]}\n"
        f"stderr (coda):\n{proc.stderr[-3000:]}"
    )
    out = tmp_path / "bench_recall_ablation.json"
    assert out.exists() and out.stat().st_size > 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(payload, list) and payload
    expected = {"cell", "mean_rank", "top1", "top3"}
    for cell in payload:
        assert expected <= cell.keys(), cell
