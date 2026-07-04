"""Audit#2 2026-06-08 A-1: the assigned_secret rule's leading \\b required a word
boundary immediately before the keyword. In a snake_case key like db_password,
'_' is a \\w char so there is NO boundary -> the keyword never matched and the
secret was stored VERBATIM and recalled into agent context. This is the highest
real-world prevalence (.env / docker-compose / os.environ['DB_PASSWORD']). Fix:
allow an optional snake/kebab prefix segment + capture the full key.
"""
from __future__ import annotations

import pytest

from engram.redaction import redact_secrets

_LEAK = [
    ("db_password=supersecretvalue123", "supersecretvalue123"),
    ("app_secret: 'abcdefghij1234567890'", "abcdefghij1234567890"),
    ("ACCESS_TOKEN=ghijklmnopqr1234567890", "ghijklmnopqr1234567890"),
    ("auth_token=tokabcdefghijklmnop", "tokabcdefghijklmnop"),
    ("user_password=passwordlongenough123", "passwordlongenough123"),
    ("MYAPP_API_KEY=abcdefghijkl1234567890", "abcdefghijkl1234567890"),
    ("service_account_key=keymaterialabcdef123", "keymaterialabcdef123"),
]


@pytest.mark.parametrize("text,leaked", _LEAK)
def test_snake_case_secret_redacted(text, leaked):
    out, n = redact_secrets(text)
    assert n >= 1, f"snake_case secret NOT redacted: {text!r}"
    assert leaked not in out, f"secret survived: {out!r}"


@pytest.mark.parametrize("clean", [
    "the_description=a perfectly normal human readable sentence here",
    "max_retries=5 and batch_size=100 are config values",
    "the session_id is logged for tracing purposes only",
    "random_token_count was 42 in that experiment",  # 'token' not in a key=value
])
def test_snake_case_clean_not_redacted(clean):
    out, n = redact_secrets(clean)
    assert n == 0, f"false positive: {clean!r} -> {out!r}"


def test_bare_keyword_still_redacted():
    # backward-compat: the optional prefix must not break bare keyword=value
    out, n = redact_secrets("api_key=abcdefghijkl1234567890")
    assert n >= 1 and "abcdefghijkl1234567890" not in out
