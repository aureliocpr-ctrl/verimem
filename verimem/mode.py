"""Single deployment-mode knob: ``ENGRAM_MODE`` = subscription | byok | local.

One env var instead of three, so a company can install Engram in any posture
without learning the underlying flags. Each mode DERIVES the lower-level env
vars — but only when they are not already explicitly set (12-factor: an explicit
low-level env var wins, same precedence as ``settings.apply_to_env``). So the
knob is a friendly default-setter, never a clobber.

  subscription  host LLM (Claude Code / Desktop), zero API keys
                -> HIPPO_HOSTED=1
  byok          enterprise brings its OWN cloud provider + key
                -> the operator sets HIPPO_LLM_PROVIDER + <KEY>; this mode only
                   asserts it is NOT hosted (no derivation to clobber)
  local         fully air-gapped: local model + offline embeddings
                -> HIPPO_LLM_PROVIDER=ollama, HF_HUB_OFFLINE=1,
                   TRANSFORMERS_OFFLINE=1  (HIPPO_HOSTED stays unset = off)

Safe to call at import: setdefault semantics never overwrite an explicit value.
"""
from __future__ import annotations

import os
from collections.abc import MutableMapping

VALID_MODES = ("subscription", "byok", "local")


def engram_mode(env: MutableMapping[str, str] | None = None) -> str:
    """Return the normalized ENGRAM_MODE ("" if unset)."""
    env = os.environ if env is None else env
    return (env.get("ENGRAM_MODE") or "").strip().lower()


def _setdefault(env: MutableMapping[str, str], key: str, val: str) -> bool:
    """Set ``key=val`` only if it is not already explicitly present + non-empty.
    Returns True if it applied the default."""
    if (env.get(key) or "").strip():
        return False
    env[key] = val
    return True


def apply_engram_mode(env: MutableMapping[str, str] | None = None) -> dict:
    """Project ENGRAM_MODE onto the lower-level env vars (default-set, no clobber).

    Returns ``{"mode", "valid", "applied": {var: val, ...}}``. No-op (mode=None)
    when ENGRAM_MODE is unset, preserving the current explicit-flags behaviour.
    """
    env = os.environ if env is None else env
    mode = engram_mode(env)
    applied: dict[str, str] = {}
    if mode == "subscription":
        if _setdefault(env, "HIPPO_HOSTED", "1"):
            applied["HIPPO_HOSTED"] = "1"
    elif mode == "local":
        for key, val in (
            ("HIPPO_LLM_PROVIDER", "ollama"),
            ("HF_HUB_OFFLINE", "1"),
            ("TRANSFORMERS_OFFLINE", "1"),
        ):
            if _setdefault(env, key, val):
                applied[key] = val
    elif mode == "byok":
        # Operator-configured cloud provider + key; nothing to derive. byok is
        # explicitly NOT hosted — but we never clobber an explicit HIPPO_HOSTED.
        pass
    return {
        "mode": mode or None,
        "valid": (mode in VALID_MODES) if mode else True,
        "applied": applied,
    }


__all__ = ["VALID_MODES", "engram_mode", "apply_engram_mode"]
