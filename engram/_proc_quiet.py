"""Cycle #136 (2026-05-17) — Windows console pop-up suppression helper.

Aurelio direttiva 2026-05-17: "shell che si aprono e chiudono da sole,
sono fastidiosissime". Root cause: every ``subprocess.run / Popen`` call
in ``engram/`` that doesn't pass ``creationflags=CREATE_NO_WINDOW``
flashes a Windows CMD window on the user's screen. This module exposes
one tiny helper, ``quiet_popen_kwargs()``, that returns the right
kwargs for the current platform — empty dict on Linux/macOS so the
helper is a no-op cross-platform.

Usage::

    from engram._proc_quiet import quiet_popen_kwargs
    subprocess.run(["git", "rev-parse", sha], **quiet_popen_kwargs())

The Windows ``CREATE_NO_WINDOW`` constant is only defined when running
on Windows (it lives in ``subprocess`` only on win32 Python builds).
We guard the attribute access defensively.
"""
from __future__ import annotations

import subprocess
import sys
from typing import Any


def quiet_popen_kwargs() -> dict[str, Any]:
    """Return kwargs that suppress the Windows console pop-up.

    On Windows this is ``{"creationflags": subprocess.CREATE_NO_WINDOW}``;
    on every other platform it is the empty dict (no behaviour change).
    """
    if sys.platform == "win32":
        flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if flag:
            return {"creationflags": flag}
    return {}
