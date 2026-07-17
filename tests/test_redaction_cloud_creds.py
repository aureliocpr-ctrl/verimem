"""Audit 2026-06-08 A3: secret redaction is correctly wired on every fact write,
but 8/8 common cloud-credential formats passed through UNREDACTED into the
curated corpus (recalled later as plaintext). This adds anchored, length-bounded
rules for them. Negative cases guard against false positives on normal text /
code (the module's whole point is high-confidence-only redaction).
"""
from __future__ import annotations

import pytest

from verimem.redaction import redact_secrets

_AZURE = ("DefaultEndpointsProtocol=https;AccountName=devstore;AccountKey="
          "Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6QUJDRA==;"
          "EndpointSuffix=core.windows.net")
_GCP_REFRESH = "refresh_token 1//0gABCdefGHIjklMNOpqrSTUvwx0123456789abcdefXYZ"
_SENDGRID = "SG.abcdefghijklmnopqrstuv.wxyzABCDEFGHIJKLMNOPqrstuvwxyz0123456789AB"
_NPM = "npm_abcdefghijklmnopqrstuvwxyz0123456789"  # npm_ + 36
_SLACK_HOOK = ("https://hooks.slack.com/services/T00000000/B11111111/"
               "abcdefghijABCDEFGHIJ0123")
# Assembled from parts so GitHub push-protection doesn't flag the literal as a
# real Twilio SID (it IS the format we redact — that's the point).
_TWILIO = "AC" + ("1234567890abcdef" * 2)  # AC + 32 hex
_PKID = 'private_key_id: "abcdef1234567890abcdef1234567890abcdef12"'

_SECRETS = [
    ("azure", _AZURE, "Zm9vYmFy"),
    ("gcp_refresh", _GCP_REFRESH, "1//0gABCdefGHI"),
    ("sendgrid", _SENDGRID, "wxyzABCDEFGHIJ"),
    ("npm", _NPM, "abcdefghijklmnop"),
    ("slack_hook", _SLACK_HOOK, "abcdefghijABCDEFGHIJ"),
    ("twilio", _TWILIO, "1234567890abcdef"),
    ("private_key_id", _PKID, "abcdef1234567890abcdef"),
]


@pytest.mark.parametrize("label,text,leaked", _SECRETS)
def test_cloud_secret_is_redacted(label, text, leaked):
    out, n = redact_secrets(text)
    assert n >= 1, f"{label}: nothing redacted"
    assert "[REDACTED]" in out, f"{label}: no redaction marker"
    assert leaked not in out, f"{label}: secret body survived: {out!r}"


@pytest.mark.parametrize("clean", [
    "the result of 1//0 raises ZeroDivisionError in python",
    "AccountName=devstore is just a label, not a secret",
    "we use npm to install packages and AC power for the lab",
    "post the update to the slack channel please",
    "normal sentence with no credentials whatsoever",
])
def test_clean_text_not_over_redacted(clean):
    out, n = redact_secrets(clean)
    assert n == 0, f"false positive: {clean!r} -> {out!r}"
    assert out == clean
