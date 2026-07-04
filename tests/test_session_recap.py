"""FORGIA pezzo #261 — Wave 60: session recap.

Summary of all activity since a session-start timestamp. Counts
episodes/facts/skills touched, top skills used, total tokens,
outcome breakdown. Useful end-of-session "what did I do?".
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class _FakeEp:
    id: str = ""
    outcome: str = "success"
    tokens_used: int = 0
    created_at: float = 0.0
    skills_used: list[str] = field(default_factory=list)


@dataclass
class _FakeFact:
    id: str
    proposition: str = ""
    topic: str = ""
    created_at: float = 0.0


class _FakeSemantic:
    def __init__(self, facts: list[_FakeFact]) -> None:
        self._facts = facts

    def list_facts(self, *, limit=1000, offset=0):
        return list(self._facts)


class _FakeMemory:
    def __init__(self, eps: list[_FakeEp]) -> None:
        self._eps = eps

    def all(self, limit=None):
        return list(self._eps)


class _FakeAgent:
    def __init__(self, eps: list[_FakeEp], facts: list[_FakeFact]) -> None:
        self.memory = _FakeMemory(eps)
        self.semantic = _FakeSemantic(facts)


def test_empty_session():
    from engram.session_recap import session_recap

    a = _FakeAgent([], [])
    out = session_recap(since=0.0, agent=a)
    assert out["n_episodes"] == 0
    assert out["n_facts_added"] == 0


def test_counts_episodes_in_window():
    from engram.session_recap import session_recap

    now = time.time()
    eps = [
        _FakeEp("e1", outcome="success", created_at=now),
        _FakeEp("e2", outcome="failure", created_at=now),
        _FakeEp("old", outcome="success", created_at=now - 86400 * 10),
    ]
    a = _FakeAgent(eps, [])
    out = session_recap(since=now - 3600, agent=a)
    assert out["n_episodes"] == 2
    assert out["n_success"] == 1
    assert out["n_failure"] == 1


def test_counts_facts_added():
    from engram.session_recap import session_recap

    now = time.time()
    facts = [
        _FakeFact("f1", "new", created_at=now),
        _FakeFact("f2", "old", created_at=now - 86400 * 30),
    ]
    a = _FakeAgent([], facts)
    out = session_recap(since=now - 3600, agent=a)
    assert out["n_facts_added"] == 1


def test_top_skills_used():
    from engram.session_recap import session_recap

    now = time.time()
    eps = [
        _FakeEp("e1", skills_used=["a", "b"], created_at=now),
        _FakeEp("e2", skills_used=["a"], created_at=now),
        _FakeEp("e3", skills_used=["c"], created_at=now),
    ]
    a = _FakeAgent(eps, [])
    out = session_recap(since=0.0, agent=a)
    # 'a' used 2x, others 1x.
    top_ids = [s["skill_id"] for s in out["top_skills_used"]]
    assert top_ids[0] == "a"


def test_total_tokens():
    from engram.session_recap import session_recap

    now = time.time()
    eps = [
        _FakeEp("e1", tokens_used=500, created_at=now),
        _FakeEp("e2", tokens_used=1500, created_at=now),
    ]
    a = _FakeAgent(eps, [])
    out = session_recap(since=0.0, agent=a)
    assert out["total_tokens"] == 2000


def test_payload_shape_complete():
    from engram.session_recap import session_recap

    a = _FakeAgent([], [])
    out = session_recap(since=0.0, agent=a)
    for k in ("since", "n_episodes", "n_success", "n_failure",
                "n_facts_added", "total_tokens", "top_skills_used",
                "summary"):
        assert k in out


def test_summary_string_present():
    from engram.session_recap import session_recap

    a = _FakeAgent([], [])
    out = session_recap(since=0.0, agent=a)
    assert isinstance(out["summary"], str)
