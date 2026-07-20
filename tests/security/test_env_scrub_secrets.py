"""Sandboxed subprocesses could read this project's own API keys (audit MEDIUM).

The scrub list was a per-vendor PREFIX denylist: AWS_, AZURE_, ANTHROPIC_API_KEY,
OPENAI_API_KEY, GOOGLE_API_KEY, HF_TOKEN, GITHUB_TOKEN, SLACK_TOKEN, NPM_TOKEN,
STRIPE_, TWILIO_. It missed MOONSHOT_, DEEPSEEK_, XAI_, GROQ_, OPENROUTER_,
MISTRAL_ — every provider this project actually switches between, including the
key it was itself using.

A denylist of vendor names structurally lags reality: each new provider is a new
hole until someone remembers to add it. What every vendor DOES do the same way
is name the variable — so scrub by suffix (_API_KEY, _TOKEN, _SECRET,
_PASSWORD…) and the next provider is covered before it exists.
"""
from __future__ import annotations

from verimem.sandbox import SandboxPolicy, _scrub_env

SECRETS = {
    "MOONSHOT_API_KEY": "sk-moonshot",
    "DEEPSEEK_API_KEY": "sk-deepseek",
    "XAI_API_KEY": "sk-xai",
    "GROQ_API_KEY": "sk-groq",
    "OPENROUTER_API_KEY": "sk-openrouter",
    "MISTRAL_API_KEY": "sk-mistral",
    "SOMEFUTUREVENDOR_API_KEY": "sk-notyetinvented",
    "INTERNAL_SERVICE_TOKEN": "tok",
    "DB_PASSWORD": "hunter2",
    "SIGNING_SECRET": "shh",
    "CLOUD_ACCESS_KEY": "ak",
}
KEEP = {
    "PATH": "/usr/bin",
    "HOME": "/home/aurelio",
    "PROJECT_NAME": "verimem",
    "LANG": "it_IT.UTF-8",
    "TOKENIZERS_PARALLELISM": "false",   # contains TOKEN but is not a secret
}


def test_every_provider_secret_is_scrubbed():
    out = _scrub_env({**KEEP, **SECRETS}, SandboxPolicy().env_scrub_prefixes)
    leaked = [k for k in SECRETS if k in out]
    assert not leaked, f"secrets readable by the subprocess: {leaked}"


def test_harmless_vars_survive():
    """Narrowness: scrubbing must not blind the subprocess to its environment."""
    out = _scrub_env({**KEEP, **SECRETS}, SandboxPolicy().env_scrub_prefixes)
    for k, v in KEEP.items():
        assert out.get(k) == v, f"{k} was scrubbed but is not a secret"


def test_suffix_rule_applies_even_with_no_prefixes_configured():
    """The early-return on an empty prefix tuple must not skip suffix scrubbing."""
    out = _scrub_env({**KEEP, **SECRETS}, ())
    assert "MOONSHOT_API_KEY" not in out
    assert out.get("PATH") == "/usr/bin"
