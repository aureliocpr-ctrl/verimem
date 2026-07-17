"""Deprecated alias for the `verimem` package (formerly `hippoagent`).

The package was renamed from ``hippoagent`` to ``verimem`` in v0.3.0
(cycle #41, 2026-05-13). This shim provides backward-compat for existing
imports of the form::

    import hippoagent
    from hippoagent import something
    from hippoagent.submodule import Thing

All accesses are forwarded to the corresponding ``verimem`` module via
:py:meth:`sys.modules` pre-registration — both names point at the same
module object, so identity (``hippoagent.X is verimem.X``), :func:`isinstance`,
and module-level singletons (e.g. MCP registry, schema cache) are stable.

A one-time :class:`DeprecationWarning` is emitted on first import; suppress
with::

    import warnings
    warnings.filterwarnings("ignore", module="hippoagent")

This shim will be **removed in 3 months** (estimated 2026-08-13). Update
your code to use ``from verimem... import ...`` directly.

Implementation note (cycle #41 critic-orchestrator fix, job 614b682c67d39a7f):
the first attempt used a meta-path finder returning the verimem spec —
CPython's ``_load_unlocked`` re-executed the verimem module body and
created a SECOND copy under the ``hippoagent.X`` alias. Module-level state
duplicated, ``isinstance`` failed across paths. Fixed by switching to
eager :func:`pkgutil.walk_packages` pre-population so every
``sys.modules['hippoagent.X']`` is set to the *same object* as
``sys.modules['verimem.X']`` before any user import resolves.
"""
from __future__ import annotations

import importlib
import pkgutil
import sys
import warnings

warnings.warn(
    "The 'hippoagent' package has been renamed to 'verimem'. "
    "Update your imports: `from verimem... import ...`. "
    "This backward-compat shim will be removed in 3 months (~2026-08-13).",
    DeprecationWarning,
    stacklevel=2,
)

# Eager import of verimem so __version__, top-level symbols are available.
import verimem as _verimem  # noqa: E402

__version__ = _verimem.__version__


def _pre_populate_aliases() -> int:
    """Register every ``verimem.X`` submodule under ``hippoagent.X`` in
    :data:`sys.modules`, pointing at the SAME object.

    Walking the verimem package tree forces import of every submodule once;
    each is then aliased under the legacy ``hippoagent.`` prefix. After
    this runs, ``from hippoagent.X import Y`` resolves via the cached
    module — no finder, no re-execution, no duplicated state.

    Idempotent: re-running this function on a process that already has
    aliases installed is a no-op (existing entries are overwritten with
    the same module object).

    Returns the number of aliases registered (introspection / tests).
    """
    n = 0
    for modinfo in pkgutil.walk_packages(
        _verimem.__path__, prefix="verimem.",
    ):
        try:
            real = importlib.import_module(modinfo.name)
        except ImportError:
            # Some submodules may fail to import (optional deps missing in
            # this install, platform-specific code, etc.). Skip silently —
            # those imports would also fail under the canonical `verimem.X`
            # form, so the shim is no worse than direct usage. Narrow to
            # ImportError specifically (ruff S110 / try-except-pass);
            # we don't want to mask unrelated bugs.
            continue
        alias = "hippoagent" + modinfo.name[len("verimem"):]
        sys.modules[alias] = real
        n += 1
    return n


_n_aliases = _pre_populate_aliases()
# Stored for tests / introspection. Not part of the public API.
__alias_count__ = _n_aliases


def __getattr__(name: str):
    """Forward top-level attribute access (``from hippoagent import X``).

    Triggered for any name not statically defined in this module.
    """
    return getattr(_verimem, name)
