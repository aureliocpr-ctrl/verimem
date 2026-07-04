"""R3.1: Calibrated confidence on recall results.

Given a recall list (with similarities), assess if HippoAgent
*actually knows* the answer or is bluffing. Returns one of:
  - "high": clear match (max sim ≥0.7 AND ≥3 high-sim concordant)
  - "medium": decent match (max sim ≥0.5)
  - "low": weak match (max sim ≥0.3)
  - "none": no relevant memory (max sim <0.3 or empty)

Used to trigger fallback behavior (ask user, search externally).
"""
from __future__ import annotations


def _r(sim, outcome="success", task="t"):
    return {"similarity": sim, "outcome": outcome, "task": task}


def test_empty_recall_returns_none():
    from engram.metacognition import assess_recall_confidence

    out = assess_recall_confidence([])
    assert out["level"] == "none"
    assert out["score"] == 0.0


def test_high_confidence():
    from engram.metacognition import assess_recall_confidence

    # 3 concordant high-sim episodes
    out = assess_recall_confidence([
        _r(0.85, outcome="success"),
        _r(0.80, outcome="success"),
        _r(0.75, outcome="success"),
    ])
    assert out["level"] == "high"


def test_medium_confidence():
    from engram.metacognition import assess_recall_confidence

    out = assess_recall_confidence([
        _r(0.60, outcome="success"),
        _r(0.55, outcome="success"),
    ])
    assert out["level"] == "medium"


def test_low_confidence():
    from engram.metacognition import assess_recall_confidence

    out = assess_recall_confidence([
        _r(0.35, outcome="success"),
    ])
    assert out["level"] == "low"


def test_none_when_sim_too_low():
    from engram.metacognition import assess_recall_confidence

    out = assess_recall_confidence([
        _r(0.15, outcome="success"),
        _r(0.10, outcome="success"),
    ])
    assert out["level"] == "none"


def test_high_requires_outcome_agreement():
    """If top results disagree on outcome, downgrade confidence."""
    from engram.metacognition import assess_recall_confidence

    # high sim but outcome split → not 'high'
    out = assess_recall_confidence([
        _r(0.85, outcome="success"),
        _r(0.80, outcome="failure"),
        _r(0.75, outcome="failure"),
    ])
    # 1 success vs 2 failures — outcome agreement is low
    # confidence should downgrade
    assert out["level"] in {"medium", "low"}


def test_fallback_message_when_none():
    from engram.metacognition import assess_recall_confidence

    out = assess_recall_confidence([])
    assert "fallback_suggestion" in out
    assert out["fallback_suggestion"]  # non-empty


def test_payload_keys():
    from engram.metacognition import assess_recall_confidence
    out = assess_recall_confidence([_r(0.5)])
    for k in ("level", "score", "max_similarity", "n_episodes",
              "outcome_agreement", "fallback_suggestion"):
        assert k in out


def test_score_is_normalized_0_1():
    from engram.metacognition import assess_recall_confidence
    out = assess_recall_confidence([_r(0.85, outcome="success")])
    assert 0.0 <= out["score"] <= 1.0
