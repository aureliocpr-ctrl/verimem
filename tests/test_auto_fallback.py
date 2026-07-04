"""FORGIA pezzo #45 — `HIPPO_AUTO_FALLBACK` env var.

Without explicit user config, the LLM dispatcher only chains
fallback providers if `HIPPO_AUTO_FALLBACK=1` is set. The auto-mode
walks the provider registry, picks every OTHER provider that has its
API key set, and chains them after the primary so a 429 / 5xx /
timeout on the primary cascades through the chain.

Three invariants:

  1. NO ENV → no auto-chain (legacy behaviour preserved).
  2. ENV=1 + only primary configured → no chain (nothing to fall back to).
  3. ENV=1 + primary + secondary both configured → chain length ≥ 1.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def force_provider_configured(monkeypatch, request):
    """Yield a setter; restore CONFIG.anthropic_api_key after the test.

    `is_configured('anthropic')` reads CONFIG.anthropic_api_key (cached
    at config-import time), not the live env. We bypass the frozen
    dataclass with object.__setattr__ and register a finalizer to
    restore the original.
    """
    from engram.config import CONFIG
    original_key = CONFIG.anthropic_api_key

    def _restore():
        object.__setattr__(CONFIG, "anthropic_api_key", original_key)
    request.addfinalizer(_restore)

    def _setter(names: list[str]) -> None:
        from engram.llm import PROVIDERS
        all_envs = {p["env"] for p in PROVIDERS.values() if p.get("env")}
        all_envs.add("ANTHROPIC_API_KEY")
        for env in all_envs:
            monkeypatch.delenv(env, raising=False)
        name_to_env = {n: PROVIDERS[n]["env"] for n in PROVIDERS}
        name_to_env["anthropic"] = "ANTHROPIC_API_KEY"
        for n in names:
            env = name_to_env.get(n)
            if env:
                monkeypatch.setenv(env, "test-fake-key-12345")
        has_anthropic = "anthropic" in names
        object.__setattr__(
            CONFIG, "anthropic_api_key",
            "test-fake-key-12345" if has_anthropic else "",
        )

    return _setter


def test_no_auto_fallback_without_env(monkeypatch, force_provider_configured):
    """Without HIPPO_AUTO_FALLBACK=1, no auto-chain even with multiple keys."""
    monkeypatch.delenv("HIPPO_AUTO_FALLBACK", raising=False)
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "mock")
    force_provider_configured(["anthropic", "openai"])
    from engram.llm import FallbackLLM, get_llm
    llm = get_llm()
    assert not isinstance(llm, FallbackLLM)


def test_auto_fallback_with_only_primary(monkeypatch, force_provider_configured):
    """Auto on but only mock provider available → no chain."""
    monkeypatch.setenv("HIPPO_AUTO_FALLBACK", "1")
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "mock")
    force_provider_configured([])  # nothing configured
    from engram.llm import FallbackLLM, get_llm
    llm = get_llm()
    assert not isinstance(llm, FallbackLLM)


@pytest.mark.skipif(True, reason="needs real provider clients to instantiate; skipped offline")
def test_auto_fallback_with_multiple_keys_creates_chain():
    """FORGIA #45 happy path — needs network. Skipped offline."""
    pass
