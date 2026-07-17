"""Tests for /api/settings/recommended_models — UI-facing curated list.

The endpoint must not round-trip to any external provider; it reads
from the local `providers.yaml` only. That makes it cheap to call from
the UI on every settings page render.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from verimem import dashboard


def test_get_all_recommended_models():
    client = TestClient(dashboard.app)
    r = client.get("/api/settings/recommended_models")
    assert r.status_code == 200
    payload = r.json()
    assert "providers" in payload
    providers = payload["providers"]

    # Every non-mock provider in providers.yaml should appear.
    assert "anthropic" in providers
    assert "ollama" in providers
    assert "openai" in providers
    assert "mock" not in providers  # explicitly excluded

    # Each entry has the expected shape.
    for name, info in providers.items():
        assert "default_model" in info
        assert "recommended_models" in info
        assert isinstance(info["recommended_models"], list)


def test_get_single_provider_recommended_models():
    client = TestClient(dashboard.app)
    r = client.get("/api/settings/recommended_models?provider=anthropic")
    assert r.status_code == 200
    payload = r.json()
    assert payload["provider"] == "anthropic"
    assert payload["default_model"]  # non-empty
    models = payload["recommended_models"]
    # Anthropic has 3 curated models in 2026: opus 4.7, sonnet 4.6, haiku 4.5
    assert len(models) >= 3
    ids = {m["id"] for m in models}
    assert "claude-opus-4-7" in ids
    # Each entry has id + label + tier
    for m in models:
        assert m["id"]
        assert m["tier"] in {"frontier", "mid", "fast", "reasoning", "coder", "small"}


def test_unknown_provider_returns_404():
    client = TestClient(dashboard.app)
    r = client.get("/api/settings/recommended_models?provider=does-not-exist")
    assert r.status_code == 404
    assert "error" in r.json()


def test_alias_does_not_resolve_through_this_endpoint():
    """The endpoint matches by canonical name; aliases (e.g. `claude` for
    `anthropic`) need to be resolved client-side. This is intentional —
    the endpoint is a thin lookup, not a query parser."""
    client = TestClient(dashboard.app)
    r = client.get("/api/settings/recommended_models?provider=claude")
    # `claude` is an alias, not a canonical name → 404 here.
    assert r.status_code == 404


def test_ollama_has_local_tier_models():
    """Ollama's recommended list should include small-tier models for
    laptops/8GB RAM machines, not only the big GPUs."""
    client = TestClient(dashboard.app)
    r = client.get("/api/settings/recommended_models?provider=ollama")
    payload = r.json()
    tiers = {m["tier"] for m in payload["recommended_models"]}
    assert "small" in tiers, "ollama list missing small-tier (8GB-friendly) models"
    assert "frontier" in tiers, "ollama list missing frontier-tier (24GB GPU) models"
