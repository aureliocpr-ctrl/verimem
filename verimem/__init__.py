"""verimem — the PUBLIC name of the package (canonical alias over ``engram``).

One product, one name (Aurelio, 2026-07-06: three names — verimem / engram /
hippo_* — confuse a user). This package makes every user-facing surface spell
**verimem**::

    from verimem import Memory          # the 5-verb SDK
    import verimem.semantic             # any submodule — same object as engram.X

Unlike the legacy ``hippoagent`` shim this is NOT deprecated and does NOT
eager-import the whole tree (``import verimem`` stays as light as ``import
engram``). Submodules resolve lazily through a meta-path alias finder whose
loader swaps the REAL ``engram.X`` module into ``sys.modules`` during
``exec_module`` — the documented self-replacement pattern, so there is no
re-execution (the cycle-#41 trap) and no mutation of the real module's
``__name__``/``__spec__``. Identity holds: ``verimem.X is engram.X``.

The internal package stays ``engram`` until the gated v0.4 deep rename.
"""
from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import sys

import engram as _engram

__version__ = _engram.__version__


class _AliasLoader(importlib.abc.Loader):
    """Loads ``verimem.X`` by swapping in the already-imported ``engram.X``."""

    def __init__(self, target: str) -> None:
        self._target = target

    def create_module(self, spec):  # noqa: ANN001 - importlib protocol
        return None  # placeholder module; replaced in exec_module

    def exec_module(self, module) -> None:  # noqa: ANN001 - importlib protocol
        real = importlib.import_module(self._target)  # cached -> no re-exec
        # Self-replacement: after exec the import machinery re-reads
        # sys.modules[name], so the alias binds to the REAL module object and
        # the placeholder is dropped. engram.X's __name__/__spec__ untouched.
        sys.modules[module.__spec__.name] = real


class _AliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):  # noqa: ANN001
        if not fullname.startswith("verimem."):
            return None
        real = "engram" + fullname[len("verimem"):]
        return importlib.machinery.ModuleSpec(
            fullname, _AliasLoader(real), is_package=True)


# Idempotent install (re-import of this module must not stack finders).
if not any(isinstance(f, _AliasFinder) for f in sys.meta_path):
    sys.meta_path.append(_AliasFinder())


def __getattr__(name: str):
    """Top-level passthrough: ``verimem.Memory``, ``verimem.semantic``, …"""
    try:
        return getattr(_engram, name)
    except AttributeError:
        try:
            return importlib.import_module(f"engram.{name}")
        except ImportError as exc:
            raise AttributeError(
                f"module 'verimem' has no attribute {name!r}") from exc


__all__ = ["Memory", "Client", "__version__"]
