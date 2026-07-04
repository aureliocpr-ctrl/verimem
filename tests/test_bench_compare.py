"""FORGIA pezzo #55 — smoke test for `scripts/bench_compare.py`.

Three invariants:

  1. EQUAL FILES → exit 0, "within threshold" footer.
  2. REGRESSION (success_rate drops below threshold) → exit 1.
  3. PROVIDER ADDED in `after` (key absent from `before`) → no crash.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bench_compare.py"


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _run(before: Path, after: Path, *, threshold: float = 0.05) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(before), str(after),
         "--threshold", str(threshold)],
        capture_output=True, text=True, timeout=15,
    )
    return proc.returncode, proc.stdout


def test_equal_files_exit_zero(tmp_path: Path):
    cell = {"success_rate": 1.0, "mean_tokens": 50.0, "mean_latency_s": 0.5,
            "mean_attempts": 1.0, "n": 1.0, "n_errors": 0.0}
    payload = {"raw|p1": cell}
    b = tmp_path / "b.json"
    a = tmp_path / "a.json"
    _write(b, payload)
    _write(a, payload)
    code, out = _run(b, a)
    assert code == 0, out
    assert "within threshold" in out


def test_regression_exits_nonzero(tmp_path: Path):
    base = {"success_rate": 1.0, "mean_tokens": 50.0, "mean_latency_s": 0.5,
            "mean_attempts": 1.0, "n": 1.0, "n_errors": 0.0}
    regressed = {**base, "success_rate": 0.5}
    b = tmp_path / "b.json"
    a = tmp_path / "a.json"
    _write(b, {"raw|p1": base})
    _write(a, {"raw|p1": regressed})
    code, out = _run(b, a)
    assert code == 1, out
    assert "REGRESSION" in out


def test_empty_file_handled_cleanly(tmp_path: Path):
    """FORGIA pezzo #96: empty file → exit 2 (load error)."""
    b = tmp_path / "b.json"
    a = tmp_path / "a.json"
    b.write_text("", encoding="utf-8")
    _write(a, {})
    code, _ = _run(b, a)
    assert code == 2  # load error


def test_corrupt_file_handled_cleanly(tmp_path: Path):
    b = tmp_path / "b.json"
    a = tmp_path / "a.json"
    b.write_text("{not json}", encoding="utf-8")
    _write(a, {})
    code, _ = _run(b, a)
    assert code == 2


def test_non_dict_payload_handled_cleanly(tmp_path: Path):
    b = tmp_path / "b.json"
    a = tmp_path / "a.json"
    b.write_text("[1,2,3]", encoding="utf-8")
    _write(a, {})
    code, _ = _run(b, a)
    assert code == 2


def test_metric_latency_gating(tmp_path: Path):
    """FORGIA pezzo #115: --metric mean_latency_s gates on latency change."""
    base = {"success_rate": 1.0, "mean_tokens": 50.0, "mean_latency_s": 1.0,
            "mean_attempts": 1.0, "n": 1.0, "n_errors": 0.0}
    slowed = {**base, "mean_latency_s": 2.0}
    b = tmp_path / "b.json"
    a = tmp_path / "a.json"
    _write(b, {"raw|p1": base})
    _write(a, {"raw|p1": slowed})
    # 100% latency increase, threshold 5% → regression on mean_latency_s.
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(b), str(a),
         "--metric", "mean_latency_s", "--threshold", "0.05"],
        capture_output=True, text=True, timeout=15,
    )
    assert proc.returncode == 1, proc.stdout


def test_provider_added_in_after_does_not_crash(tmp_path: Path):
    base = {"success_rate": 1.0, "mean_tokens": 50.0, "mean_latency_s": 0.5,
            "mean_attempts": 1.0, "n": 1.0, "n_errors": 0.0}
    b = tmp_path / "b.json"
    a = tmp_path / "a.json"
    _write(b, {"raw|p1": base})
    _write(a, {"raw|p1": base, "raw|p2": base})
    code, out = _run(b, a)
    # No regression on the existing cell, the new provider is +∞
    # against zero-baseline but threshold-gate is on success_rate
    # only and both are 1.0 → exit 0.
    assert code == 0, out
