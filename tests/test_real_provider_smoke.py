"""FORGIA pezzo #36 — Smoke test against a real LLM provider.

Skipped automatically when no provider API key is configured.

The point isn't to validate model quality (the bench harness covers
that) — it's to catch wire-level regressions: a SDK signature change,
a JSON schema drift, an auth header rename, a base_url that quietly
moved. Things that mocks miss because they bypass the network.

We probe the cheapest model available for each configured provider
with a one-token-grade prompt and assert the call comes back with a
non-empty answer + non-zero token usage.

To force-run the test even with keys, set `HIPPO_RUN_REAL_LLM=1`.
"""
from __future__ import annotations

import os

import pytest

# Trigger HippoAgent's .env discovery so keys in repo-local files are
# visible to the test (`engram.config` searches the repo-local `.env`).
# Without this, `_AVAILABLE` is empty even when the keys are present
# in the developer's normal env.
from engram.config import _load_env  # noqa: E402

_load_env()


# Skip the entire module if no provider key is set — keeps CI green
# on machines without secrets.
_PROVIDER_ENV: list[tuple[str, str]] = [
    ("anthropic", "ANTHROPIC_API_KEY"),
    ("openai", "OPENAI_API_KEY"),
    ("openrouter", "OPENROUTER_API_KEY"),
    ("groq", "GROQ_API_KEY"),
    ("mistral", "MISTRAL_API_KEY"),
    ("deepseek", "DEEPSEEK_API_KEY"),
    ("gemini", "GEMINI_API_KEY"),
    ("xai", "XAI_API_KEY"),
]
_AVAILABLE = [
    name for name, env in _PROVIDER_ENV if os.environ.get(env, "").strip()
]


pytestmark = [
    # Live integration: hits the real provider API over the network. It is
    # incompatible with the default OFFLINE suite (conftest enforces
    # HIPPO_OFFLINE=1), so mark it e2e — the default run `-m "not slow and not
    # e2e"` excludes it. Run explicitly online with keys: `pytest -m e2e
    # tests/test_real_provider_smoke.py` (or `make bench-real`).
    pytest.mark.e2e,
    pytest.mark.skipif(
        not _AVAILABLE,
        reason="no real LLM provider key configured",
    ),
]


@pytest.mark.parametrize("provider", _AVAILABLE or ["mock"])
def test_real_provider_responds(provider, monkeypatch):
    """One-shot prompt — model must respond with a non-empty answer.

    Uses each provider's *default* model (cheapest sane choice). The
    test is intentionally permissive on content — quality lives in
    the bench harness; this is a wire-level smoke.
    """
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", provider)
    # Strip any cross-provider model overrides so each provider uses
    # its own default. A leftover `HIPPO_MODEL=claude-opus-4-7` would
    # cause every non-Anthropic provider to 400.
    for var in ("HIPPO_MODEL", "HIPPO_MODEL_EXECUTOR",
                "HIPPO_MODEL_DREAMER", "HIPPO_MODEL_CRITIC"):
        monkeypatch.delenv(var, raising=False)
    # Force the provider to refresh from env, ignoring any leftover cache.
    from engram.llm import LLMError, get_llm
    try:
        llm = get_llm(use_mock=False)
    except LLMError as exc:
        if "not set" in str(exc).lower():
            # Key visible at collection but gone at runtime (another test's env
            # hygiene) — an environment condition, not a wire regression.
            pytest.skip(f"{provider}: {exc}")
        raise

    try:
        resp = llm.complete(
            system="You are a precise assistant. Answer in 1-3 words only.",
            messages=[{"role": "user", "content": "Capital of France?"}],
        )
    except LLMError as exc:
        msg = str(exc).lower()
        # Quota exhaustion / billing is upstream — not a code regression.
        if any(s in msg for s in ("429", "quota", "credit", "billing",
                                   "exhausted", "rate limit", "spending limit")):
            pytest.skip(f"{provider}: upstream quota/billing issue ({exc})")
        raise
    assert resp.text and resp.text.strip(), (
        f"{provider}: empty response"
    )
    assert resp.input_tokens > 0, (
        f"{provider}: input_tokens not reported"
    )
    # Some providers report 0 output tokens for very short replies; lenient.
    assert resp.total_tokens > 0


def test_real_provider_count_is_consistent_with_env():
    """Sanity: every provider in `_AVAILABLE` actually has a key set."""
    for name, env in _PROVIDER_ENV:
        if name in _AVAILABLE:
            assert os.environ.get(env, "").strip(), (
                f"{name} in _AVAILABLE but {env} not set"
            )
