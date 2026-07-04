"""Cycle 169 (2026-05-20) — Claude Code hook entry points for HippoAgent.

Each submodule exposes a CLI-shaped ``main_stdin_stdout(stdin, stdout)``
that ``.claude/hooks/*.py`` wrapper scripts can call after delegating
the heavy import work into the engram package (testable from pytest
without subprocess).

Submodules:
  * :mod:`engram.hooks.pre_tool_use` — PreToolUse hook that consumes
    :class:`engram.proactive_step_injector.StepInjector` between tool
    calls. Closes the cycle-168 critic finding from PR #108.
"""
