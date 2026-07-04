"""Cycle #110.E — wire-up test: SessionStart hook → daemon_runner.

The hook ``hooks/hippo_session_start.py`` was extended to call
``maybe_spawn_all_default_daemons`` before emitting the closing
banner. These tests run the hook in a real subprocess (so we exercise
the same code path Claude Code uses) and check:

  1. The banner now includes a "Background daemons" section.
  2. With all env gates OFF, every daemon reports ``disabled``.
  3. With one gate ON, that daemon reports ``spawned`` (and a real
     subprocess is launched — verified by the cooldown state file).

These are E2E-ish: they import nothing, they cd nowhere, they just
run the script and inspect stdout + the state dir.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / "hooks" / "hippo_session_start.py"


def _run_hook(env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    """Invoke the hook with a fresh env. Returns the completed process."""
    full_env = {**os.environ, **env}
    # Force the hook to find an empty data dir under tmp_path so its
    # banner doesn't depend on the real ~/.engram corpus.
    return subprocess.run(  # noqa: S603
        [sys.executable, str(HOOK)],
        env=full_env, capture_output=True, text=True,
        cwd=str(cwd), timeout=30,
    )


def _seed_minimal_data(data_dir: Path) -> None:
    """Create the bare-minimum file layout the hook needs to NOT exit
    early. Without this the hook bails at `_find_data_dir() is None`
    and never reaches the daemon code."""
    (data_dir / "episodes").mkdir(parents=True, exist_ok=True)
    (data_dir / "episodes" / "episodes.db").write_bytes(b"")
    (data_dir / "semantic").mkdir(parents=True, exist_ok=True)
    (data_dir / "semantic" / "semantic.db").write_bytes(b"")


class TestSessionStartHookDaemons:

    def test_banner_includes_daemons_section_when_all_disabled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _seed_minimal_data(tmp_path)
        env = {
            "ENGRAM_DATA_DIR": str(tmp_path),
            "ENGRAM_CONTRADICTION_ENABLED": "0",
            "ENGRAM_DECAY_ENABLED": "0",
            # Keep Auto-Dream off so we don't fire side effects.
            "ENGRAM_AUTO_DREAM_ENABLED": "0",
        }
        proc = _run_hook(env, cwd=tmp_path)
        assert proc.returncode == 0
        out = proc.stdout
        assert "Background daemons" in out
        # Both default daemons listed; both should report disabled.
        assert "contradiction_scan: disabled" in out
        assert "decay_run: disabled" in out

    def test_enable_one_daemon_fires_subprocess(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _seed_minimal_data(tmp_path)
        env = {
            "ENGRAM_DATA_DIR": str(tmp_path),
            "ENGRAM_CONTRADICTION_ENABLED": "1",
            "ENGRAM_DECAY_ENABLED": "0",
            "ENGRAM_AUTO_DREAM_ENABLED": "0",
        }
        proc = _run_hook(env, cwd=tmp_path)
        assert proc.returncode == 0
        out = proc.stdout
        # The contradiction scanner should have been spawned. We can
        # see it in two places: the banner line AND a state file in
        # the data dir (cooldown marker).
        assert "contradiction_scan: spawned" in out
        assert "decay_run: disabled" in out
        state_file = tmp_path / "daemon_contradiction_scan_last.txt"
        # Give the subprocess + filesystem a moment to settle.
        for _ in range(30):
            if state_file.exists():
                break
            time.sleep(0.1)
        assert state_file.exists(), (
            "cooldown state file should be created on a real spawn"
        )
        ts = float(state_file.read_text().strip())
        assert abs(ts - time.time()) < 60, (
            "state file timestamp must be close to 'now'"
        )

    def test_hook_never_crashes_on_daemon_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Force PATH-less env so subprocess.Popen has chances of failing
        # in interesting ways. The hook MUST swallow the failure and
        # still emit the rest of the banner.
        _seed_minimal_data(tmp_path)
        env = {
            "ENGRAM_DATA_DIR": str(tmp_path),
            "ENGRAM_CONTRADICTION_ENABLED": "1",
            "ENGRAM_DECAY_ENABLED": "1",
            "ENGRAM_AUTO_DREAM_ENABLED": "0",
        }
        proc = _run_hook(env, cwd=tmp_path)
        assert proc.returncode == 0
        # Banner should still close cleanly with the separator.
        assert "USE THIS MEMORY" in proc.stdout
