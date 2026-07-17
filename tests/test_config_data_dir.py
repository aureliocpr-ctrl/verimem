"""Audit 2026-06-08 A6: with no *_DATA_DIR env, config._data_root() defaulted to
``<project>/data`` — which on a non-editable ``pip install`` lives INSIDE
site-packages (wiped on upgrade, often read-only) and disagrees with the
``~/.engram`` path the dashboard/auth resolver (``_compat.data_dir``) uses: a
silent split-brain / data-loss on the canonical first-run path. Fix: fall back
to ``_compat.data_dir()`` (``~/.engram``) when no env is set, and honor
ENGRAM_DATA_DIR (the name the README .mcp.json uses) in addition to HIPPO_DATA_DIR.
"""
from __future__ import annotations

from pathlib import Path

import engram._compat as _compat
from engram._compat import data_dir as compat_data_dir
from engram.config import _data_root, _project_root


def _fake_home(monkeypatch, home):
    monkeypatch.setattr(Path, "home", lambda: home)
    for _v in ("VERIMEM_DATA_DIR", "ENGRAM_DATA_DIR", "HIPPO_DATA_DIR"):
        monkeypatch.delenv(_v, raising=False)


def test_data_dir_prefers_verimem_then_legacy_engram(monkeypatch, tmp_path):
    """Total rename 0.6.0: ~/.verimem is canonical, but an existing ~/.engram is
    still read (never stranded)."""
    _fake_home(monkeypatch, tmp_path)
    (tmp_path / ".engram").mkdir()
    assert _compat.data_dir() == tmp_path / ".engram"      # legacy read as-is
    (tmp_path / ".verimem").mkdir()
    assert _compat.data_dir() == tmp_path / ".verimem"     # canonical wins


def test_data_dir_never_migrates_existing_engram(monkeypatch, tmp_path):
    """A machine with only ~/.engram (possibly many GB) keeps using it — the
    rename must NOT create ~/.verimem and strand the existing store."""
    _fake_home(monkeypatch, tmp_path)
    (tmp_path / ".engram").mkdir()
    assert _compat.data_dir() == tmp_path / ".engram"
    assert not (tmp_path / ".verimem").exists()


def test_data_dir_fresh_install_creates_verimem(monkeypatch, tmp_path):
    _fake_home(monkeypatch, tmp_path)
    got = _compat.data_dir()
    assert got == tmp_path / ".verimem" and got.exists()


def test_verimem_data_dir_env_overrides(monkeypatch, tmp_path):
    for _v in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR"):
        monkeypatch.delenv(_v, raising=False)
    target = tmp_path / "explicit"
    monkeypatch.setenv("VERIMEM_DATA_DIR", str(target))
    assert _compat.data_dir() == target


def test_data_root_agrees_with_compat_when_no_env(monkeypatch) -> None:
    monkeypatch.delenv("ENGRAM_DATA_DIR", raising=False)
    monkeypatch.delenv("HIPPO_DATA_DIR", raising=False)
    assert _data_root() == compat_data_dir(), "config + compat data-dir disagree (split-brain)"


def test_data_root_not_inside_installed_package_when_no_env(monkeypatch) -> None:
    monkeypatch.delenv("ENGRAM_DATA_DIR", raising=False)
    monkeypatch.delenv("HIPPO_DATA_DIR", raising=False)
    # the old buggy default wrote the whole memory tree into the package dir
    assert _data_root() != _project_root() / "data"


def test_engram_data_dir_env_is_honored(monkeypatch, tmp_path) -> None:
    # README .mcp.json sets ENGRAM_DATA_DIR; config only read HIPPO_DATA_DIR before.
    monkeypatch.delenv("HIPPO_DATA_DIR", raising=False)
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path / "custom"))
    assert _data_root() == (tmp_path / "custom").resolve()
