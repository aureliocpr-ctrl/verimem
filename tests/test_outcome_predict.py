"""FORGIA pezzo #252 — Wave 51: rule-based outcome prediction.

Before executing a task, estimate the probability of success based
on similar past episodes (Jaccard on task_text tokens). Helps the
agent decide whether to ask for confirmation or try a different
approach.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _FakeEp:
    task_text: str = ""
    outcome: str = "success"


def test_no_history_uncertain():
    from verimem.outcome_predict import predict_outcome

    out = predict_outcome(task="anything", episodes=[])
    assert out["n_similar"] == 0
    # No data → uncertainty.
    assert out["confidence"] == 0.0


def test_all_success_predicts_success():
    from verimem.outcome_predict import predict_outcome

    eps = [
        _FakeEp("compute sum of digits", "success"),
        _FakeEp("compute sum of digits", "success"),
        _FakeEp("compute sum of digits 42", "success"),
    ]
    out = predict_outcome(
        task="compute sum of digits 99",
        episodes=eps, threshold=0.3,
    )
    # With Laplace smoothing (+1,+1) and 3 successes, p_success
    # is (3+1)/(3+0+2) = 0.80. Tolerable threshold = 0.75.
    assert out["p_success"] >= 0.75
    assert out["p_failure"] <= 0.25


def test_all_failure_predicts_failure():
    from verimem.outcome_predict import predict_outcome

    eps = [
        _FakeEp("apply rot3 reverse rot3", "failure"),
        _FakeEp("apply rot3 reverse rot3", "failure"),
    ]
    out = predict_outcome(
        task="apply rot3 reverse rot3",
        episodes=eps, threshold=0.3,
    )
    # Laplace +1,+1: 2 failures → (0+1)/(0+2+2) = 0.25 p_succ,
    # 0.75 p_fail. Threshold relaxed to 0.7.
    assert out["p_failure"] >= 0.7


def test_mixed_outcome():
    from verimem.outcome_predict import predict_outcome

    eps = [
        _FakeEp("count words in text", "success"),
        _FakeEp("count words in text", "success"),
        _FakeEp("count words in text", "failure"),
    ]
    out = predict_outcome(
        task="count words in text",
        episodes=eps, threshold=0.3,
    )
    # 2 success, 1 failure → p_success ~0.66.
    assert 0.5 < out["p_success"] < 0.8


def test_dissimilar_task_low_confidence():
    from verimem.outcome_predict import predict_outcome

    eps = [_FakeEp("completely different topic", "success")]
    out = predict_outcome(
        task="totally unrelated query xyz",
        episodes=eps, threshold=0.5,
    )
    # Should return very few similar.
    assert out["n_similar"] == 0


def test_returns_similar_episodes():
    from verimem.outcome_predict import predict_outcome

    eps = [
        _FakeEp("apple banana cherry", "success"),
        _FakeEp("apple banana", "failure"),
    ]
    out = predict_outcome(
        task="apple banana", episodes=eps,
        threshold=0.3, top_k=5,
    )
    assert len(out["similar_episodes"]) >= 1


def test_payload_shape_complete():
    from verimem.outcome_predict import predict_outcome

    out = predict_outcome(task="x", episodes=[])
    for k in ("task", "n_similar", "p_success", "p_failure",
                "confidence", "similar_episodes"):
        assert k in out
