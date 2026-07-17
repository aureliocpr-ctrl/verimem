"""Air-gap self-verification (verimem.airgap.airgap_status).

For the sovereign / air-gapped enterprise segment: a deployment that must run
with ZERO network egress (local LLM + local embeddings). This pins the verdict
logic derived from the 2026-06-06 LLM leak-audit. Pure over the passed env —
no network, no model load.
"""
from __future__ import annotations

from verimem.airgap import airgap_status


def test_ollama_offline_is_air_gapped():
    env = {"HIPPO_LLM_PROVIDER": "ollama", "HF_HUB_OFFLINE": "1"}
    st = airgap_status(env)
    assert st["air_gapped"] is True, st
    assert st["llm"]["local"] is True
    assert st["embeddings"]["offline_pinned"] is True
    assert st["leaks"] == []


def test_anthropic_cloud_llm_leaks():
    env = {"HIPPO_LLM_PROVIDER": "anthropic", "HF_HUB_OFFLINE": "1"}
    st = airgap_status(env)
    assert st["air_gapped"] is False
    assert st["llm"]["local"] is False
    assert any("egress" in leak.lower() or "cloud" in leak.lower() for leak in st["leaks"])


def test_hosted_mode_leaks_even_with_local_provider():
    # HIPPO_HOSTED routes consolidate/run to the host LLM (cloud) — breaks air-gap.
    env = {"HIPPO_LLM_PROVIDER": "ollama", "HF_HUB_OFFLINE": "1", "HIPPO_HOSTED": "1"}
    st = airgap_status(env)
    assert st["air_gapped"] is False
    assert st["hosted_mode"] is True
    assert any("HIPPO_HOSTED" in leak for leak in st["leaks"])


def test_openai_compatible_local_endpoint_is_local():
    # vLLM / LM Studio / llama.cpp exposed on localhost.
    env = {
        "HIPPO_LLM_PROVIDER": "openai",
        "OPENAI_BASE_URL": "http://localhost:8000/v1",
        "TRANSFORMERS_OFFLINE": "1",
    }
    st = airgap_status(env)
    assert st["llm"]["local"] is True, st["llm"]
    assert st["air_gapped"] is True


def test_openai_cloud_base_url_is_not_local():
    env = {
        "HIPPO_LLM_PROVIDER": "openai",
        "OPENAI_BASE_URL": "https://api.openai.com/v1",
        "HF_HUB_OFFLINE": "1",
    }
    st = airgap_status(env)
    assert st["llm"]["local"] is False
    assert st["air_gapped"] is False


def test_embeddings_not_pinned_offline_is_a_leak():
    env = {"HIPPO_LLM_PROVIDER": "ollama"}  # no offline flag
    st = airgap_status(env)
    assert st["embeddings"]["offline_pinned"] is False
    assert st["air_gapped"] is False
    assert any("offline" in leak.lower() for leak in st["leaks"])


def test_no_provider_is_not_air_gapped():
    # Empty config must NOT claim air-gap (auto-detect may pick cloud/hosted).
    st = airgap_status({})
    assert st["air_gapped"] is False
    assert st["llm"]["local"] is False


# ---- hostname-exact locality (2026-07-15 adversarial-review fix) -----------
# _is_local_base_url used to SUBSTRING-match ("127.0.0.1" in url), so a base_url
# like http://evil-localhost.attacker.com counted as local and airgap_status
# returned a FALSE "air_gapped: true" — a spoofable compliance verdict. Locality
# must be decided on the PARSED hostname; anything ambiguous fails CLOSED
# (non-local → reported as a leak).

def _openai_env(base_url: str) -> dict[str, str]:
    return {"HIPPO_LLM_PROVIDER": "openai", "OPENAI_BASE_URL": base_url,
            "HF_HUB_OFFLINE": "1"}


def test_localhost_lookalike_hostname_is_not_local():
    st = airgap_status(_openai_env("http://evil-localhost.attacker.com/v1"))
    assert st["llm"]["local"] is False, st["llm"]
    assert st["air_gapped"] is False


def test_loopback_ip_prefix_hostname_is_not_local():
    st = airgap_status(_openai_env("http://127.0.0.1.evil.com/v1"))
    assert st["llm"]["local"] is False, st["llm"]
    assert st["air_gapped"] is False


def test_local_tokens_in_path_or_query_are_not_local():
    st = airgap_status(_openai_env("https://api.evil.com/localhost?next=127.0.0.1"))
    assert st["llm"]["local"] is False, st["llm"]
    assert st["air_gapped"] is False


def test_malformed_base_url_fails_closed():
    # Unbalanced IPv6 bracket: unparseable → NON-local (the verdict is a
    # compliance claim; in doubt it must report a leak, never certify).
    st = airgap_status(_openai_env("http://[::1"))
    assert st["llm"]["local"] is False, st["llm"]
    assert st["air_gapped"] is False


def test_schemeless_localhost_is_still_local():
    # Provider configs commonly omit the scheme (ollama-style host:port).
    st = airgap_status(_openai_env("localhost:11434"))
    assert st["llm"]["local"] is True, st["llm"]
    assert st["air_gapped"] is True


def test_ipv6_loopback_with_port_is_local():
    st = airgap_status(_openai_env("http://[::1]:8080/v1"))
    assert st["llm"]["local"] is True, st["llm"]


def test_https_loopback_with_port_is_local():
    st = airgap_status(_openai_env("https://127.0.0.1:8443/v1"))
    assert st["llm"]["local"] is True, st["llm"]


def test_uppercase_localhost_is_local():
    st = airgap_status(_openai_env("http://LOCALHOST:8000/v1"))
    assert st["llm"]["local"] is True, st["llm"]
