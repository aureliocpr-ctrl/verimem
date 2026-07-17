"""Backward-compat bridge for the cycle #41 rename (hippoagent → engram)
plus the product-brand env prefix (Verimem, 2026-07-15).

Two surfaces are bridged here so existing user configurations keep working:

1. **Environment variables**: every ``HIPPO_*`` env var visible at process
   start is mirrored to ``ENGRAM_*`` (and vice versa) via
   :func:`init_env_aliases`. Existing ``HIPPO_HOSTED=1``, ``HIPPO_DATA_DIR``,
   ``HIPPO_AUTH_TOKEN``, etc. continue to work without code changes; new
   ``ENGRAM_*`` names are picked up by older code paths through the same
   mirror. The mirror uses :py:meth:`os.environ.setdefault` so an explicit
   value on one side never overrides an explicit value on the other.

   The same mirror covers ``VERIMEM_*`` — the PRODUCT prefix (PyPI name is
   ``verimem``; ``engram`` is the architecture package): ``VERIMEM_X`` is
   seen by every reader of ``ENGRAM_X`` / ``HIPPO_X`` without touching any
   call-site, and ``ENGRAM_X`` is mirrored back to ``VERIMEM_X`` for
   introspection. Unlike ``HIPPO_*`` this prefix is NOT scheduled for
   removal — it is the brand-forward name.

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
_PREFIX_BRAND = "VERIMEM_"

# Old data dir (cycle #1 — #40).
_OLD_DIR_NAME = ".hippoagent"
# New data dir (cycle #41+).
_NEW_DIR_NAME = ".engram"
# Canonical data dir since the total rename (0.6.0). Existing ~/.engram (and the
# older ~/.hippoagent) are still READ and NEVER migrated — a machine with a large
# ~/.engram store keeps using it untouched; only fresh installs create ~/.verimem.
_VERIMEM_DIR_NAME = ".verimem"


def init_env_aliases() -> int:
    """Mirror VERIMEM_* / HIPPO_* ↔ ENGRAM_* env vars (idempotent).

    Three passes, all :py:meth:`os.environ.setdefault`-semantics (an explicit
    value on one side never overrides an explicit value on the other):

    1. ``VERIMEM_X`` → ``ENGRAM_X`` (brand prefix feeds the canonical readers)
    2. ``HIPPO_X`` ↔ ``ENGRAM_X``  (legacy mirror, unchanged — running it
       after pass 1 makes the brand value transitively visible as ``HIPPO_X``)
    3. ``ENGRAM_X`` → ``VERIMEM_X`` (symmetry, for introspection)

    Returns the number of mirror entries added (for tests / introspection).
    """
    added = 0

    def _mirror(src_prefix: str, dst_prefix: str) -> int:
        n = 0
        # Snapshot keys to avoid mutation-during-iteration warnings.
        for k, v in list(os.environ.items()):
            if k.startswith(src_prefix):
                dst = dst_prefix + k[len(src_prefix):]
                if dst not in os.environ:
                    os.environ[dst] = v
                    n += 1
        return n

    added += _mirror(_PREFIX_BRAND, _PREFIX_NEW)   # VERIMEM_ → ENGRAM_
    added += _mirror(_PREFIX_OLD, _PREFIX_NEW)     # HIPPO_   → ENGRAM_
    added += _mirror(_PREFIX_NEW, _PREFIX_OLD)     # ENGRAM_  → HIPPO_
    added += _mirror(_PREFIX_NEW, _PREFIX_BRAND)   # ENGRAM_  → VERIMEM_
    return added


def data_dir() -> Path:
    """Return the canonical Verimem data directory.

    Order of preference (total rename 0.6.0):

    1. If ``~/.verimem`` exists, use it (canonical).
    2. Else if ``~/.engram`` exists, use it (legacy — NEVER migrated).
    3. Else if ``~/.hippoagent`` exists, use it (older legacy install).
    4. Else create ``~/.verimem`` and use it.

    A machine with an existing ``~/.engram`` store keeps reading it untouched:
    the rename never moves user data (a ~/.engram store can be many GB). Only a
    fresh install with no prior dir gets the new ``~/.verimem`` default.

    Never throws — best-effort. Callers should still handle :py:class:`OSError`
    on subsequent disk operations.

    Env override (highest precedence, in order): ``VERIMEM_DATA_DIR`` /
    ``ENGRAM_DATA_DIR`` / ``HIPPO_DATA_DIR`` — the first set wins entirely.
    """
    # Explicit override via env (VERIMEM_DATA_DIR / ENGRAM_DATA_DIR / HIPPO_DATA_DIR).
    override = (os.environ.get("VERIMEM_DATA_DIR")
                or os.environ.get("ENGRAM_DATA_DIR")
                or os.environ.get("HIPPO_DATA_DIR"))
    if override:
        p = Path(override).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    home = Path.home()
    verimem_dir = home / _VERIMEM_DIR_NAME
    engram_dir = home / _NEW_DIR_NAME
    hippo_dir = home / _OLD_DIR_NAME

    if verimem_dir.exists():
        return verimem_dir
    if engram_dir.exists():
        return engram_dir      # legacy store — read as-is, never migrated
    if hippo_dir.exists():
        return hippo_dir
    verimem_dir.mkdir(parents=True, exist_ok=True)
    return verimem_dir
