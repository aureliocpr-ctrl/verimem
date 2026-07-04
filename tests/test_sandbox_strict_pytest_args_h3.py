"""H3 (2026-07-04 security sweep): strict-mode `python -m pytest` must reject
code-loading pytest flags.

`python -m pytest` was allow-listed in strict mode, but its trailing args were
unvalidated — `-p mod`/`--pyargs` import a module, `--import-mode importlib`
runs a planted conftest, `-c`/`-o addopts=` point at an attacker config that
executes code at collection. Strict mode's contract is "injection impossible",
so those flags must be blocked. (The `git config` write vector the sweep also
named was already closed in 2026-06-05 — covered by the existing suite.)
"""
from __future__ import annotations

import pytest

from engram.sandbox import _validate_argv


@pytest.mark.parametrize("argv", [
    ["python", "-m", "pytest", "-p", "evil_plugin"],
    ["python", "-m", "pytest", "--pyargs", "evil_module"],
    ["python", "-m", "pytest", "--import-mode", "importlib"],
    ["python", "-m", "pytest", "--import-mode=importlib"],
    ["python", "-m", "pytest", "-c", "/tmp/evil.ini"],
    ["python", "-m", "pytest", "-o", "addopts=-p evil"],
    ["python", "-m", "pytest", "--override-ini", "addopts=-p evil"],
    ["python", "-m", "pytest", "--confcutdir", "/etc"],
])
def test_dangerous_pytest_flags_blocked_in_strict(argv):
    ok, reason = _validate_argv(argv)
    assert ok is False
    assert "strict mode" in reason


@pytest.mark.parametrize("argv", [
    ["python", "-m", "pytest"],
    ["python", "-m", "pytest", "tests/test_x.py"],
    ["python", "-m", "pytest", "-q", "-x"],
    ["python", "-m", "pytest", "tests/", "-k", "smoke"],
])
def test_benign_pytest_invocations_still_allowed(argv):
    ok, reason = _validate_argv(argv)
    assert ok is True
    assert "pytest" in reason
