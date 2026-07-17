"""TDD — il motore (llm.PROVIDERS inline) deve usare i default_model AGGIORNATI
di providers.yaml, non quelli obsoleti hardcoded (rescan2 dual-registry, 2026-06-02).

llm.py teneva default_model obsoleti (gpt-4o-mini, gemini-1.5-flash, glm-4-plus,
moonshot-v1-8k...) mentre cli/dashboard usano providers.yaml con gli id 2026
(gpt-5.4-mini, gemini-3-flash, glm-5.1, kimi-k2...). Il motore girava su id vecchi.

Fix aggiusta-non-rovina: per i provider presenti in ENTRAMBI, llm.PROVIDERS deriva
il default_model dal registry (single source per gli id). NON rimuove ne aggiunge
provider, NON cambia la shape (i consumer fanno PROVIDERS[x]['env'] / ['default_model']).
"""
from __future__ import annotations

from verimem import llm
from verimem import provider_registry as pr


def test_inline_default_models_match_registry_for_common_providers():
    mismatches = []
    for name, spec in pr.PROVIDERS_BY_NAME.items():
        if name in llm.PROVIDERS and spec.default_model:
            inline_dm = llm.PROVIDERS[name].get("default_model")
            if inline_dm != spec.default_model:
                mismatches.append((name, inline_dm, spec.default_model))
    assert not mismatches, (
        f"default_model inline divergenti dal registry (motore usa id obsoleti): "
        f"{mismatches}"
    )


def test_shape_preserved():
    # i consumer fanno PROVIDERS[x]["env"] / ["default_model"] — shape legacy intatta
    for name in ("openai", "deepseek", "gemini"):
        assert "env" in llm.PROVIDERS[name]
        assert "default_model" in llm.PROVIDERS[name]


def test_no_provider_lost_or_added():
    # il fix NON deve cambiare l'insieme dei provider del motore (33 inline)
    assert len(llm.PROVIDERS) >= 30
    # i provider only-inline (non in yaml) restano
    assert "nvidia" in llm.PROVIDERS and "cerebras" in llm.PROVIDERS
