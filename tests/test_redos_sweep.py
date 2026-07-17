"""Permanent ReDoS guard for the write-path regex surface.

After the _DEV_CONTEXT O(n^2) blow-up (fixed 2026-07-17, found by the gateway
load probe), this sweeps EVERY user-input regex scanner in the write path with
adversarial strings (long no-space, near-match repeats, email/url-ish, all
digits, many words) and asserts each stays well under a second. A future regex
edit that reintroduces catastrophic backtracking fails here instead of in
production.

Generous 1.5s ceiling (measured worst is ~180ms) so it flags the O(n^2) class
without flaking on a busy CI box.
"""
from __future__ import annotations

import time

import pytest

_ADVERSARIAL = {
    "no_space_64k": "x" * 65536,
    "near_name_attr_line": ("a" * 100 + "." + "b" * 100 + ":") * 300,
    "email_ish_32k": "user@host" * 4000,
    "url_ish_32k": "http://a.b/" * 3000,
    "many_words_64k": "a " * 32768,
    "all_digits_64k": "1" * 65536,
}


def _scanners():
    from verimem.admission_gate import classify_admission
    from verimem.anti_confab_gate import (
        _has_dev_context,
        _has_personal_context,
        run_validation_gate,
    )
    from verimem.prompt_injection import detect_injection
    from verimem.redaction import redact_secrets
    return [
        ("redact_secrets", lambda s: redact_secrets(s)),
        ("detect_injection", lambda s: detect_injection(s)),
        ("classify_admission",
         lambda s: classify_admission(topic="t", proposition=s)),
        ("_has_dev_context", lambda s: _has_dev_context(s)),
        ("_has_personal_context", lambda s: _has_personal_context(s)),
        ("gate_fast",
         lambda s: run_validation_gate(proposition=s, verified_by=None,
                                       topic="t", agent=None, validate="fast")),
    ]


@pytest.mark.parametrize("adv_name", list(_ADVERSARIAL))
def test_write_path_regex_no_redos(adv_name):
    s = _ADVERSARIAL[adv_name]
    for name, fn in _scanners():
        t = time.perf_counter()
        fn(s)
        dt = time.perf_counter() - t
        assert dt < 1.5, f"{name} O(n^2) on {adv_name}: {dt:.2f}s"
