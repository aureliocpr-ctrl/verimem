"""P0-5 (audit 2026-06-07): `mcp` must be a CORE dependency.

mcp_server.py imports `mcp` unconditionally at module top, and the README's
primary install is plain `pip install git+...` (core only) + `engram mcp`.
With `mcp` only in the [mcp-only]/[full] extras, a fresh install crashes with
ModuleNotFoundError on the very first command Claude Code runs — product dead
on arrival. This guard keeps mcp in core.
"""
from __future__ import annotations

import pathlib

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # tomllib is 3.11+
    tomllib = None

_PYPROJECT = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"


@pytest.mark.skipif(tomllib is None, reason="tomllib requires Python 3.11+")
def test_mcp_is_a_core_dependency():
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    core = data["project"]["dependencies"]
    names = {d.replace("[", " ").split(">=")[0].split("==")[0].split("[")[0].strip().lower() for d in core}
    assert "mcp" in names, (
        "`mcp` must be in [project.dependencies] (core), not only in extras — "
        "mcp_server.py imports it unconditionally and `engram mcp` is the headline "
        "command (audit P0-5)."
    )
