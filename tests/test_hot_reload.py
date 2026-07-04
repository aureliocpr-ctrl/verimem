"""Cycle 2026-05-27 round 13 P2a — hot-reload watcher pytest.

Tests the polling half (collect_pending_changes + diff_snapshots).
The live watchdog observer half is exercised in passing via start/stop
no-op if the lib isn't installed (degraded mode).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engram.hot_reload import (
    HotReloadWatcher,
    collect_pending_changes,
    diff_snapshots,
)


@pytest.fixture
def py_root(tmp_path: Path) -> Path:
    """A temp dir with 3 .py files seeded."""
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.py").write_text("y = 2\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.py").write_text("z = 3\n")
    return tmp_path


class TestDiffSnapshots:
    def test_no_changes_returns_empty(self):
        snap = {"a": "h1", "b": "h2"}
        assert diff_snapshots(snap, dict(snap)) == []

    def test_added_file_detected(self):
        before = {"a": "h1"}
        after = {"a": "h1", "b": "h2"}
        changes = diff_snapshots(before, after)
        assert len(changes) == 1
        assert changes[0].path == Path("b")
        assert changes[0].new_hash == "h2"

    def test_modified_file_detected(self):
        before = {"a": "h1"}
        after = {"a": "h_new"}
        changes = diff_snapshots(before, after)
        assert len(changes) == 1
        assert changes[0].new_hash == "h_new"

    def test_deleted_file_detected(self):
        before = {"a": "h1", "b": "h2"}
        after = {"a": "h1"}
        changes = diff_snapshots(before, after)
        assert len(changes) == 1
        assert changes[0].path == Path("b")
        assert changes[0].new_hash == ""


class TestCollectPendingChanges:
    def test_first_call_establishes_baseline(
        self, py_root: Path, tmp_path: Path,
    ):
        state = tmp_path / "state.json"
        changes = collect_pending_changes([py_root], state_file=state)
        # First call: every file is "new" vs empty baseline.
        assert len(changes) == 3
        assert state.exists()

    def test_second_call_detects_only_changes(
        self, py_root: Path, tmp_path: Path,
    ):
        state = tmp_path / "state.json"
        # Establish baseline.
        collect_pending_changes([py_root], state_file=state)
        # Modify one file.
        (py_root / "a.py").write_text("x = 999\n")
        # Add new file.
        (py_root / "new.py").write_text("hello\n")
        changes = collect_pending_changes([py_root], state_file=state)
        paths = {c.path.name for c in changes}
        assert "a.py" in paths
        assert "new.py" in paths
        assert "b.py" not in paths

    def test_skips_pycache(self, py_root: Path, tmp_path: Path):
        # Create a __pycache__ dir with a .py file — should be ignored.
        pcache = py_root / "__pycache__"
        pcache.mkdir()
        (pcache / "ignored.py").write_text("noise\n")
        state = tmp_path / "state.json"
        changes = collect_pending_changes([py_root], state_file=state)
        names = {c.path.name for c in changes}
        assert "ignored.py" not in names


class TestHotReloadWatcher:
    def test_watcher_constructs(self, py_root: Path):
        w = HotReloadWatcher(roots=[py_root])
        assert w.pending == []
        # start/stop should be no-op safe even without watchdog installed.
        w.start()
        w.stop()

    def test_drain_pending_clears(self, py_root: Path):
        w = HotReloadWatcher(roots=[py_root])
        import time as _t

        from engram.hot_reload import FileChange
        w.pending.append(FileChange(path=py_root / "fake.py",
                                     new_hash="abc",
                                     detected_at=_t.time()))
        drained = w.drain_pending()
        assert len(drained) == 1
        assert w.pending == []
