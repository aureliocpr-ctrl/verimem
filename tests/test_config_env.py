"""FORGIA pezzo #29 — HIPPO_DATA_DIR env override for CONFIG paths.

Until now `CONFIG.data_dir` was hard-coded to `<project_root>/data`. That
made test isolation impossible without per-test path injection (every
EpisodicMemory call was passing `db_path=` explicitly to bypass) and
multi-tenant deploys had to symlink. Pezzo #29 makes `HIPPO_DATA_DIR` a
first-class env var: when set, the entire data tree (episodes, skills,
semantic, runs, reports) is rooted there.

We test the resolver function `_data_root()` directly rather than
reloading the config module — module reload would invalidate every
other module's `from .config import CONFIG` snapshot and pollute
unrelated tests.

Three invariants:

  1. NO ENV → DEFAULT — without `HIPPO_DATA_DIR`, `_data_root()`
     returns `<project>/data` exactly as before.

  2. ENV SET → OVERRIDE — with `HIPPO_DATA_DIR=/tmp/foo`,
     `_data_root()` returns `/tmp/foo` resolved.

  3. EXPANDUSER + RESOLVE — paths are normalised to absolute paths.

  4. CONFIG WIRING — every derived field of the live `CONFIG` instance
     uses `_data_root()` and is consistent with `data_dir`.
"""
from __future__ import annotations

from pathlib import Path

from verimem.config import CONFIG, _data_root, _project_root


def test_no_env_falls_back_to_home_engram(monkeypatch):
    # A6 (2026-06-08): the no-env default is now ~/.engram (via
    # _compat.data_dir), NOT <project>/data — the old default wrote the entire
    # memory tree into site-packages on a non-editable install and disagreed
    # with the dashboard/auth resolver. Must agree with _compat by construction.
    monkeypatch.delenv("HIPPO_DATA_DIR", raising=False)
    monkeypatch.delenv("ENGRAM_DATA_DIR", raising=False)
    from verimem._compat import data_dir as compat_data_dir
    root = _data_root()
    assert root == compat_data_dir()
    assert root != _project_root() / "data"


def test_env_set_overrides_data_root(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_DATA_DIR", raising=False)  # isolate HIPPO_DATA_DIR path
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    root = _data_root()
    assert root == tmp_path
    assert root.is_absolute()


def test_env_value_is_resolved_absolute(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_DATA_DIR", raising=False)  # isolate HIPPO_DATA_DIR path
    relish = tmp_path / "rel"
    monkeypatch.setenv("HIPPO_DATA_DIR", str(relish))
    root = _data_root()
    assert root.is_absolute()
    assert root == relish.resolve()


def test_env_value_expanduser(monkeypatch):
    """`~` in the env value must expand to the user's home."""
    monkeypatch.delenv("ENGRAM_DATA_DIR", raising=False)  # isolate HIPPO_DATA_DIR path
    monkeypatch.setenv("HIPPO_DATA_DIR", "~/.hippoagent_test_xyz")
    root = _data_root()
    assert "~" not in str(root)
    assert root.is_absolute()


def test_config_wires_every_path_under_data_dir():
    """The live CONFIG: every derived path lives under `data_dir`."""
    derived: list[Path] = [
        CONFIG.episodes_db,
        CONFIG.skills_dir,
        CONFIG.skills_db,
        CONFIG.semantic_db,
        CONFIG.runs_dir,
        CONFIG.reports_dir,
    ]
    for p in derived:
        # Use os.path.commonpath to be platform-agnostic.
        try:
            p.relative_to(CONFIG.data_dir)
        except ValueError:
            raise AssertionError(
                f"{p} is not under CONFIG.data_dir={CONFIG.data_dir}"
            ) from None
