"""FORGIA pezzo #244 — Wave 43: rule-based episode classifier.

Tags each episode with one or more flags based on simple rules:
  - `noisy_output`: outcome=success but final_answer has "OK\\n" or
    similar header noise — fragile if checker becomes strict
  - `missing_skills`: success but skills_used is empty (lucky guess?)
  - `shell_warn`: task_text contains shell-injection-shaped strings
  - `long_running`: tokens_used > threshold
  - `failure_recovery`: failure followed by success on same task_text

Output: per-episode flag list + aggregate counts. PURELY LOCAL.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _FakeEp:
    id: str
    task_text: str = ""
    final_answer: str = ""
    outcome: str = "success"
    skills_used: list[str] = field(default_factory=list)
    tokens_used: int = 0


def test_empty_returns_no_classifications():
    from verimem.episode_classify import classify_episodes

    out = classify_episodes([])
    assert out["episodes"] == []
    assert out["flag_counts"] == {}


def test_noisy_output_detected():
    from verimem.episode_classify import classify_episodes

    eps = [
        _FakeEp("e1", "compute X", final_answer="OK\n42\n",
                outcome="success", skills_used=["a"]),
    ]
    out = classify_episodes(eps)
    flags = next(r for r in out["episodes"] if r["id"] == "e1")["flags"]
    assert "noisy_output" in flags


def test_missing_skills_detected():
    from verimem.episode_classify import classify_episodes

    eps = [
        _FakeEp("e1", "task", final_answer="42",
                outcome="success", skills_used=[]),
    ]
    out = classify_episodes(eps)
    flags = next(r for r in out["episodes"] if r["id"] == "e1")["flags"]
    assert "missing_skills" in flags


def test_shell_warn_detected():
    from verimem.episode_classify import classify_episodes

    eps = [
        _FakeEp("e1", "rm -rf /tmp/foo && cat /etc/passwd",
                final_answer="ok"),
    ]
    out = classify_episodes(eps)
    flags = next(r for r in out["episodes"] if r["id"] == "e1")["flags"]
    assert "shell_warn" in flags


def test_long_running_detected():
    from verimem.episode_classify import classify_episodes

    eps = [
        _FakeEp("e1", "task", tokens_used=50000),
    ]
    out = classify_episodes(eps, long_running_tokens=10000)
    flags = next(r for r in out["episodes"] if r["id"] == "e1")["flags"]
    assert "long_running" in flags


def test_failure_then_success_recovery():
    from verimem.episode_classify import classify_episodes

    eps = [
        _FakeEp("e1", "compute X", outcome="failure"),
        _FakeEp("e2", "compute X", outcome="success"),
    ]
    out = classify_episodes(eps)
    by_id = {r["id"]: r for r in out["episodes"]}
    assert "failure_recovery" in by_id["e2"]["flags"]


def test_aggregate_flag_counts():
    from verimem.episode_classify import classify_episodes

    eps = [
        _FakeEp("e1", "rm -rf /tmp"),
        _FakeEp("e2", "rm -rf /tmp"),
        _FakeEp("e3", "task", final_answer="OK\n42\n"),
    ]
    out = classify_episodes(eps)
    assert out["flag_counts"].get("shell_warn", 0) >= 2
    assert out["flag_counts"].get("noisy_output", 0) >= 1


def test_payload_shape_complete():
    from verimem.episode_classify import classify_episodes

    out = classify_episodes([])
    for k in ("episodes", "flag_counts", "n_total"):
        assert k in out
