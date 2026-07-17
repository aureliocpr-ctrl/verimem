"""TDD — in STRICT mode (shell=False) il sandbox deve BLOCCARE l'arbitrary code
execution che il binary-allowlist "*" lasciava passare (rescan2 HIGH, 2026-06-02).

Scope DELIBERATO: solo il path STRICT (_validate_argv). Il legacy mode permette
`python -c` per dev-productivity (commento sandbox.py:256 "is an allowed pattern"
+ 6 test lo usano come cavia per env/timeout/output/cwd) -> NON lo tocco in
autonomia: cambiare quella policy e' una decisione per Aurelio. In strict
(production posture) invece l'exec arbitrario va chiuso.

Regola: python permesso SOLO via `-m pytest`; `-c` e l'esecuzione diretta di
file (`python foo.py`) sono arbitrary code execution. find blocca le azioni
-exec/-execdir/-delete/-ok/...
"""
from __future__ import annotations

from verimem.sandbox import _validate_argv


def test_strict_blocks_python_dash_c():
    ok, rule = _validate_argv(["python", "-c", "import os; os.system('x')"])
    assert not ok, rule


def test_strict_blocks_python3_dash_c():
    ok, _ = _validate_argv(["python3", "-c", "print(1)"])
    assert not ok


def test_strict_blocks_python_script():
    ok, _ = _validate_argv(["python", "evil.py"])
    assert not ok


def test_strict_allows_python_m_pytest():
    ok, rule = _validate_argv(["python", "-m", "pytest", "tests/"])
    assert ok, rule


def test_strict_blocks_find_exec():
    ok, _ = _validate_argv(["find", ".", "-name", "*.log", "-exec", "cat", "{}", ";"])
    assert not ok


def test_strict_blocks_find_delete():
    ok, _ = _validate_argv(["find", ".", "-delete"])
    assert not ok


def test_strict_allows_find_readonly():
    ok, rule = _validate_argv(["find", ".", "-name", "*.py"])
    assert ok, rule


def test_strict_allows_ls():
    ok, rule = _validate_argv(["ls", "-la"])
    assert ok, rule


# --- git config WRITE = persistence arbitrary-exec, even in strict mode ------
# (loop 2026-06-05) `config` is in the git allow-set, so `git config
# core.pager "sh -c evil"` is accepted; a later allowed `git log` then runs
# evil through the pager (same for core.editor / core.hooksPath / alias.*).
# The whole exec chain lives INSIDE the strict allowlist -> the secure mode's
# "injection impossible" contract is violated. Only READ forms (--get/--list)
# are safe. Legacy mode is the dev-productivity posture (Aurelio's policy) and
# is intentionally NOT touched here, mirroring the python/find scope above.

def test_strict_blocks_git_config_write_pager():
    # core.pager fires on the NEXT allowed `git log`/`git diff` -> exec.
    ok, rule = _validate_argv(["git", "config", "core.pager", "sh -c 'touch /tmp/pwn'"])
    assert not ok, rule


def test_strict_blocks_git_config_write_editor():
    ok, rule = _validate_argv(["git", "config", "core.editor", "evil"])
    assert not ok, rule


def test_strict_blocks_git_config_write_hookspath():
    ok, rule = _validate_argv(["git", "config", "core.hooksPath", "/tmp/evilhooks"])
    assert not ok, rule


def test_strict_blocks_git_config_bare():
    # `git config` with no read flag is a write/usage form -> deny (safe).
    ok, _ = _validate_argv(["git", "config"])
    assert not ok


def test_strict_allows_git_config_get():
    ok, rule = _validate_argv(["git", "config", "--get", "user.name"])
    assert ok, rule


def test_strict_allows_git_config_list():
    ok, rule = _validate_argv(["git", "config", "--list"])
    assert ok, rule


def test_strict_still_allows_git_status():
    # Regression guard: the git-config guard must not break other read-only
    # git subcommands that were already allowed.
    ok, rule = _validate_argv(["git", "status"])
    assert ok, rule
