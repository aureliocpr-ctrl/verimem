"""Tests for the Pydantic-Settings v2 module (HIGH #6 in ARCHITECTURE_AUDIT.md)."""
from __future__ import annotations

import os

import pytest

from verimem.settings_v2 import Settings, get_settings, refresh_settings


@pytest.fixture(autouse=True)
def _clear_cache():
    """Settings is cached; clear before AND after every test so envs don't leak."""
    refresh_settings()
    yield
    refresh_settings()


def test_defaults_when_no_env(monkeypatch):
    # Strip every HIPPO_* var so we test pure defaults.
    for k in list(os.environ):
        if k.startswith("HIPPO_"):
            monkeypatch.delenv(k, raising=False)
    refresh_settings()
    s = get_settings()
    assert s.llm_provider == ""
    assert s.model == ""
    assert s.llm_max_tokens == 2048
    assert s.wake_max_steps == 8
    assert s.enable_shell is False
    assert s.enable_web is True
    assert s.fs_strict is False


def test_picks_up_env_at_creation(monkeypatch):
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("HIPPO_MODEL", "claude-haiku-4-5")
    monkeypatch.setenv("HIPPO_LLM_MAX_TOKENS", "4096")
    monkeypatch.setenv("HIPPO_WAKE_MAX_STEPS", "12")
    monkeypatch.setenv("HIPPO_ENABLE_SHELL", "1")
    monkeypatch.setenv("HIPPO_OFFLINE", "1")

    refresh_settings()
    s = get_settings()
    assert s.llm_provider == "anthropic"
    assert s.model == "claude-haiku-4-5"
    assert s.llm_max_tokens == 4096
    assert s.wake_max_steps == 12
    assert s.enable_shell is True
    assert s.use_mock is True


def test_get_settings_is_cached(monkeypatch):
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "kimi")
    refresh_settings()
    s1 = get_settings()
    # Mutate env after the cache is warm — the cached instance should be unchanged.
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "deepseek")
    s2 = get_settings()
    assert s2.llm_provider == "kimi", (
        "settings should be cached until refresh_settings() is called"
    )
    assert s1 is s2


def test_refresh_picks_up_new_env(monkeypatch):
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "kimi")
    refresh_settings()
    assert get_settings().llm_provider == "kimi"

    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "deepseek")
    refresh_settings()
    assert get_settings().llm_provider == "deepseek"


def test_settings_max_tokens_validation():
    """llm_max_tokens must be ≥ 1."""
    with pytest.raises(Exception):
        Settings(llm_max_tokens=0)


def test_user_settings_save_invalidates_v2_cache(tmp_path, monkeypatch):
    """When the dashboard saves user_settings, Settings v2 must reflect it."""
    from verimem import settings as user_settings

    monkeypatch.setattr(user_settings, "SETTINGS_FILE", tmp_path / "user.json")
    # Other tests may have set HIPPO_LLM_PROVIDER as a side-effect of
    # `apply_to_env()`. Strip every HIPPO_* var so the v2 Settings starts
    # from a clean slate for this isolation test.
    for k in list(os.environ):
        if k.startswith("HIPPO_") or k in ("OLLAMA_HOST", "OLLAMA_MODEL"):
            monkeypatch.delenv(k, raising=False)
    refresh_settings()
    s_initial = get_settings()
    assert s_initial.llm_provider == ""

    user_settings.save(user_settings.UserSettings(provider="kimi"))
    s_after = get_settings()
    # apply_to_env() in save() projects s.provider verbatim onto
    # HIPPO_LLM_PROVIDER, and Settings v2 is a *read-only* typed view of that
    # env var (settings_v2.py) — it does NOT normalise aliases. The
    # kimi->moonshot alias resolution happens later, at LLM-client build time
    # (llm.ALIASES, llm.py:1082). So the v2 view must observe the raw "kimi",
    # NOT the resolved "moonshot". Precise, non-disjunctive assert.
    assert s_after.llm_provider == "kimi", (
        f"expected 'kimi' (verbatim, pre-alias), got {s_after.llm_provider!r}"
    )


def test_extra_env_vars_ignored(monkeypatch):
    """HIPPO_UNKNOWN_FOO should not break Settings creation."""
    monkeypatch.setenv("HIPPO_UNKNOWN_FOO", "bar")
    refresh_settings()
    # Must not raise.
    get_settings()
