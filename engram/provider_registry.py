"""Pydantic-validated LLM provider registry, loaded from `providers.yaml`.

Replaces the untyped `dict[str, dict[str, Any]]` registry that was previously
inlined in `llm.py` (CRITICAL #3 in ARCHITECTURE_AUDIT.md). The registry is:

  • declared as data — `hippoagent/providers.yaml`,
  • parsed and validated with Pydantic at import time,
  • exposed as `PROVIDERS_DICT` (legacy shape) so the existing dict-based
    callers in `llm.py` and `dashboard_routes/settings.py` keep working,
  • exposed as `PROVIDERS` (typed list of `ProviderSpec`) for new code.

Backward compatibility:
  • `from engram.llm import PROVIDERS, ALIASES` — unchanged.
  • `PROVIDERS["openai"]["env"]` keys still resolve to the same strings.

Adding a new provider:
  1. append an entry to `providers.yaml`,
  2. run `hippo provider check <name>` for a real round-trip diagnostic,
  3. run `pytest tests/test_provider_registry.py`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

ProviderFamily = Literal["anthropic", "openai_compat", "ollama", "mock"]
ModelTier = Literal["frontier", "mid", "fast", "reasoning", "coder", "small"]


class RecommendedModel(BaseModel):
    """One model surfaced in the UI selector for a given provider.

    Curated list — not the full /models output. Pin the exact API id
    plus a few hints so the UI can group and filter without round-tripping
    to the provider on every render.

    `id` is the literal value passed to the provider's API.
    `label` is the human-readable name shown in the UI.
    `tier` is one of frontier/mid/fast/reasoning/coder/small — used for
        sorting and filtering in the UI.
    `notes` is an optional short comment (e.g. "MoE, 1.6T total, 49B active",
        "needs 24GB VRAM").
    `supports_tools` / `supports_vision` / `supports_reasoning` override
        the provider-level flags when a specific model has different
        capabilities.
    """

    id: str = Field(min_length=1)
    label: str = ""
    tier: ModelTier = "mid"
    notes: str = ""
    supports_tools: bool | None = None
    supports_vision: bool | None = None
    supports_reasoning: bool | None = None


class ProviderSpec(BaseModel):
    """One provider as declared in `providers.yaml`.

    Field semantics:
      - `name` — canonical id (lowercase, used as the key everywhere).
      - `env` — env var that holds the API key. Empty string for providers
        that don't need a key (ollama, mock).
      - `base_url` — default OpenAI-compatible endpoint. Empty for providers
        that ship their own native SDK (anthropic).
      - `base_url_env` — optional env var that, if set, replaces base_url.
      - `default_model` — model id used when `HIPPO_MODEL` is not set.
      - `family` — selects the adapter class inside `llm.py`.
      - `aliases` — extra names that resolve back to this provider via
        `_canonical(...)`. Always lowercase.
      - `supports_tools` / `supports_vision` — capability flags surfaced
        to callers; not enforced at runtime (it's a hint).
    """

    name: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    env: str = ""
    base_url: str = ""
    base_url_env: str | None = None
    default_model: str = ""
    family: ProviderFamily = "openai_compat"
    supports_tools: bool = True
    supports_vision: bool = False
    aliases: list[str] = Field(default_factory=list)
    # Curated model list shown in the UI selector. Empty list = use
    # provider's full /models discovery.
    recommended_models: list[RecommendedModel] = Field(default_factory=list)

    @field_validator("aliases")
    @classmethod
    def _aliases_lowercase(cls, v: list[str]) -> list[str]:
        cleaned = [a.lower().strip() for a in v if a and a.strip()]
        # Reject duplicates within an entry.
        if len(cleaned) != len(set(cleaned)):
            raise ValueError(f"duplicate aliases: {cleaned}")
        return cleaned

    def to_legacy_dict(self) -> dict[str, Any]:
        """Project this spec back to the dict shape the legacy llm.py uses.

        Some callers (e.g. settings page) expect `PROVIDERS["openai"]["env"]`.
        We keep that contract so the split is risk-free.
        """
        out: dict[str, Any] = {
            "env": self.env,
            "base_url": self.base_url,
            "default_model": self.default_model,
        }
        if self.base_url_env:
            out["base_url_env"] = self.base_url_env
        return out


class ProviderRegistry(BaseModel):
    """Top-level YAML schema."""
    providers: list[ProviderSpec]

    @field_validator("providers")
    @classmethod
    def _no_duplicate_names(cls, v: list[ProviderSpec]) -> list[ProviderSpec]:
        seen: set[str] = set()
        for p in v:
            if p.name in seen:
                raise ValueError(f"duplicate provider name: {p.name}")
            seen.add(p.name)
        return v


# ----- YAML loader --------------------------------------------------------


def _registry_path() -> Path:
    return Path(__file__).resolve().parent / "providers.yaml"


def load_registry(path: Path | None = None) -> ProviderRegistry:
    """Read + validate the YAML registry. Raises on parse / schema errors."""
    import yaml  # imported here so import-time failure surfaces clearly
    src = path or _registry_path()
    with src.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    try:
        return ProviderRegistry.model_validate(data)
    except ValidationError as exc:
        raise RuntimeError(
            f"Invalid provider registry at {src}: {exc}"
        ) from exc


# ----- Module-level: load once at import ---------------------------------

_REGISTRY: ProviderRegistry = load_registry()

# Public typed view.
PROVIDERS_LIST: list[ProviderSpec] = list(_REGISTRY.providers)
PROVIDERS_BY_NAME: dict[str, ProviderSpec] = {p.name: p for p in PROVIDERS_LIST}

# Legacy dict view — kept for backward compatibility with llm.py callers.
# We exclude `anthropic`, `ollama`, and `mock` because the legacy dict only
# held OpenAI-compat providers; the others are special-cased in llm.py.
LEGACY_PROVIDERS_DICT: dict[str, dict[str, Any]] = {
    p.name: p.to_legacy_dict()
    for p in PROVIDERS_LIST
    if p.family == "openai_compat"
}

# Aliases map: alias -> canonical name.
ALIASES_DICT: dict[str, str] = {}
for _p in PROVIDERS_LIST:
    for _alias in _p.aliases:
        ALIASES_DICT[_alias] = _p.name


def get_provider(name: str) -> ProviderSpec | None:
    """Resolve a provider by its canonical name or one of its aliases."""
    key = name.lower().strip()
    canonical = ALIASES_DICT.get(key, key)
    return PROVIDERS_BY_NAME.get(canonical)


def reload_registry(path: Path | None = None) -> None:
    """Test helper — reload the registry from a custom path."""
    global _REGISTRY, PROVIDERS_LIST, PROVIDERS_BY_NAME
    global LEGACY_PROVIDERS_DICT, ALIASES_DICT
    _REGISTRY = load_registry(path)
    PROVIDERS_LIST = list(_REGISTRY.providers)
    PROVIDERS_BY_NAME = {p.name: p for p in PROVIDERS_LIST}
    LEGACY_PROVIDERS_DICT = {
        p.name: p.to_legacy_dict()
        for p in PROVIDERS_LIST
        if p.family == "openai_compat"
    }
    ALIASES_DICT = {}
    for p in PROVIDERS_LIST:
        for alias in p.aliases:
            ALIASES_DICT[alias] = p.name


__all__ = [
    "ProviderSpec",
    "ProviderRegistry",
    "RecommendedModel",
    "PROVIDERS_LIST",
    "PROVIDERS_BY_NAME",
    "LEGACY_PROVIDERS_DICT",
    "ALIASES_DICT",
    "load_registry",
    "reload_registry",
    "get_provider",
]
