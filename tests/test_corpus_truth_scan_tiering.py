"""The real-corpus truth scan must judge KNOWLEDGE only by default.

Night-2 finding: with only the test-tier excluded, the scan's residual NLI
conflicts were telemetry near-duplicates (bus/consensus verdicts, dream/*/state,
metric/event_*) — noise the reconcile judge must not see. The scanner now
selects facts by tier (single source: engram._telemetry_prefixes.classify_tier)
and reports the corpus tier composition so every scan documents what it read.
"""
from __future__ import annotations

from benchmark.corpus_truth_scan_local import _DEFAULT_TIERS, _tier_selection


def test_default_selection_is_knowledge_only() -> None:
    topics = [
        "project/engram/cfg",          # knowledge
        "metric/event_git_commit",     # telemetry
        "dream/abc",                   # telemetry (the missing prefix)
        "dialog/doc1-hippoagent",      # dialog transcript
        "test/canary",                 # test fixture
        "lessons/errors/x",            # knowledge
        None,                          # knowledge (empty topic)
    ]
    sel, comp = _tier_selection(topics, _DEFAULT_TIERS)
    assert sel == [0, 5, 6]
    assert comp == {"knowledge": 3, "telemetry": 2, "dialog": 1, "test": 1}


def test_opt_in_tiers_widen_the_selection() -> None:
    topics = ["project/x", "metric/y", "dialog/doc"]
    sel, _ = _tier_selection(topics, frozenset({"knowledge", "telemetry"}))
    assert sel == [0, 1]


def test_default_tiers_constant() -> None:
    assert _DEFAULT_TIERS == frozenset({"knowledge"})
