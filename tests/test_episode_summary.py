"""FORGIA pezzo #246 — Wave 45: episode TL;DR renderer.

Compact human-readable summary of an episode. Useful when listing
many episodes in a UI without cluttering with raw fields.

Format: `[outcome] task_text (N skills, T tokens, MM-DD)`
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class _FakeEp:
    id: str = ""
    task_text: str = ""
    final_answer: str = ""
    outcome: str = "success"
    skills_used: list[str] = field(default_factory=list)
    tokens_used: int = 0
    created_at: float = 0.0


def test_returns_string():
    from verimem.episode_summary import summarize_episode

    out = summarize_episode(_FakeEp())
    assert isinstance(out, str)


def test_includes_outcome_marker():
    from verimem.episode_summary import summarize_episode

    success = summarize_episode(_FakeEp(outcome="success"))
    failure = summarize_episode(_FakeEp(outcome="failure"))
    # Outcome should be visible somehow.
    assert ("✓" in success or "success" in success.lower())
    assert ("✗" in failure or "failure" in failure.lower())


def test_includes_task_text():
    from verimem.episode_summary import summarize_episode

    ep = _FakeEp(task_text="compute the sum of digits")
    out = summarize_episode(ep)
    assert "compute" in out or "sum" in out


def test_truncates_long_task():
    from verimem.episode_summary import summarize_episode

    long_task = "x" * 500
    out = summarize_episode(_FakeEp(task_text=long_task))
    # Truncated to a reasonable display length.
    assert len(out) < 250


def test_handles_missing_fields():
    from verimem.episode_summary import summarize_episode

    out = summarize_episode(_FakeEp())
    # No crash, returns something.
    assert isinstance(out, str)
    assert len(out) > 0


def test_shows_skills_count():
    from verimem.episode_summary import summarize_episode

    ep = _FakeEp(skills_used=["a", "b", "c"])
    out = summarize_episode(ep)
    assert "3" in out


def test_shows_date_when_timestamp_present():
    from verimem.episode_summary import summarize_episode

    ep = _FakeEp(created_at=time.time())
    out = summarize_episode(ep)
    # Should include some date marker (YYYY-MM-DD prefix).
    import re
    assert re.search(r"\d{4}-\d{2}-\d{2}", out) is not None


def test_summarize_episodes_batch():
    """Convenience batch helper."""
    from verimem.episode_summary import summarize_episodes

    eps = [_FakeEp(id="e1"), _FakeEp(id="e2")]
    out = summarize_episodes(eps)
    assert len(out) == 2
    assert all(isinstance(s, str) for s in out)
