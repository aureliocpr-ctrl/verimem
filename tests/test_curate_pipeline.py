"""FORGIA pezzo #239 — Wave 38: full curation pipeline (orchestrator).

One-shot housekeeping that runs:
  1. derive_predicates_batch (bootstrap STRIPS graph)
  2. apply_recommendations (promote/retire per policy)
  3. find_duplicate_skills (report near-dupes)
  4. predicate_graph_check (sanity: cycles + isolated)
  5. corpus_size_report
  6. decay_simulate (preview prune)

Output: aggregated dashboard the user can review before / after
any cleanup. dry-run by default; `apply=True` actually persists
the changes that 1+2 propose.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from engram.skill import Skill


@dataclass
class _FakeEp:
    id: str = ""
    task_text: str = ""
    outcome: str = "success"
    pinned: bool = False
    salience_score: float = 0.5
    skills_used: list[str] = field(default_factory=list)


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._by_id = {s.id: s for s in skills}
        self.stored: list[Skill] = []

    def all(self, status: str | None = None) -> list[Skill]:
        out = list(self._by_id.values())
        if status is None:
            return out
        return [s for s in out if s.status == status]

    def get(self, sid: str) -> Skill | None:
        return self._by_id.get(sid)

    def store(self, s: Skill) -> None:
        self._by_id[s.id] = s
        self.stored.append(s)


class _FakeMemory:
    def __init__(self, eps: list[_FakeEp]) -> None:
        self._eps = eps

    def all(self, limit: int | None = None):
        return list(self._eps if limit is None else self._eps[:limit])

    def decay_pruning_candidates(self, *, top_k: int = 50):
        active = [e for e in self._eps if not e.pinned]
        return sorted(active, key=lambda e: e.salience_score)[:top_k]

    def count(self) -> int:
        return len(self._eps)


class _FakeAgent:
    def __init__(
        self, skills: list[Skill], eps: list[_FakeEp],
    ) -> None:
        self.skills = _FakeSkillsStore(skills)
        self.memory = _FakeMemory(eps)


def test_dry_run_no_mutations():
    from engram.curate_pipeline import curate_pipeline

    skills = [
        Skill(id="ready", name="ready", trials=20, successes=18,
              status="candidate"),
    ]
    a = _FakeAgent(skills, [])
    out = curate_pipeline(agent=a, apply=False)
    # Skills not changed.
    assert a.skills.stored == []
    # But output reports the proposed action.
    assert "recommendations" in out


def test_returns_all_sections():
    from engram.curate_pipeline import curate_pipeline

    a = _FakeAgent([], [])
    out = curate_pipeline(agent=a, apply=False)
    for k in ("predicates", "recommendations", "duplicates",
                "predicate_graph", "size", "decay_preview", "summary"):
        assert k in out


def test_apply_mode_persists_changes():
    from engram.curate_pipeline import curate_pipeline

    skills = [
        Skill(id="ready", name="ready", trials=20, successes=18,
              status="candidate"),
    ]
    a = _FakeAgent(skills, [])
    out = curate_pipeline(agent=a, apply=True)
    # Apply: status changed to promoted.
    s = a.skills.get("ready")
    assert s is not None
    assert s.status == "promoted"


def test_summary_string_present():
    from engram.curate_pipeline import curate_pipeline

    a = _FakeAgent([], [])
    out = curate_pipeline(agent=a)
    assert isinstance(out["summary"], str)
    assert len(out["summary"]) > 0


def test_payload_shape_complete():
    from engram.curate_pipeline import curate_pipeline

    a = _FakeAgent([], [])
    out = curate_pipeline(agent=a)
    for k in ("apply", "predicates", "recommendations",
                "duplicates", "predicate_graph", "size",
                "decay_preview", "summary"):
        assert k in out
