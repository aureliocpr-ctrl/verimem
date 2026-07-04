"""Audit 3-round R2 #11 (packaging): the core runtime deps jsonschema + mcp must
stay in [project.dependencies], NOT be demoted to an optional extra.

A wheel built with them as extras crashes on a fresh install (engram.mcp_server
imports both at module load). The R2 finding observed a stale dist/ 0.3.0 wheel
with exactly that defect — but dist/ is gitignored (a local build artifact, not
published) and pyproject.toml is already correct. The stale wheel was removed;
this test locks the source so the regression can't return.
"""
from __future__ import annotations

import re
from pathlib import Path


def _core_dependencies_block() -> str:
    pp = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pp.read_text(encoding="utf-8")
    # stop at the closing bracket on its OWN line (optionally indented), so the
    # ']' inside "uvicorn[standard]" doesn't truncate the block early.
    m = re.search(r"(?ms)^dependencies\s*=\s*\[(.*?)\n\s*\]", text)
    assert m is not None, "pyproject [project].dependencies block not found"
    return m.group(1)


def test_jsonschema_is_a_core_dependency():
    block = _core_dependencies_block()
    assert re.search(r'"jsonschema\b', block), (
        "jsonschema must be a CORE dependency — mcp_server._validate_input imports "
        "it at module load, so a wheel without it crashes on import"
    )


def test_mcp_is_a_core_dependency_not_extra():
    block = _core_dependencies_block()
    assert re.search(r'"mcp\b', block), (
        "mcp must be a CORE dependency, not demoted to an optional extra"
    )
