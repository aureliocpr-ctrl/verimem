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
import importlib.util
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

    # runpy support (``python -m verimem.X``, review 5-lenti C7): delegate the
    # code lookup to the real module's loader under its REAL name, so -m
    # executes engram/X.py exactly as ``python -m engram.X`` would.
    def get_code(self, fullname):  # noqa: ANN001 - importlib protocol
        spec = importlib.util.find_spec(self._target)
        if spec and spec.loader and hasattr(spec.loader, "get_code"):
            return spec.loader.get_code(self._target)
        return None

    def get_source(self, fullname):  # noqa: ANN001 - importlib protocol
        spec = importlib.util.find_spec(self._target)
        if spec and spec.loader and hasattr(spec.loader, "get_source"):
            return spec.loader.get_source(self._target)
        return None


class _AliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):  # noqa: ANN001
        if not fullname.startswith("verimem."):
            return None
        real = "engram" + fullname[len("verimem"):]
        # Review 5-lenti C7: resolve the REAL spec first. (a) Missing target ->
        # None, so the machinery raises ModuleNotFoundError named after what
        # the USER typed (no synthetic spec for nonexistent modules, no
        # feature-detection false positives). (b) Mirror the real module's
        # shape: is_package=True on a flat module broke ``python -m``
        # ("is a package and cannot be directly executed").
        try:
            real_spec = importlib.util.find_spec(real)
        except (ImportError, AttributeError, ValueError):
            return None
        if real_spec is None:
            return None
        spec = importlib.machinery.ModuleSpec(
            fullname, _AliasLoader(real), origin=real_spec.origin,
            is_package=real_spec.submodule_search_locations is not None)
        if real_spec.submodule_search_locations is not None:
            spec.submodule_search_locations = list(
                real_spec.submodule_search_locations)
        return spec


# Idempotent install (re-import of this module must not stack finders).
# INSERTED AT THE HEAD (C7): appended, the finder lost every NESTED name
# (verimem.swarm.X) to PathFinder, which found the file via the swapped
# parent's real __path__ and RE-EXECUTED it under the alias name — two
# distinct module objects (the cycle-#41 trap). First in line, every
# verimem.* import resolves through the alias; non-verimem names cost one
# startswith check.
if not any(isinstance(f, _AliasFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _AliasFinder())


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
