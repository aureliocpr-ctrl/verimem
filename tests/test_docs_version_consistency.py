"""Version-consistency guard (2026-07-13).

An external agent reported verimem as "stuck at 0.3.0" because docs hardcoded a
now-stale current version. Root fix was to make SECURITY.md version-agnostic and
bump the snapshots; this locks the class so it cannot silently recur:

  * code and packaging must agree on ONE version (drift between verimem.__version__
    and pyproject is itself a real release bug);
  * SECURITY.md must not pin a "currently X.Y" string that goes stale;
  * STATE.md's Release row, if present, must match the true version.

Historical version mentions (CHANGELOG entries, "0.3.x and earlier remain MIT")
are correct and intentionally NOT policed here.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # tomllib is 3.11+
    tomllib = None

import verimem

_ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    d = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return d["project"]["version"]


@pytest.mark.skipif(tomllib is None, reason="tomllib requires Python 3.11+")
def test_code_and_packaging_version_agree():
    """The single-source-of-truth check: a mismatch is a release bug."""
    assert verimem.__version__ == _pyproject_version(), (
        f"verimem.__version__={verimem.__version__} but "
        f"pyproject version={_pyproject_version()}")


def test_security_md_is_version_agnostic():
    """The durable fix: SECURITY.md must not hardcode a 'currently X.Y' that rots.
    Point at PyPI / the badge instead."""
    txt = (_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    m = re.search(r"current(?:ly)?[^\n]*?`?v?(\d+\.\d+(?:\.\d+)?)", txt, re.I)
    assert not m, (
        f"SECURITY.md hardcodes a current version ({m.group(1)}) — keep it "
        "version-agnostic so it can't go stale again")


@pytest.mark.skipif(tomllib is None, reason="tomllib requires Python 3.11+")
def test_state_md_release_row_matches_true_version():
    v = _pyproject_version()
    txt = (_ROOT / "STATE.md").read_text(encoding="utf-8")
    m = re.search(r"\|\s*Release\s*\|\s*v?(\d+\.\d+\.\d+)", txt)
    assert m is None or m.group(1) == v, (
        f"STATE.md Release row says {m.group(1)}, true version is {v}")
