"""Cycle #68 — Deterministic self_model refresh (no LLM).

The refresh updates ONLY fields that can be derived without natural-
language reasoning:
  - `active_projects` from topic prefix frequency in last N episodes
  - `recent_focus`   from the title of the latest episode

Preserves (does NOT auto-rewrite) the fields that require interpretation:
  - current_goals, open_decisions, collab_style, notes

Pure-Python logic. No SQLite mocking required for these tests: we pass
synthetic episode dicts and a synthetic "current model" dict directly to
`propose_refresh()`.
"""
from __future__ import annotations

import pytest

from engram.self_model_refresh import propose_refresh


def _ep(eid: str, task: str, topic_hint: str | None = None,
        created_at: float = 1_000_000.0) -> dict:
    """Helper: build a fake episode dict that mimics what
    Agent.memory.last_episodes() returns."""
    return {
        "id": eid,
        "task_text": task,
        "outcome": "success",
        "created_at": created_at,
        "topic_hint": topic_hint,  # optional carrier
    }


def test_extracts_active_projects_from_topic_frequency():
    """Top-K topic prefixes (second segment) become active_projects."""
    episodes = [
        _ep("e1", "task1", topic_hint="project/engram/cycle-67"),
        _ep("e2", "task2", topic_hint="project/engram/cycle-66"),
        _ep("e3", "task3", topic_hint="project/nexus/setup"),
        _ep("e4", "task4", topic_hint="project/nexus/run"),
        _ep("e5", "task5", topic_hint="project/beacon/philosophy"),
        _ep("e6", "task6", topic_hint="lessons/hippoagent-development"),
    ]
    current = {
        "current_goals": ["keep this"],
        "open_decisions": ["keep me"],
        "active_projects": ["stale_project"],
        "collab_style": "italian, brevity",
        "recent_focus": "old focus",
        "notes": "preserve",
    }
    proposed = propose_refresh(
        current=current, episodes=episodes, top_k_projects=5,
    )
    # active_projects derived from topic prefix
    assert "engram" in proposed["active_projects"]
    assert "nexus" in proposed["active_projects"]
    assert "beacon" in proposed["active_projects"]
    # stale_project should be replaced, not merged
    assert "stale_project" not in proposed["active_projects"]


def test_recent_focus_set_to_latest_episode_task():
    """recent_focus becomes the task_text of the most recent episode."""
    episodes = [
        _ep("e1", "vecchio task", created_at=100.0),
        _ep("e2", "NUOVO TASK più recente", created_at=200.0),
    ]
    current = {"recent_focus": "obsoleto"}
    proposed = propose_refresh(current=current, episodes=episodes)
    assert "NUOVO TASK" in proposed["recent_focus"]


def test_preserves_immutable_fields():
    """Fields that require interpretation are NOT auto-rewritten."""
    current = {
        "current_goals": ["specific goal A", "specific goal B"],
        "open_decisions": ["decisione X"],
        "active_projects": ["old"],
        "collab_style": "italian, brevity, CEO mode",
        "recent_focus": "old",
        "notes": "important note preserved",
    }
    episodes = [_ep("e1", "new task", topic_hint="project/x/y")]
    proposed = propose_refresh(current=current, episodes=episodes)
    # Preserved verbatim
    assert proposed["current_goals"] == current["current_goals"]
    assert proposed["open_decisions"] == current["open_decisions"]
    assert proposed["collab_style"] == current["collab_style"]
    assert proposed["notes"] == current["notes"]
    # Auto-updated
    assert proposed["recent_focus"] != "old"
    assert "x" in proposed["active_projects"]


def test_handles_empty_episodes_gracefully():
    """No episodes → return current unchanged (no fake data)."""
    current = {
        "current_goals": [], "open_decisions": [],
        "active_projects": ["a", "b"], "collab_style": "x",
        "recent_focus": "y", "notes": "z",
    }
    proposed = propose_refresh(current=current, episodes=[])
    assert proposed == current


def test_handles_missing_current_gracefully():
    """If there is no current self_model yet, build from episodes only."""
    episodes = [
        _ep("e1", "ultimo task fatto", topic_hint="project/engram/foo"),
    ]
    proposed = propose_refresh(current=None, episodes=episodes)
    assert proposed is not None
    assert "engram" in proposed["active_projects"]
    assert "ultimo task" in proposed["recent_focus"]
    # Defaults for non-derivable
    assert proposed["current_goals"] == []
    assert proposed["open_decisions"] == []


def test_top_k_projects_caps_list_length():
    """active_projects must be capped at top_k_projects."""
    episodes = []
    for i in range(20):
        episodes.append(_ep(f"e{i}", f"t{i}", topic_hint=f"project/proj{i}/x"))
    current = {"active_projects": []}
    proposed = propose_refresh(
        current=current, episodes=episodes, top_k_projects=4,
    )
    assert len(proposed["active_projects"]) == 4


def test_ignores_non_project_topics():
    """Topics not starting with 'project/' do not contribute to
    active_projects (they're lessons/decisions/dialog/etc.)."""
    episodes = [
        _ep("e1", "t1", topic_hint="lessons/foo"),
        _ep("e2", "t2", topic_hint="decisions/bar"),
        _ep("e3", "t3", topic_hint="dialog/doc1"),
        _ep("e4", "t4", topic_hint="project/engram/x"),
    ]
    current = {"active_projects": []}
    proposed = propose_refresh(current=current, episodes=episodes)
    assert proposed["active_projects"] == ["engram"]


def test_diff_helper_reports_changed_fields():
    """compute_diff returns the set of field names that changed."""
    from engram.self_model_refresh import compute_diff
    a = {"recent_focus": "old", "active_projects": ["x"], "notes": "same"}
    b = {"recent_focus": "new", "active_projects": ["y"], "notes": "same"}
    changed = compute_diff(a, b)
    assert "recent_focus" in changed
    assert "active_projects" in changed
    assert "notes" not in changed


def test_recent_focus_truncated_to_reasonable_length():
    """A very long episode title gets truncated so the rendered block
    in SessionStart stays compact."""
    long_task = "x" * 1000
    episodes = [_ep("e1", long_task)]
    proposed = propose_refresh(current={"recent_focus": "old"}, episodes=episodes)
    assert len(proposed["recent_focus"]) <= 280
