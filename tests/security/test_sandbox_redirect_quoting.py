"""Redirect denylist vs QUOTED targets (external red-team audit, CRITICAL-1).

The legacy-mode denylist that blocks file redirects was
``>>?\\s*[A-Za-z0-9/_.~$-]`` — a character class that does NOT contain a quote.
So the guard fired on `echo pwn > C:/tmp/x` and stayed silent on
`echo pwn > "C:/tmp/x"`. With `echo` on the allowlist and shell=True on Windows,
cmd.exe honours the quoting: arbitrary file write with fully attacker-chosen
content (settings.json, hooks, CLAUDE.md, any tool config).

Reproduced before fixing: the quoted form returned allowed=True via
`allow:^\\s*echo\\s+[^\\r\\n]*$`, the unquoted one allowed=False via the
denylist — proving the quote, not the payload, was what slipped through.

Severity in context: sandbox_exec is gated behind HIPPO_ENABLE_SHELL=1 and is
OFF by default, so a stock install never exposes this. It matters for anyone who
turns the shell surface on.
"""
from __future__ import annotations

import os

import pytest

from verimem.sandbox import SandboxedShell


@pytest.fixture(autouse=True)
def _legacy_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("ENGRAM_SANDBOX_MODE", "legacy")
    return str(tmp_path)


@pytest.mark.parametrize("cmd", [
    'echo pwned>"C:/temp/x.txt"',
    'echo pwn > "C:/temp/x.txt"',
    "echo pwn > 'C:/temp/x.txt'",
    'echo pwn >> "C:/temp/x.txt"',
    'echo pwn>"\\\\server\\share\\x.txt"',
])
def test_quoted_redirect_is_denied(cmd, _legacy_mode):
    v = SandboxedShell().validate(cmd, _legacy_mode)
    assert not v.allowed, f"quoting slipped the redirect guard: {cmd} -> {v}"


def test_unquoted_redirect_still_denied(_legacy_mode):
    v = SandboxedShell().validate("echo pwn > C:/temp/x.txt", _legacy_mode)
    assert not v.allowed


def test_plain_echo_still_allowed(_legacy_mode):
    """Narrowness: the guard must not break echo without a redirect."""
    v = SandboxedShell().validate("echo hello world", _legacy_mode)
    assert v.allowed


def test_sandbox_exec_is_off_by_default():
    """The severity modifier, pinned: the shell surface is opt-in."""
    from verimem.mcp_server import _shell_perm_enabled
    old = os.environ.pop("HIPPO_ENABLE_SHELL", None)
    try:
        assert _shell_perm_enabled() is False
    finally:
        if old is not None:
            os.environ["HIPPO_ENABLE_SHELL"] = old
