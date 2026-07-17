"""Characterization tests for l1_evidence.ref_is_negated (F2 gap).

Shared guard for the L1.x detectors: a ref whose payload says NOT-yet-done
("approval:pending", "cron:someday") must not count as evidence of a completed
claim. Centralizing it fixed a bare-prefix hole (audit#3 2026-06-09); F2 pins
the behavior so the hole cannot silently reopen — and guards the deliberate
non-negating words (active/open/scheduled) that appear in REAL evidence.
"""
from __future__ import annotations

import pytest

from verimem.l1_evidence import NEGATING_TOKENS, ref_is_negated


@pytest.mark.parametrize("ref", [
    "approval:pending", "alert:planned", "cron:someday", "task:todo",
    "feature:wip", "doc:draft", "fix:proposed", "deploy:manual",
    "audit:requested", "plan:backlog", "later", "TBD",
])
def test_not_done_refs_are_negated(ref):
    assert ref_is_negated(ref)


@pytest.mark.parametrize("ref", [
    # deliberately NOT negating — legitimately present in real evidence
    "prometheus:rule_active", "alert:open", "cron:scheduled",
    "opentelemetry:span", "pytest:test_x passed", "bench:p95",
    "commit:abc123", "",
])
def test_real_evidence_is_not_negated(ref):
    assert not ref_is_negated(ref)


def test_per_token_not_substring():
    # 'wip' negates as a token, but must not match inside 'wiper' or 'swipe'
    assert ref_is_negated("branch:wip")
    assert not ref_is_negated("module:wiper_config")
    assert not ref_is_negated("gesture:swipe_handler")


def test_non_string_is_safe():
    assert ref_is_negated(None) is False
    assert ref_is_negated(123) is False


def test_tokens_set_is_lowercase_and_nonempty():
    assert NEGATING_TOKENS and all(t == t.lower() for t in NEGATING_TOKENS)
