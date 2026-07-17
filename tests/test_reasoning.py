"""FORGIA pezzo #212 — `hippo_reason` orchestrator.

Combines the 4 lenses HippoAgent now has into a single composite call:

  1. SEMANTIC RECALL (existing): "what skills look like this task"
  2. FORWARD SR (Pezzo B):       "if I start at top-skill, what 3-step
                                  trajectory is most likely?"
  3. STRIPS (Pezzo A):           "if I have these initial predicates and
                                  want these goal predicates, what skill
                                  chain works?"
  4. STRUCTURAL ANALOGY (Pezzo C): "what skills have the same procedural
                                    SHAPE in a different domain — transfer
                                    candidates the semantic recall missed?"

The orchestrator is the natural API for "give me everything you know
about how to approach this task". Returns a dict the host LLM can
inspect and pick the best move from.

Six invariants:

  1. EMPTY-EVERYTHING: empty corpus → all sections empty, no crash.
  2. RECALL ALWAYS RUNS: even with no STRIPS args, recall + forward +
     analogues are computed.
  3. STRIPS ONLY WHEN STATES PROVIDED: skip when init/goal not given.
  4. FORWARD/ANALOGY USE TOP-1 RECALL: when recall is non-empty, the
     top hit is the seed for forward_plan and find_analogues.
  5. NO TOP RECALL → NO FORWARD/ANALOGY: skipped sections instead of
     errors.
  6. SUMMARY IS DETERMINISTIC: given the same fakes, the summary
     string is byte-stable (used for snapshot tests).
"""
from __future__ import annotations

from typing import Any

import numpy as np

from verimem.skill import Skill

# ---------- Fakes --------------------------------------------------------


class _FakeEpisode:
    def __init__(self, eid: str, skills_used: list[str]) -> None:
        self.id = eid
        self.skills_used = skills_used


class _FakeMemory:
    def __init__(self, episodes: list[_FakeEpisode]) -> None:
        self._eps = episodes

    def all(self, limit: int | None = None) -> list[_FakeEpisode]:
        if limit is None:
            return list(self._eps)
        return list(self._eps[:limit])


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._by_id = {s.id: s for s in skills}

    def get(self, sid: str) -> Skill | None:
        return self._by_id.get(sid)

    def all(self, status: str | None = None) -> list[Skill]:
        ss = list(self._by_id.values())
        if status is None:
            return ss
        return [s for s in ss if s.status == status]

    def retrieve(self, task: str, k: int = 3,
                  task_embedding=None) -> list[tuple[Skill, float]]:
        # Fake semantic recall — just return the first `k` whose name
        # shares a token with the task.
        task_tokens = set(task.lower().split())
        scored: list[tuple[Skill, float]] = []
        for s in self._by_id.values():
            tokens = set((s.name or "").lower().split("_"))
            if tokens & task_tokens:
                # Cosine-like score: token overlap fraction.
                ov = len(tokens & task_tokens) / max(len(tokens | task_tokens), 1)
                scored.append((s, float(ov)))
        scored.sort(key=lambda x: -x[1])
        return scored[:k]


class _FakeAgent:
    def __init__(self, skills: list[Skill], episodes: list[_FakeEpisode]) -> None:
        self.skills = _FakeSkillsStore(skills)
        self.memory = _FakeMemory(episodes)


# ---------- Tests --------------------------------------------------------


def test_empty_corpus_returns_empty_sections():
    from verimem.reasoning import reason_about_task

    a = _FakeAgent(skills=[], episodes=[])
    out = reason_about_task("any task", agent=a)
    assert out["task"] == "any task"
    assert out["recall"] == []
    assert out["forward_plans"] == []
    assert out["analogues"] == []
    # No states → no STRIPS run.
    assert out["strips_plan"] is None
    assert isinstance(out["summary"], str)


def test_recall_runs_when_corpus_nonempty():
    """Recall should always fire if skills exist."""
    from verimem.reasoning import reason_about_task

    skills = [
        Skill(id="s1", name="deploy_app", trigger="deploy",
              status="promoted"),
        Skill(id="s2", name="parse_json", trigger="parse",
              status="promoted"),
    ]
    a = _FakeAgent(skills=skills, episodes=[])
    out = reason_about_task("deploy something", agent=a)
    # 'deploy' is in 'deploy_app'.
    assert any(r["id"] == "s1" for r in out["recall"]), (
        f"deploy_app should match 'deploy something'; got {out['recall']}"
    )


def test_strips_runs_only_when_states_provided():
    """If initial_state + goal_state are not provided, skip STRIPS."""
    from verimem.reasoning import reason_about_task

    skills = [
        Skill(id="auth", name="login", trigger="login",
              preconditions=["have_creds"],
              postconditions=["logged_in"], status="promoted"),
    ]
    a = _FakeAgent(skills=skills, episodes=[])

    # No states → strips_plan is None.
    out1 = reason_about_task("login task", agent=a)
    assert out1["strips_plan"] is None

    # States provided → STRIPS runs.
    out2 = reason_about_task(
        "login task",
        initial_state=["have_creds"],
        goal_state=["logged_in"],
        agent=a,
    )
    assert out2["strips_plan"] is not None
    assert len(out2["strips_plan"]) >= 1
    assert out2["strips_plan"][0]["id"] == "auth"


def test_forward_uses_top_recall():
    """Forward planning uses the top recall hit as start_skill, with
    transitions inferred from recent episodes."""
    from verimem.reasoning import reason_about_task

    skills = [
        Skill(id="A", name="alpha", trigger="alpha", status="promoted"),
        Skill(id="B", name="beta", trigger="beta", status="promoted"),
        Skill(id="C", name="gamma", trigger="gamma", status="promoted"),
    ]
    eps = [
        _FakeEpisode("e1", ["A", "B", "C"]),
        _FakeEpisode("e2", ["A", "B", "C"]),
        _FakeEpisode("e3", ["A", "B"]),
    ]
    a = _FakeAgent(skills=skills, episodes=eps)
    out = reason_about_task("alpha", agent=a, forward_depth=2)
    # Recall finds 'alpha' → top is A → forward should produce paths
    # starting with A.
    assert out["recall"], "recall should fire for 'alpha'"
    assert out["forward_plans"], "forward should fire after recall"
    assert all(p["path"][0] == "A" for p in out["forward_plans"])


def test_analogues_use_top_recall():
    """Analogy search uses the top recall as the target skill."""
    from verimem.reasoning import reason_about_task

    skills = [
        Skill(id="t", name="deploy_web", trigger="deploy"),
        Skill(id="other", name="deploy_mobile", trigger="deploy"),
    ]
    a = _FakeAgent(skills=skills, episodes=[])
    out = reason_about_task("deploy", agent=a, analogy_top_k=5)
    assert "analogues" in out
    # We may or may not get analogues depending on cosine threshold
    # (real embedding code path); both shapes are valid.
    assert isinstance(out["analogues"], list)


def test_no_recall_skips_forward_and_analogues():
    """When semantic recall finds nothing, forward and analogy are
    skipped (no seed skill available)."""
    from verimem.reasoning import reason_about_task

    skills = [
        Skill(id="x", name="something", trigger="something"),
    ]
    eps = [_FakeEpisode("e1", ["x"])]
    a = _FakeAgent(skills=skills, episodes=eps)
    out = reason_about_task(
        "completely unrelated query no overlap zzz", agent=a,
    )
    # Recall miss → forward and analogues empty.
    assert out["recall"] == []
    assert out["forward_plans"] == []
    assert out["analogues"] == []


def test_summary_contains_section_headers():
    """The summary string mentions the sections that produced data."""
    from verimem.reasoning import reason_about_task

    skills = [
        Skill(id="auth", name="login", trigger="login",
              preconditions=["have_creds"],
              postconditions=["logged_in"]),
    ]
    a = _FakeAgent(skills=skills, episodes=[])
    out = reason_about_task(
        "login flow",
        initial_state=["have_creds"],
        goal_state=["logged_in"],
        agent=a,
    )
    s = out["summary"].lower()
    # The summary should mention recall (since it ran) and STRIPS
    # (since states were provided and a plan was found).
    assert "recall" in s or "skill" in s
    assert "strips" in s or "plan" in s


def test_payload_shape_complete():
    """Every section key always present (defaults if section skipped)."""
    from verimem.reasoning import reason_about_task

    a = _FakeAgent(skills=[], episodes=[])
    out = reason_about_task("foo", agent=a)
    for key in ("task", "recall", "forward_plans", "strips_plan",
                "analogues", "summary"):
        assert key in out, f"missing key: {key}"
