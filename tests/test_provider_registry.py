"""Tests for the YAML-backed LLM provider registry (ARCHITECTURE_AUDIT CRITICAL #3).

Asserts:
  • the bundled `providers.yaml` parses cleanly,
  • every spec has the expected shape (Pydantic validation),
  • every alias resolves to a real provider,
  • the legacy dict view stays in sync with the typed view,
  • `get_provider` resolves aliases case-insensitively.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from verimem import provider_registry as pr


def test_registry_loads_at_least_20_providers():
    """The bundled YAML must ship the curated set the audit asked for."""
    assert len(pr.PROVIDERS_LIST) >= 20, (
        f"expected >=20 providers, got {len(pr.PROVIDERS_LIST)}: "
        f"{[p.name for p in pr.PROVIDERS_LIST]}"
    )


def test_every_provider_has_required_fields():
    for spec in pr.PROVIDERS_LIST:
        assert spec.name, f"provider name must not be empty: {spec}"
        assert spec.family in ("anthropic", "openai_compat", "ollama", "mock")
        # Each OpenAI-compat provider must have a base_url.
        if spec.family == "openai_compat":
            assert spec.base_url, f"{spec.name} (openai_compat) needs base_url"
        # Anthropic + ollama + mock have native SDKs / local servers.
        if spec.family == "openai_compat" and spec.name not in ("mock",):
            assert spec.env, f"{spec.name} needs an env var"


def test_no_duplicate_provider_names():
    seen = [p.name for p in pr.PROVIDERS_LIST]
    assert len(seen) == len(set(seen)), f"duplicates: {seen}"


def test_aliases_map_to_real_providers():
    """Every alias must point at a real canonical name."""
    for alias, canonical in pr.ALIASES_DICT.items():
        assert canonical in pr.PROVIDERS_BY_NAME, (
            f"alias {alias!r} -> {canonical!r} but {canonical!r} is not a "
            f"known provider. Known: {sorted(pr.PROVIDERS_BY_NAME)}"
        )


def test_alias_resolution_case_insensitive():
    spec = pr.get_provider("KIMI")
    assert spec is not None
    assert spec.name == "moonshot"


def test_get_provider_returns_none_for_unknown():
    assert pr.get_provider("does-not-exist") is None


def test_legacy_dict_excludes_native_families():
    """Anthropic / ollama / mock are NOT in the legacy openai-compat dict."""
    for special in ("anthropic", "ollama", "mock"):
        assert special not in pr.LEGACY_PROVIDERS_DICT, (
            f"{special} should be special-cased in llm.py, not in legacy dict"
        )


def test_legacy_dict_shape_matches_llm_py_expectations():
    """Each entry must expose env, base_url, default_model — same shape llm.py uses."""
    for name, entry in pr.LEGACY_PROVIDERS_DICT.items():
        assert "env" in entry, name
        assert "base_url" in entry, name
        assert "default_model" in entry, name


def test_invalid_yaml_rejected(tmp_path: Path):
    """A bad spec (duplicate name) must fail validation, not silently load."""
    bad = tmp_path / "providers.yaml"
    bad.write_text(
        yaml.safe_dump({
            "providers": [
                {"name": "x", "family": "openai_compat",
                 "base_url": "https://x.com", "env": "X_API_KEY",
                 "default_model": "x"},
                {"name": "x", "family": "openai_compat",
                 "base_url": "https://y.com", "env": "Y_API_KEY",
                 "default_model": "y"},
            ],
        }),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="duplicate provider name"):
        pr.load_registry(bad)


def test_invalid_name_pattern_rejected(tmp_path: Path):
    """Names must match `^[a-z0-9_]+$` — uppercase and dashes are rejected."""
    bad = tmp_path / "providers.yaml"
    bad.write_text(
        yaml.safe_dump({
            "providers": [
                {"name": "BadName", "family": "openai_compat",
                 "base_url": "https://x.com", "env": "X_API_KEY",
                 "default_model": "x"},
            ],
        }),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError):
        pr.load_registry(bad)
