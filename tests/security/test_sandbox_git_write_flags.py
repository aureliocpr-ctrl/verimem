"""Strict mode: git subcommands are allowlisted, their FLAGS were not (audit H3).

The strict allowlist matches `git <subcommand>` and then accepts everything that
follows. `git diff` is on the list, and git's `--output=<path>` writes the diff
to an arbitrary absolute path — so an allowlisted read-only-looking command was
arbitrary file write.

Note the cwd jail does NOT close this one: `--output=C:/temp/x` is absolute and
independent of the working directory. The jail limits how much of the CONTENT
an attacker controls (which repo the diff comes from); it does nothing about
where the bytes land. Two separate fixes.
"""
from __future__ import annotations

import pytest

from verimem.sandbox import SandboxedShell

# NOTE on the entry point: SandboxedShell has TWO validation paths.
# validate() consults the regex allowlist; execute() in strict mode parses argv
# and goes through _validate_argv. The MCP tool calls execute(), so that is the
# governing path and the one these tests must exercise — a first version of this
# file used validate() and would have "passed" against a fix it never reached.


@pytest.fixture()
def strict(monkeypatch, tmp_path):
    monkeypatch.setenv("ENGRAM_SANDBOX_MODE", "strict")
    return str(tmp_path)


@pytest.mark.parametrize("cmd", [
    "git diff --output=C:/temp/gitout.txt",
    "git diff --output C:/temp/gitout.txt",
    "git log --output=/tmp/gitout.txt",
    "git show --output=/tmp/gitout.txt",
])
def test_git_output_flag_is_denied(cmd, strict):
    r = SandboxedShell().execute(cmd, strict, dry_run=True)
    assert r.action == "deny", f"arbitrary file write via git flag: {cmd} -> {r}"


@pytest.mark.parametrize("cmd", [
    "git status",
    "git log --oneline -5",
    "git diff HEAD~1",
    "git show --stat",
])
def test_plain_read_only_git_still_allowed(cmd, strict):
    """Narrowness: the block must not break ordinary read-only git."""
    r = SandboxedShell().execute(cmd, strict, dry_run=True)
    assert r.action != "deny", f"legitimate git broken: {cmd} -> {r}"
