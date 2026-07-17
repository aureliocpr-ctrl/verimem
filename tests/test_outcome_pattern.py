"""R42: Find tokens correlated with success/failure.

For each token in task_text, compute success_rate when present.
Tokens with high rate = positive signals. Low rate = warning signals.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str


def test_empty_returns_empty():
    from verimem.outcome_pattern import find_outcome_patterns
    out = find_outcome_patterns([])
    assert out["positive_signals"] == []
    assert out["negative_signals"] == []


def test_positive_token_high_rate():
    from verimem.outcome_pattern import find_outcome_patterns
    eps = (
        [_Ep(f"s{i}", "passive recon", "success") for i in range(5)]
        + [_Ep(f"f{i}", "aggressive scan", "failure") for i in range(5)]
    )
    out = find_outcome_patterns(eps, min_occurrence=2)
    pos_tokens = [t["token"] for t in out["positive_signals"]]
    assert "passive" in pos_tokens or "recon" in pos_tokens


def test_negative_token_low_rate():
    from verimem.outcome_pattern import find_outcome_patterns
    eps = (
        [_Ep(f"s{i}", "passive recon", "success") for i in range(5)]
        + [_Ep(f"f{i}", "aggressive scan", "failure") for i in range(5)]
    )
    out = find_outcome_patterns(eps, min_occurrence=2)
    neg_tokens = [t["token"] for t in out["negative_signals"]]
    assert "aggressive" in neg_tokens or "scan" in neg_tokens


def test_min_occurrence_filter():
    from verimem.outcome_pattern import find_outcome_patterns
    eps = [_Ep("e1", "rare task", "success")]
    out = find_outcome_patterns(eps, min_occurrence=5)
    assert out["positive_signals"] == []


def test_payload_shape():
    from verimem.outcome_pattern import find_outcome_patterns
    out = find_outcome_patterns([])
    for k in ("positive_signals", "negative_signals", "n_episodes_scanned"):
        assert k in out


def test_entry_keys():
    from verimem.outcome_pattern import find_outcome_patterns
    eps = [_Ep(f"s{i}", "X", "success") for i in range(3)]
    out = find_outcome_patterns(eps, min_occurrence=2)
    if out["positive_signals"]:
        for k in ("token", "n_occurrences", "success_rate"):
            assert k in out["positive_signals"][0]
