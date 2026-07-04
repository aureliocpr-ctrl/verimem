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
    env["HIPPO_DATA_DIR"] = str(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        env=env, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, (
        f"ablation failed: stdout={proc.stdout[:500]} stderr={proc.stderr[:500]}"
    )
    out = tmp_path / "bench_recall_ablation.json"
    assert out.exists() and out.stat().st_size > 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(payload, list) and payload
    expected = {"cell", "mean_rank", "top1", "top3"}
    for cell in payload:
        assert expected <= cell.keys(), cell
