"""FORGIA pezzo #63 — black-box test for `scripts/bench_with_without_hippo.py`.

Runs the actual CLI as a subprocess with `--providers mock` and the
default suite. Verifies the JSON outputs land where expected and have
the documented shape. This is the regression guard for the most
common end-user invocation (`make bench-mock`).

Three invariants:

  1. CLI exits 0 with `--providers mock`.
  2. results.json + summary.json exist + non-empty + parse as JSON.
  3. summary.json has the expected key shape `condition|provider`
     with `success_rate` / `mean_tokens` / `mean_latency_s` etc.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts" / "bench_with_without_hippo.py"
)


def test_bench_mock_cli_smokes_clean(tmp_path: Path):
    env = os.environ.copy()
    env["HIPPO_DATA_DIR"] = str(tmp_path)
    env["HIPPO_OFFLINE"] = "1"

    proc = subprocess.run(
        [sys.executable, str(_SCRIPT),
         "--providers", "mock",
         "--quiet",
         "--max-tasks", "2",
         "--output-dir", str(tmp_path)],
        env=env, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, (
        f"bench CLI failed: stdout={proc.stdout[:500]} stderr={proc.stderr[:500]}"
    )

    results = tmp_path / "bench_with_without_hippo.results.json"
    summary = tmp_path / "bench_with_without_hippo.summary.json"
    assert results.exists() and results.stat().st_size > 0
    assert summary.exists() and summary.stat().st_size > 0

    rs = json.loads(results.read_text(encoding="utf-8"))
    assert isinstance(rs, list) and rs, rs
    expected_keys = {"condition", "provider", "task_id", "success",
                     "tokens", "latency_s", "attempts", "error", "extra"}
    for r in rs:
        assert expected_keys <= r.keys(), r

    sm = json.loads(summary.read_text(encoding="utf-8"))
    assert isinstance(sm, dict) and sm, sm
    for key, stats in sm.items():
        assert "|" in key, key
        for metric in ("n", "success_rate", "mean_tokens",
                        "mean_latency_s", "mean_attempts", "n_errors"):
            assert metric in stats, (key, metric, stats)


def test_bench_mock_cli_with_save_md(tmp_path: Path):
    env = os.environ.copy()
    env["HIPPO_DATA_DIR"] = str(tmp_path)
    env["HIPPO_OFFLINE"] = "1"
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT),
         "--providers", "mock",
         "--quiet",
         "--max-tasks", "2",
         "--save-md",
         "--output-dir", str(tmp_path)],
        env=env, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    md = tmp_path / "bench_with_without_hippo.summary.md"
    assert md.exists() and md.stat().st_size > 0
    body = md.read_text(encoding="utf-8")
    assert "provider" in body
    assert "condition" in body
    assert "|" in body  # markdown table delimiter
