"""Fase-C audit mod.12 — redaction.py (secret scrubbing, security-critical).

Empirical sweep 2026-07-17 found two real FALSE NEGATIVES (secrets stored in
the clear):

M12-1 (MED, secret leak): a Hugging Face token (``hf_…``) matched no rule —
anyone ingesting a conversation that pastes an HF token persisted it verbatim.

M12-2 (MED, secret leak): the ``assigned_secret`` key gate allowed only ONE
optional prefix segment (``(?:[a-z0-9]+[_-])?``), so a MULTI-segment key —
``MY_SECRET_TOKEN=…``, ``APP_DB_PASSWORD=…``, ``SERVICE_ACCOUNT_API_KEY=…`` —
never matched and its value leaked. Real env-var names are routinely
multi-segment.

The fix must not open a ReDoS hole (the module's stated invariant) and must
keep every existing pattern working.
"""
from __future__ import annotations

import time

from engram.redaction import redact_secrets

_REDACT = "[REDACTED]"


def _tok(prefix: str, body: str) -> str:
    """Build a fake secret at RUNTIME so no literal token string sits in the
    file — GitHub push-protection flags a literal ``hf_…`` even in a test."""
    return prefix + body


def test_hf_token_is_redacted():
    fake = _tok("hf_", "abcdefghijklmnopqrstuvwxyzABCDEFGH")  # hf_ + 34 chars
    out, n = redact_secrets(f"here is my key {fake} ok")
    assert n == 1
    assert fake not in out
    assert _REDACT in out


def test_multi_segment_secret_keys_are_redacted():
    for raw, leaked in [
        ("MY_SECRET_TOKEN=abc123XYZ789def456", "abc123XYZ789def456"),
        ("APP_DB_PASSWORD = 'hunter2horse!'", "hunter2horse"),
        ("SERVICE_ACCOUNT_API_KEY: sd8f7s9d8f7s9d8f", "sd8f7s9d8f7s9d8f"),
    ]:
        out, n = redact_secrets(raw)
        assert n >= 1, f"not redacted: {raw}"
        assert leaked not in out, f"secret leaked: {out}"


def test_arbitrarily_long_prefix_keys_are_redacted():
    # critic mod.12b (counterexample 12f46e5e): the {0,6} bound just MOVED the
    # false negative to 7+ segments — a plausible enterprise env-var name still
    # leaked. The fix must eliminate the CLASS, not cap it.
    for raw, leaked in [
        ("MY_APP_STAGING_EU_WEST_PAYMENT_SERVICE_API_KEY=Xy9kLm2pQr7tWv3zAAA",
         "Xy9kLm2pQr7tWv3zAAA"),
        ("A_B_C_D_E_F_G_H_I_J_K_L_TOKEN=Xy9kLm2pQr7tWv3zAAA",
         "Xy9kLm2pQr7tWv3zAAA"),
    ]:
        out, n = redact_secrets(raw)
        assert n >= 1, f"long-prefix key not redacted: {raw}"
        assert leaked not in out, f"secret leaked: {out}"


def test_single_segment_and_bare_keys_still_work():
    # non-regression on the existing behaviour
    for raw in ["api_key=abcdefghij1234567890",
                "password: 'super secret value'",
                "access_token = tok_abcdefghijklmnop"]:
        _, n = redact_secrets(raw)
        assert n >= 1, raw


def test_no_false_positive_on_prose():
    # ordinary sentences with the trigger words but no assignment must survive
    for raw in ["The secret to good pasta is salt.",
                "My token of appreciation for the team.",
                "We discussed the password policy at length today."]:
        out, n = redact_secrets(raw)
        assert n == 0, f"false positive: {raw} -> {out}"
        assert out == raw


def test_no_redos_on_adversarial_prefix():
    # the multi-segment prefix must stay linear: a long a_a_a_… run with NO
    # terminating keyword must return fast, not hang (ReDoS invariant).
    for evil in [("a_" * 5000) + "= " + ("x" * 20),
                 ("a_" * 5000) + "token= " + ("x" * 20),
                 ("x" * 10000) + "secret=" + ("y" * 20)]:
        t0 = time.perf_counter()
        redact_secrets(evil)
        assert time.perf_counter() - t0 < 1.0, "possible catastrophic backtracking"


def test_idempotent_on_cleaned_text():
    s = "SERVICE_ACCOUNT_API_KEY=abcdefghij1234567890"
    o1, _ = redact_secrets(s)
    o2, _ = redact_secrets(o1)
    assert o1 == o2       # text stable once cleaned
    assert "abcdefghij1234567890" not in o1
