"""The write gate must not blow up on a large fact (found by the gateway load
probe, 2026-07-17): a single 64KB no-word-break write took 23.8s — 22.65s of it
in ONE `re.search` inside `_has_dev_context`, whose `_DEV_CONTEXT` pattern
(`\\w+\\.\\w+:\\d+` and friends) backtracks catastrophically O(n^2) on a long
run without spaces. It runs on EVERY write, so a large paste = a DoS + a
tens-of-seconds hang. The lexical L1 scan is capped to a bounded prefix (a
dev/personal/historical SIGNAL in a real fact is near the start; a 64KB blob is
a document — README routes those to DocumentIndex).

Perf assertions use a generous ceiling (100x headroom over the fixed behaviour)
so they flag the O(n^2) regression without being flaky on a busy CI box.
"""
from __future__ import annotations

import time

from verimem.anti_confab_gate import (
    _has_dev_context,
    _has_personal_context,
    _is_historical_completion,
    run_validation_gate,
)


def test_has_dev_context_is_fast_on_huge_input():
    blob = "x" * 65536
    t = time.perf_counter()
    assert _has_dev_context(blob) is False
    assert (time.perf_counter() - t) < 1.0, "dev-context regex is O(n^2) again"


def test_all_escalation_helpers_fast_on_huge_input():
    blob = "y" * 131072  # 128KB — would be minutes with the old backtracking
    for fn in (_has_dev_context, _has_personal_context, _is_historical_completion):
        t = time.perf_counter()
        fn(blob)
        assert (time.perf_counter() - t) < 1.0, f"{fn.__name__} O(n^2) on 128KB"


def test_full_gate_fast_on_huge_input():
    blob = "z" * 65536
    t = time.perf_counter()
    run_validation_gate(proposition=blob, verified_by=None, topic="x",
                        agent=None, validate="fast")
    assert (time.perf_counter() - t) < 2.0, "the write gate hangs on a large fact"


def test_dev_context_detection_unchanged_on_normal_text():
    # behavior preserved for real (short) inputs — the cap is far beyond any fact
    assert _has_dev_context("fixed the bug in commit abc1234") is True
    assert _has_dev_context("deployed the auth service to production") is True
    assert _has_dev_context("Alice moved to Berlin in March") is False
    assert _has_personal_context("my dentist appointment is on Monday") is True
