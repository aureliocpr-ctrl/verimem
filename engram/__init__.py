"""Engram — persistent memory layer for LLM agents.

Architecture: hippocampal-cortical inspired learning loop.
- Wake: ReAct execution, episodic recording.
- Sleep: replay, skill synthesis, fitness selection.
- Skills are persistent artifacts (not weights), inspectable and versioned.

Formerly named ``hippoagent``. The legacy ``hippoagent`` package is a
backward-compat shim that re-exports this module (see top-level
``hippoagent/__init__.py``); it will be removed ~2026-08-13.
"""
from __future__ import annotations

# Keep in lockstep with pyproject [project].version and .claude-plugin/
# plugin.json — enforced by tests/test_version_single_source.py (audit#2 C-4).
__version__ = "0.4.1"

# Initialize backward-compat env mirror (HIPPO_* ↔ ENGRAM_*) at import time
# so the rest of the package — and anyone importing ``engram`` — sees a
# consistent environment regardless of which prefix the user has set.
from . import _compat as _compat

_compat.init_env_aliases()

# ENGRAM_MODE single-knob (subscription | byok | local): derive the lower-level
# flags (HIPPO_HOSTED / HIPPO_LLM_PROVIDER / HF_HUB_OFFLINE / ...) BEFORE any
# submodule (config, llm, settings) reads the env. Runs on ANY `import
# engram[.x]`. setdefault-safe (never clobbers an explicit flag); no-op when
# ENGRAM_MODE is unset.
from .mode import apply_engram_mode as _apply_engram_mode  # noqa: E402

_apply_engram_mode()

# Public turnkey SDK — exposed lazily so ``import engram`` stays light (the
# Memory client pulls in the embedding/semantic stack only when first used).
__all__ = ["Memory", "Client"]


def __getattr__(name: str):  # PEP 562 lazy attribute access
    if name in ("Memory", "Client"):
        from .client import Client, Memory

        return {"Memory": Memory, "Client": Client}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
