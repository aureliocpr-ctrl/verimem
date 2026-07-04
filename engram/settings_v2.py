"""Pydantic-settings v2 — single source of truth for HIPPO_* env vars.

Replaces the scattered `os.environ.get("HIPPO_*", ...)` calls with one typed
`Settings` class loaded from env at process start (HIGH #6 in
ARCHITECTURE_AUDIT.md).

Why a v2 module instead of editing `settings.py`?
  • `settings.py` already owns the persisted JSON (`UserSettings`) and the
    `apply_to_env()` helper that the dashboard mutates. Migrating it in-place
    risks a churn-heavy rewrite that fights the 299-tests-must-stay-green
    constraint.
  • `settings_v2.Settings` is a *read-only* projection of the env. Code that
    used to do `os.environ.get("HIPPO_FOO", "default")` can now do
    `get_settings().foo` and get a typed value. The legacy paths keep working.
  • When the legacy `apply_to_env()` mutates env, callers can ask for a
    `Settings.refresh()` to re-read.

Migration path (incremental, no flag-day):
  1. New code reads from `get_settings()` directly.
  2. Old `os.environ.get` sites are migrated module-by-module as touched.
  3. `apply_to_env()` calls `Settings.refresh()` once after writing env so
    the cache is consistent.

This file is import-safe (no I/O at import time other than reading os.environ
which Python already populated).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed view of the HIPPO_* environment.

    All fields default to safe values that match the pre-v2 behaviour.
    Adding a new env var: add a field here, give it a sensible default,
    update tests/test_settings_v2.py to assert defaults + override.
    """

    model_config = SettingsConfigDict(
        env_prefix="HIPPO_",
        env_file=None,  # dotenv loading still happens via config._load_env()
        case_sensitive=False,
        extra="ignore",
    )

    # ----- LLM provider selection ---------------------------------------
    llm_provider: str = Field(
        default="",
        description="Forced provider (overrides autodetect). Empty = autodetect.",
    )
    model: str = Field(default="", description="Model id (all stages)")
    model_executor: str = Field(default="", description="Model id for the wake-loop executor")
    model_dreamer: str = Field(default="", description="Model id for the sleep-cycle dreamer")
    model_critic: str = Field(default="", description="Model id for self-critique")
    llm_max_tokens: int = Field(default=2048, ge=1)
    offline: bool = Field(default=False, description="HIPPO_OFFLINE=1 forces MockLLM")

    # ----- Wake / sleep -------------------------------------------------
    wake_max_steps: int = Field(default=8, ge=1, le=64)

    # ----- Sandbox capability flags -------------------------------------
    enable_shell: bool = Field(default=False)
    enable_computer_use: bool = Field(default=False)
    enable_webcam: bool = Field(default=False)
    enable_web: bool = Field(default=True)
    enable_vision: bool = Field(default=True)

    # ----- Filesystem policy --------------------------------------------
    fs_strict: bool = Field(default=False)
    fs_home: bool = Field(default=False)
    fs_root: str = Field(default="")

    # ----- Ollama overrides ---------------------------------------------
    # (Ollama uses non-prefixed OLLAMA_HOST / OLLAMA_MODEL; tracked outside
    # this Settings class because the env_prefix=HIPPO_ guard is intentional.)

    # ----- Dashboard auth -----------------------------------------------
    dashboard_auth_disabled: bool = Field(default=True)
    dashboard_token: str = Field(default="")

    # ----- Misc / legacy passthroughs -----------------------------------
    trusted_network: Literal["", "0", "1", "true", "false", "yes", "no"] = ""

    @property
    def use_mock(self) -> bool:
        """Was MockLLM explicitly requested via HIPPO_OFFLINE=1?"""
        return self.offline


# ----- Cached singleton --------------------------------------------------
# `lru_cache` keeps `Settings()` cheap. Tests / `apply_to_env()` call
# `refresh_settings()` to invalidate the cache after mutating env.

@lru_cache(maxsize=1)
def _build_settings() -> Settings:
    return Settings()


def get_settings() -> Settings:
    """Return the cached Settings singleton, re-creating it on first access."""
    return _build_settings()


def refresh_settings() -> Settings:
    """Drop the cache and re-read env. Call after mutating os.environ."""
    _build_settings.cache_clear()
    return _build_settings()


__all__ = ["Settings", "get_settings", "refresh_settings"]
