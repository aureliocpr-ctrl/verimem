"""R17: Episode diff — compare two arbitrary episodes side-by-side.

Different from trajectory_diff (which compares step-by-step traces),
this compares episodes at the metadata level: task, outcome,
skills_used, tokens, time.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str
    skills_used: list = field(default_factory=list)
    tokens_used: int = 0
    num_steps: int = 1


def test_identical_episodes_no_diff():
    from engram.episode_diff import episode_diff

    a = _Ep("e1", "task X", "success", skills_used=["s1"], tokens_used=100)
    b = _Ep("e2", "task X", "success", skills_used=["s1"], tokens_used=100)
    out = episode_diff(a, b)
    # Same content → diffs minimal (only ids)
    assert "id" in out["diff_fields"]


def test_outcome_diff():
    from engram.episode_diff import episode_diff

    a = _Ep("a", "task", "success")
    b = _Ep("b", "task", "failure")
    out = episode_diff(a, b)
    assert "outcome" in out["diff_fields"]


def test_skills_used_diff():
    from engram.episode_diff import episode_diff

    a = _Ep("a", "x", "success", skills_used=["s1", "s2"])
    b = _Ep("b", "x", "success", skills_used=["s1", "s3"])
    out = episode_diff(a, b)
    assert "skills_used" in out["diff_fields"]


def test_token_diff():
    from engram.episode_diff import episode_diff

    a = _Ep("a", "x", "success", tokens_used=100)
    b = _Ep("b", "x", "success", tokens_used=500)
    out = episode_diff(a, b)
    assert "tokens_used" in out["diff_fields"]


def test_payload_keys():
    from engram.episode_diff import episode_diff
    a = _Ep("a", "x", "success")
    b = _Ep("b", "y", "failure")
    out = episode_diff(a, b)
    for k in ("diff_fields", "summary", "a", "b"):
        assert k in out


def test_summary_string():
    from engram.episode_diff import episode_diff
    a = _Ep("a", "x", "success")
    b = _Ep("b", "y", "failure")
    out = episode_diff(a, b)
    assert len(out["summary"]) > 0
