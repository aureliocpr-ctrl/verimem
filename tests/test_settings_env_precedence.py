"""Explicit HIPPO_LLM_PROVIDER env override must WIN over persisted settings.

Real bug (2026-06-06, found by a live `engram run` in air-gap mode): the
module-level `apply_to_env()` (settings.py, run on import) + `get_llm`'s lazy
`from . import settings` projected the saved settings provider onto os.environ,
CLOBBERING an explicit `HIPPO_LLM_PROVIDER=ollama`. So the FIRST get_llm()
honoured ollama but mutated the env -> the SECOND (sleep/critic) read the saved
cloud provider (anthropic) and tried a cloud call -> air-gap leak / crash
("ANTHROPIC_API_KEY not set"). An operator who forces a provider via env must
keep it (12-factor: env > config file).
"""
from __future__ import annotations

import os

from verimem import settings


def test_explicit_env_provider_survives_apply_to_env(monkeypatch):
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "ollama")
    settings.apply_to_env(settings.UserSettings(provider="anthropic"))
    assert os.environ["HIPPO_LLM_PROVIDER"] == "ollama", (
        "explicit env override must NOT be clobbered by the persisted provider"
    )


def test_settings_provider_applies_when_no_env_override(monkeypatch):
    monkeypatch.delenv("HIPPO_LLM_PROVIDER", raising=False)
    settings.apply_to_env(settings.UserSettings(provider="groq"))
    assert os.environ["HIPPO_LLM_PROVIDER"] == "groq", (
        "with no explicit override, the persisted provider must apply"
    )


def test_empty_env_provider_is_replaced_by_settings(monkeypatch):
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "")  # stale empty
    settings.apply_to_env(settings.UserSettings(provider="ollama"))
    assert os.environ["HIPPO_LLM_PROVIDER"] == "ollama"


def test_get_llm_does_not_mutate_explicit_provider(monkeypatch):
    """End-to-end: building an LLM must not corrupt the explicit override for
    the next builder (the air-gap multi-LLM failure mode)."""
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "ollama")
    monkeypatch.delenv("HIPPO_HOSTED", raising=False)
    from verimem.llm import get_llm
    get_llm()  # was mutating os.environ to the saved provider
    assert os.environ["HIPPO_LLM_PROVIDER"] == "ollama", (
        "get_llm() must not clobber the explicit provider override"
    )
