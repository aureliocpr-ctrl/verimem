"""TDD — Auto-Dream shadow retention.

The worker snapshots the FULL live DB into ``dreams/auto-<ts>/`` on every
firing and never pruned them → observed 2026-06-01: 346 stale shadow dirs
= ~7.9 GB on disk. ``_prune_old_dreams`` keeps only the ``keep`` most-recent
``auto-*`` dirs (default 3, env ``ENGRAM_DREAM_KEEP``), deletes older ones,
and NEVER touches non-``auto-`` dirs (manual dreams) or the live DB.
"""
from __future__ import annotations

import os
from pathlib import Path

from verimem.auto_dream_worker import _prune_old_dreams


def _mk(d: Path, mtime: float) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / "semantic.db").write_text("x", encoding="utf-8")
    os.utime(d, (mtime, mtime))


def test_prune_keeps_last_n(tmp_path):
    dreams = tmp_path / "dreams"
    for i in range(6):
        _mk(dreams / f"auto-{1000 + i}", mtime=1000.0 + i)
    res = _prune_old_dreams(tmp_path, keep=3)
    remaining = sorted(d.name for d in dreams.iterdir() if d.is_dir())
    assert res["pruned"] == 3
    assert remaining == ["auto-1003", "auto-1004", "auto-1005"]  # newest 3 kept


def test_prune_never_touches_non_auto(tmp_path):
    dreams = tmp_path / "dreams"
    for i in range(4):
        _mk(dreams / f"auto-{i + 1}", mtime=float(i + 1))
    _mk(dreams / "dream_manual", mtime=0.5)  # non-auto → must survive
    _prune_old_dreams(tmp_path, keep=1)
    names = sorted(d.name for d in dreams.iterdir() if d.is_dir())
    assert "dream_manual" in names      # manual dream untouched
    assert "auto-4" in names            # newest auto kept
    assert "auto-1" not in names        # oldest pruned


def test_prune_no_dreams_dir_is_safe(tmp_path):
    assert _prune_old_dreams(tmp_path, keep=3) == {"pruned": 0, "kept": 0}
