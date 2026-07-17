"""Cycle #110.E (2026-05-16) — production spawn_callable.

`verimem.daemon_runner.maybe_spawn_daemon` takes an injected
`spawn_callable`. In production the SessionStart hook wires it to
`production_spawn` which fires a real *detached* subprocess so the
hook itself doesn't block on the child.

Design choices:

* Same Python interpreter (`sys.executable`) as the parent — avoids
  the "wrong-Python venv" surprise where a daemon imports a stale
  copy of verimem.
* All three std streams routed to ``DEVNULL`` so the child's logs
  don't appear in the SessionStart banner.
* Windows: ``subprocess.CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS``
  so a Ctrl-C in the parent doesn't kill the daemon.
* POSIX: ``start_new_session=True`` for the same reason.
* No PID file. Cooldown is the only state we persist (see
  ``daemon_runner._save_last_ts``). If a daemon crashes the next
  call (after cooldown) tries again — that's the entire recovery
  strategy.

We return a dict ``{"pid": <int>}`` so `daemon_runner` can fold
it into its structured-dict return.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_IS_WINDOWS = os.name == "nt"

# Repo root resolution (cycle 110.E counterexample fix, 2026-05-16).
# DEFAULT_DAEMONS.script_path is RELATIVE ("scripts/contradiction_scan.py").
# The SessionStart hook is invoked by Claude Code with cwd = user's
# workspace, NOT the HippoAgent repo. Without explicit anchoring the
# child would silently FileNotFoundError while the parent burns the
# cooldown. We anchor against this module's location (engram/ is
# always at <repo_root>/engram/, so ``parent.parent`` is canonical).
_REPO_ROOT = Path(__file__).resolve().parent.parent
# Windows-only constants — not present on POSIX; guard the import.
if _IS_WINDOWS:  # pragma: no cover - platform branch
    _CREATE_NEW_PROCESS_GROUP = getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200,
    )
    _DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
    # Cycle #136.A (2026-05-17): DETACHED_PROCESS alone doesn't suppress
    # the console window — a console-subsystem child (like `python.exe`)
    # gets a FRESH console allocated by Windows, which appears as a
    # flash CMD pop-up before the detached process exits. We must
    # additionally set CREATE_NO_WINDOW (0x08000000). The two flags
    # combine: detached process group (so Ctrl-C in parent doesn't
    # propagate) AND no console window allocated.
    #
    # Aurelio diagnosis 2026-05-17 sera: shell che si aprono e chiudono
    # da sole. Empirical evidence: ~/.engram/dreams/ has 18 auto-dream
    # dirs from 2026-05-16 to 2026-05-17 — every SessionStart hook spawn
    # was flashing a CMD window.
    _CREATE_NO_WINDOW = getattr(
        subprocess, "CREATE_NO_WINDOW", 0x08000000,
    )
    _DETACH_FLAGS = (
        _CREATE_NEW_PROCESS_GROUP | _DETACHED_PROCESS | _CREATE_NO_WINDOW
    )
else:
    _DETACH_FLAGS = 0


def _resolve_script(script_path: str) -> Path:
    """Resolve ``script_path`` to an absolute path.

    Absolute paths are used as-is. Relative paths anchor against
    ``_REPO_ROOT`` (the HippoAgent repo) rather than the parent's
    cwd — this is the cycle 110.E counterexample fix.
    """
    p = Path(script_path)
    if p.is_absolute():
        return p
    return (_REPO_ROOT / p).resolve()


def production_spawn(
    *, script_path: str, extra_args: list[str],
) -> dict[str, Any]:
    """Fire a detached subprocess; return ``{"pid", "resolved_script_path"}``.

    Args:
        script_path: filesystem path to the Python script to run.
            Relative paths are resolved against the HippoAgent repo
            root (the directory containing the ``engram/`` package).
            This is intentional: the SessionStart hook runs with an
            arbitrary cwd and a relative path interpreted as
            cwd-relative would silently FileNotFound at the child.
        extra_args: list of CLI args appended after the resolved path.

    Returns:
        ``{"pid": int, "resolved_script_path": str}`` on successful
        Popen.

    Raises:
        FileNotFoundError: if the resolved script does not exist.
            ``daemon_runner.maybe_spawn_daemon`` catches this and
            returns a ``reason="error"`` dict, leaving the cooldown
            UNBURNED so a fixed deploy can retry immediately.
    """
    resolved = _resolve_script(script_path)
    if not resolved.exists():
        raise FileNotFoundError(
            f"daemon script not found: {resolved} "
            f"(input was {script_path!r}, anchor={_REPO_ROOT})"
        )

    cmd = [sys.executable, str(resolved), *list(extra_args)]
    popen_kwargs: dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if _IS_WINDOWS:  # pragma: no cover - platform branch
        popen_kwargs["creationflags"] = _DETACH_FLAGS
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **popen_kwargs)  # noqa: S603
    return {"pid": int(proc.pid), "resolved_script_path": str(resolved)}


__all__ = ["production_spawn"]
