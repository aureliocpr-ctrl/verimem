"""audit#3-r3 R7: the operator-overridable provider ``base_url``
(``UserSettings.base_url`` -> ``OpenAICompatLLM``) reached the HTTP client with
no host validation.

Both the save (``/api/settings``) and the provider-test (``/api/settings/test``)
endpoints are authenticated, so this is operator-scoped defense-in-depth rather
than an open SSRF. But a ``base_url`` pointing at a cloud-metadata /
link-local endpoint is NEVER a legitimate LLM provider and is the classic SSRF
credential-theft target, so we block exactly those while leaving localhost /
private-LAN / public endpoints (legit self-hosted / Ollama / Azure) untouched.

NARROW by design: literal metadata IPs + link-local + known metadata hostnames.
Hostnames are NOT DNS-resolved, so this is not a DNS-rebind defense —
proportionate to a single-user authenticated tool.
"""
from __future__ import annotations

import pytest

from verimem.llm import LLMError, _is_blocked_host


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://metadata.goog/computeMetadata/v1/",
        "http://100.100.100.200/latest/meta-data/",   # Alibaba Cloud
        "http://[fd00:ec2::254]/latest/meta-data/",    # AWS IMDS over IPv6
        "http://[fe80::1]/v1",                          # IPv6 link-local
    ],
)
def test_blocks_cloud_metadata_endpoints(url):
    assert _is_blocked_host(url) is True, url


@pytest.mark.parametrize(
    "url",
    [
        "https://api.openai.com/v1",
        "https://openrouter.ai/api/v1",
        "https://my-host.openai.azure.com/",
        "http://127.0.0.1:11434/v1",     # localhost Ollama (legit)
        "http://localhost:8000/v1",      # localhost self-hosted (legit)
        "http://192.168.1.50:8000/v1",   # private LAN self-hosted (legit)
        "http://10.0.0.5:8080/v1",       # private LAN (legit)
    ],
)
def test_allows_legit_endpoints(url):
    assert _is_blocked_host(url) is False, url


def test_openai_compat_client_rejects_metadata_base_url():
    # The guard must fire BEFORE the openai client is constructed (so it does
    # not even depend on the openai package being importable).
    from verimem.llm import OpenAICompatLLM

    with pytest.raises(LLMError):
        OpenAICompatLLM(
            api_key="sk-test",
            base_url="http://169.254.169.254/v1",
            default_model="m",
        )
