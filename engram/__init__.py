"""engram — compatibility alias for :mod:`verimem` (renamed in 0.6.0).

The internal package was ``engram`` through 0.5.x; the total rename to
``verimem`` (0.6.0) makes ``verimem`` the real package and keeps this shim so
existing consumers — ``import engram`` / ``from engram.X import Y``, MCP configs,
third-party code — keep working unchanged. Identity holds: ``engram.X is
verimem.X`` (no re-execution, no duplicate module objects — the same meta-path
self-replacement pattern the old ``verimem`` facade used, reversed).

Silent by construction: emitting a DeprecationWarning at import time would trip
this repo's ``filterwarnings = error`` in the test suite (and spam any consumer
on every import). The deprecation notice lives in the docs/CHANGELOG; the alias
is functional, not noisy.
"""
from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys

import verimem as _verimem

__version__ = _verimem.__version__


class _AliasLoader(importlib.abc.Loader):
    """Loads ``engram.X`` by swapping in the already-imported ``verimem.X``."""

    def __init__(self, target: str) -> None:
        self._target = target

    def create_module(self, spec):  # noqa: ANN001 - importlib protocol
        return None

    def exec_module(self, module) -> None:  # noqa: ANN001 - importlib protocol
        real = importlib.import_module(self._target)  # cached -> no re-exec
        sys.modules[module.__spec__.name] = real

    def get_code(self, fullname):  # noqa: ANN001 - runpy support (python -m engram.X)
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
        if not fullname.startswith("engram."):
            return None
        real = "verimem" + fullname[len("engram"):]
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


# Idempotent, head-of-meta_path install (mirror of the old verimem facade).
if not any(isinstance(f, _AliasFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _AliasFinder())


def __getattr__(name: str):
    """Top-level passthrough: ``engram.Memory``, ``engram.semantic``, …"""
    try:
        return getattr(_verimem, name)
    except AttributeError:
        try:
            return importlib.import_module(f"verimem.{name}")
        except ImportError as exc:
            raise AttributeError(
                f"module 'engram' has no attribute {name!r}") from exc
