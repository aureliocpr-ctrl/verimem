"""FORGIA pezzo #66 — smoke test for `scripts/clean_bench_data.py`.

Three invariants:
  1. Dry-run never deletes (default).
  2. --apply removes matching prefix dirs.
  3. Non-matching dirs are untouched.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "clean_bench_data.py"
)


@pytest.fixture
def fake_bench_dirs(monkeypatch, tmp_path):
    """Make tempfile.gettempdir() resolve to tmp_path; create some fake dirs."""
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    targets = [tmp_path / "hippo_a", tmp_path / "hippo_b"]
    decoy = tmp_path / "other_thing"
    for d in targets + [decoy]:
        d.mkdir()
        (d / "marker.txt").write_text("x", encoding="utf-8")
    return targets, decoy


def test_dry_run_does_not_delete(fake_bench_dirs, tmp_path):
    targets, decoy = fake_bench_dirs
    # Force the script to use our patched tempdir by setting TMPDIR / TEMP.
    import os
    env = os.environ.copy()
    env["TMPDIR"] = str(tmp_path)
    env["TEMP"] = str(tmp_path)
    env["TMP"] = str(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        env=env, capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    assert "would delete" in proc.stdout
    # Both target dirs still exist.
    for d in targets:
        assert d.exists()
    assert decoy.exists()


def test_apply_deletes_only_matching(fake_bench_dirs, tmp_path):
    targets, decoy = fake_bench_dirs
    import os
    env = os.environ.copy()
    env["TMPDIR"] = str(tmp_path)
    env["TEMP"] = str(tmp_path)
    env["TMP"] = str(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--apply"],
        env=env, capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    # Targets gone, decoy still there.
    for d in targets:
        assert not d.exists(), f"{d} should have been deleted"
    assert decoy.exists(), "decoy must NOT have been deleted"
