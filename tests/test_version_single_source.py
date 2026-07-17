"""Audit#2 2026-06-08 C-4: three version strings disagreed —
verimem.__version__ = 0.2.0, pyproject [project].version = 0.3.0 (== git tag
v0.3.0, the build truth), .claude-plugin/plugin.json = 0.4.0. Worse, the
plugin's own pip requirement was `hippoagent>=0.4.0`, a version the package
never produced — so a plugin install would resolve to nothing. Pin all of them
to the pyproject version and keep this test as the anti-drift gate.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import verimem

_ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    # Regex parse (NOT tomllib): tomllib is py3.11+ but the project supports
    # py3.10 (requires-python >=3.10) — importing tomllib broke py3.10 CI.
    # The [project] table's `version = "X.Y.Z"` is the canonical line.
    text = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    assert m, "could not find `version = \"...\"` in pyproject.toml"
    return m.group(1)


def _vt(s: str) -> tuple[int, ...]:
    return tuple(int(x) for x in s.split("."))


def test_version_strings_do_not_drift():
    pv = _pyproject_version()
    assert verimem.__version__ == pv, (
        f"verimem.__version__={verimem.__version__!r} != pyproject {pv!r}"
    )
    manifest = json.loads(
        (_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == pv, (
        f"plugin.json version={manifest['version']!r} != pyproject {pv!r}"
    )


def test_plugin_pip_requirement_is_satisfiable():
    pv = _pyproject_version()
    manifest = json.loads(
        (_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    pin = next(
        (r for r in manifest["requirements"]["pip"] if r.startswith("verimem")),
        "",
    )
    m = re.search(r">=\s*([\d.]+)", pin)
    assert m, f"no version floor found in plugin pip requirement: {pin!r}"
    assert _vt(m.group(1)) <= _vt(pv), (
        f"plugin requires verimem{pin} but the package builds as {pv} "
        "(unsatisfiable — install resolves to nothing)"
    )
