"""Backward-compat bridge for the cycle #41 rename (hippoagent → engram).

Two surfaces are bridged here so existing user configurations keep working:

1. **Environment variables**: every ``HIPPO_*`` env var visible at process
   start is mirrored to ``ENGRAM_*`` (and vice versa) via
   :func:`init_env_aliases`. Existing ``HIPPO_HOSTED=1``, ``HIPPO_DATA_DIR``,
   ``HIPPO_AUTH_TOKEN``, etc. continue to work without code changes; new
   ``ENGRAM_*`` names are picked up by older code paths through the same
   mirror. The mirror uses :py:meth:`os.environ.setdefault` so an explicit
   value on one side never overrides an explicit value on the other.

2. **User data directory**: :func:`data_dir` returns ``~/.engram`` if it
   exists, falls back to ``~/.hippoagent`` if only the old dir exists,
   otherwise creates ``~/.engram``. This keeps existing installations
   reading their data while new installations get the new path.

The module is intentionally tiny and stdlib-only — it's imported by
``engram/__init__.py`` and must not have any heavy dependencies.

Scheduled removal: ~2026-08-13 (3 months from rename). After that, all
code is expected to use ``ENGRAM_*`` env names and the ``~/.engram``
path; this module can be deleted and ``HIPPO_*`` configs will start
failing — by then any user still on the old names has had 3 months
of clear deprecation warnings to migrate.
"""
from __future__ import annotations

import os
from pathlib import Path

_PREFIX_OLD = "HIPPO_"
_PREFIX_NEW = "ENGRAM_"

# Old data dir (cycle #1 — #40).
_OLD_DIR_NAME = ".hippoagent"
# New data dir (cycle #41+).
_NEW_DIR_NAME = ".engram"


def init_env_aliases() -> int:
    """Mirror HIPPO_* ↔ ENGRAM_* env vars (idempotent).

    For each environment variable starting with ``HIPPO_``, set the
    corresponding ``ENGRAM_`` variant if not already defined. Same in
    reverse for ``ENGRAM_*`` → ``HIPPO_*``. Uses :py:meth:`os.environ.setdefault`
    so explicit user values are never clobbered.

    Returns the number of mirror entries added (for tests / introspection).
    """
    added = 0
    # Snapshot keys to avoid mutation-during-iteration warnings.
    snapshot = list(os.environ.items())
    for k, v in snapshot:
        if k.startswith(_PREFIX_OLD):
            new_key = _PREFIX_NEW + k[len(_PREFIX_OLD):]
            if new_key not in os.environ:
                os.environ[new_key] = v
                added += 1
        elif k.startswith(_PREFIX_NEW):
            old_key = _PREFIX_OLD + k[len(_PREFIX_NEW):]
            if old_key not in os.environ:
                os.environ[old_key] = v
                added += 1
    return added


def data_dir() -> Path:
    """Return the canonical Engram data directory.

    Order of preference:

    1. If ``~/.engram`` exists, use it.
    2. Else if ``~/.hippoagent`` exists, use it (legacy install).
    3. Else create ``~/.engram`` and use it.

    Never throws — best-effort. Callers should still handle :py:class:`OSError`
    on subsequent disk operations.

    The env var ``HIPPO_DATA_DIR`` / ``ENGRAM_DATA_DIR`` (whichever is set;
    if both, the new name wins) overrides this default entirely.
    """
    # Explicit override via env (HIPPO_DATA_DIR or ENGRAM_DATA_DIR).
    override = os.environ.get("ENGRAM_DATA_DIR") or os.environ.get("HIPPO_DATA_DIR")
    if override:
        p = Path(override).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    home = Path.home()
    new_dir = home / _NEW_DIR_NAME
    old_dir = home / _OLD_DIR_NAME

    if new_dir.exists():
        return new_dir
    if old_dir.exists():
        return old_dir
    new_dir.mkdir(parents=True, exist_ok=True)
    return new_dir
