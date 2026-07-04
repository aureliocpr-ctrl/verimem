"""HippoAgent PreToolUse hook — wrapper around engram.hooks.pre_tool_use.

Cycle 169 (2026-05-20). Closes the cycle-168 critic finding from
PR #108 ("StepInjector dead code = no MCP wrapper / no consumer") by
making :class:`engram.proactive_step_injector.StepInjector` reachable
from a real Claude Code consumer.

Wire-up
-------
Add to ``~/.claude/settings.json``::

    "hooks": {
      "PreToolUse": [
        {
          "matcher": "Bash|Edit|Write|Read|Grep|Glob|PowerShell",
          "hooks": [
            {
              "type": "command",
              "command": "pythonw \\"<repo>/.claude/hooks/hippo_pre_tool_use.py\\""
            }
          ]
        }
      ]
    }

Defensive guarantees (same contract as :mod:`hippo_post_tool_use`):
  * Silent on missing data dir → exit 0.
  * Silent on malformed stdin → exit 0.
  * Silent on embedding daemon offline → exit 0 (StepInjector internal).
  * NEVER blocks the tool call: exit code is always 0.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _ensure_engram_importable() -> None:
    """Make :mod:`engram` importable when this hook runs OUTSIDE the
    repo (e.g. installed copy in ``~/.claude/hooks/``). When the host
    has installed hippoagent via pip the import works directly; this
    fallback is for dev setups where the repo is on a sibling path.
    """
    try:
        import engram  # noqa: F401, PLC0415
        return
    except ImportError:
        pass
    # Locate the repo by walking up from this file.
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / "engram" / "__init__.py").exists():
            sys.path.insert(0, str(ancestor))
            return


def main() -> int:
    _ensure_engram_importable()
    try:
        from engram.hooks.pre_tool_use import main_stdin_stdout
    except ImportError:
        # engram not on path even after the heuristic — silent fail.
        return 0
    return main_stdin_stdout()


if __name__ == "__main__":  # pragma: no cover — invoked by Claude Code
    raise SystemExit(main())
