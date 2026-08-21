"""Verimem — verified persistent memory for LLM agents.

Writes pass an admission gate; a fact its source does not support is
QUARANTINED — stored, but kept out of default recall.

Architecture: hippocampal-cortical inspired learning loop.
- Wake: ReAct execution, episodic recording.
- Sleep: replay, skill synthesis, fitness selection.
- Skills are persistent artifacts (not weights), inspectable and versioned.

THE NAMES, and which one is the product. ``verimem`` is the package and the
brand (PyPI ``verimem``, env prefix ``VERIMEM_*``, fresh data dir
``~/.verimem``). ``engram`` was the architecture name through 0.5.x and
``hippoagent`` the original one; both survive as import shims with identity
(``engram.X is verimem.X``) and as env prefixes mirrored by
:func:`_compat.init_env_aliases` — verified live 2026-08-02 in all five
directions, including that an explicit value on one side is never overwritten
by the other. Nothing configured on the old names breaks.

This docstring used to open with the OLD name while the README declared the
new one and then taught the old one in all five of its configuration examples:
a document that names itself one thing and teaches another. Presented first is
the name that gets learned.

``hippoagent`` (the shim, not the env prefix) is DEPRECATED: it still ships and
still imports. Removal is NOT dated, deliberately — a date lived here, and in
``agent_guide.py``, until 2026-08-14, and it passed with the shim still in
place. A promise with an expiry date is the only kind that turns false on its
own, with nobody touching anything; and this one is served to every MCP client
on connect. Whoever schedules the removal puts a date back in BOTH places —
and in ``_compat.py``, which carries its own for a DIFFERENT debt (the
``HIPPO_*`` env names).
"""
from __future__ import annotations

# Keep in lockstep with pyproject [project].version and .claude-plugin/
# plugin.json — enforced by tests/test_version_single_source.py (audit#2 C-4).
__version__ = "0.7.6"

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

# Il tetto ai thread di calcolo, PRIMA che torch esista in questo processo. Su
# 20 core torch ne prende 10, e a dieci si perde su ENTRAMBI gli assi: 525 MB di
# prenotazione in piu' e un batch da 32 otto volte piu' lento (misurato il
# 20/08; i numeri e il metodo stanno nel modulo). setdefault-safe;
# `VERIMEM_TORCH_THREADS=0` lo disattiva.
from ._thread_budget import applica_tetto_thread as _applica_tetto_thread  # noqa: E402

_applica_tetto_thread()

# Public turnkey SDK — exposed lazily so ``import verimem`` stays light (the
# Memory client pulls in the embedding/semantic stack only when first used).
__all__ = ["AutoMemory", "Memory", "Client"]


def __getattr__(name: str):  # PEP 562 lazy attribute access
    if name in ("Memory", "Client", "open_memory"):
        from .client import Client, Memory, open_memory

        return {"Memory": Memory, "Client": Client,
                "open_memory": open_memory}[name]
    if name == "AutoMemory":
        from .auto_memory import AutoMemory

        return AutoMemory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
