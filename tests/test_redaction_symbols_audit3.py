"""audit#3-r3 (2026-06-09): the catch-all assigned_secret rule masked the value
with a charclass [A-Za-z0-9._/+=~-]{12,} that EXCLUDES common credential symbols
(@ $ ! : space). Any such char in the first chars of the value dropped the run
below the floor -> the whole secret was stored VERBATIM (R1). Quoted multi-word
secrets (passphrases) leaked too (R9). Fix widens the value to a quote-span or a
whitespace-terminated run; the key-name gate prevents false positives.
"""
from __future__ import annotations

import pytest

from verimem.redaction import redact_secrets


@pytest.mark.parametrize("text", [
    'password = "p@ssw0rd123456"',
    'db_password=p@ssw0rd1234567',
    'api_key: aB3$xY7kLmNoPqRsT99',
    'client_secret=Gx2!aB3cD4eF5gH6jK7',
    'pwd=My$ecretP@ssw0rd!!',
    'auth_token: tok#en:with:colons:1234',
    'password = "correct horse battery staple"',  # R9 quoted multi-word
])
def test_secrets_with_symbols_or_spaces_are_redacted(text):
    out, n = redact_secrets(text)
    assert n >= 1, f"secret leaked unredacted: {text!r} -> {out!r}"
    for leak in ("p@ssw0rd", "aB3$xY7", "Gx2!aB3", "My$ecret",
                 "correct horse battery", "tok#en:with"):
        assert leak not in out, f"raw secret survived: {out!r}"


@pytest.mark.parametrize("text", [
    "version = 1.2.3",
    "the password policy requires rotation every 90 days",
    "status = ok",
    "retries: 5",
])
def test_non_secret_assignments_not_redacted(text):
    out, n = redact_secrets(text)
    assert n == 0, f"false positive on {text!r} -> {out!r}"
