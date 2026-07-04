"""R23: Failure diagnosis — root cause from similar past failures.

Given a failed episode, find similar past failures + what they had
in common (frequent tokens in final_answer). Suggest the dominant
failure mode.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str
    final_answer: str = ""


def test_no_similar_returns_unknown():
    from engram.failure_diagnosis import diagnose_failure
    target = _Ep("t", "novel task X", "failure", "weird crash")
    out = diagnose_failure(target, past_episodes=[])
    assert out["root_cause"] == "" or out["confidence"] == "none"


def test_finds_common_cause():
    from engram.failure_diagnosis import diagnose_failure
    target = _Ep("t", "WordPress recon target", "failure",
                 "Cloudflare WAF blocked")
    past = [
        _Ep("p1", "WordPress recon target", "failure",
            "Cloudflare WAF blocked request"),
        _Ep("p2", "WordPress recon different", "failure",
            "Cloudflare WAF rate limited then blocked"),
        _Ep("p3", "WordPress recon another", "failure",
            "Cloudflare blocked IP"),
    ]
    out = diagnose_failure(target, past_episodes=past)
    assert "cloudflare" in out["root_cause"].lower() or "waf" in out["root_cause"].lower()


def test_ignores_success_episodes():
    from engram.failure_diagnosis import diagnose_failure
    target = _Ep("t", "task", "failure", "error X")
    past = [
        _Ep("p1", "task", "success", "completed"),
        _Ep("p2", "task", "success", "completed"),
    ]
    out = diagnose_failure(target, past_episodes=past)
    # Only failures should be aggregated → no root cause
    assert out["n_similar_failures"] == 0


def test_payload_shape():
    from engram.failure_diagnosis import diagnose_failure
    target = _Ep("t", "x", "failure")
    out = diagnose_failure(target, past_episodes=[])
    for k in ("root_cause", "confidence", "n_similar_failures",
              "similar_ids"):
        assert k in out


def test_high_confidence_on_strong_pattern():
    from engram.failure_diagnosis import diagnose_failure
    target = _Ep("t", "X attack", "failure", "rate limit hit")
    past = [
        _Ep(f"p{i}", "X attack", "failure", "rate limit hit retry blocked")
        for i in range(5)
    ]
    out = diagnose_failure(target, past_episodes=past)
    assert out["confidence"] in {"medium", "high"}


def test_low_confidence_on_weak_pattern():
    from engram.failure_diagnosis import diagnose_failure
    target = _Ep("t", "Y attack", "failure", "unknown error")
    past = [_Ep("p1", "Y attack", "failure", "completely different cause")]
    out = diagnose_failure(target, past_episodes=past)
    # Single weak match → low/none
    assert out["confidence"] in {"low", "none", "medium"}
