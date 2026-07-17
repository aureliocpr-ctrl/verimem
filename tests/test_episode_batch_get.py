"""FORGIA pezzo #267 — Wave 66: multi-id episode lookup.

Single MCP call fetches N episodes by id at once. Avoids N round-
trips when comparing/displaying multiple related episodes.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _FakeEp:
    id: str
    task_text: str = ""
    outcome: str = "success"
    skills_used: list[str] = field(default_factory=list)


class _FakeMemory:
    def __init__(self, eps: list[_FakeEp]) -> None:
        self._by_id = {e.id: e for e in eps}

    def get(self, eid: str):
        return self._by_id.get(eid)


def test_empty_ids_returns_empty():
    from verimem.episode_batch_get import episode_batch_get

    m = _FakeMemory([])
    out = episode_batch_get(memory=m, episode_ids=[])
    assert out["episodes"] == []
    assert out["missing"] == []


def test_finds_all_present():
    from verimem.episode_batch_get import episode_batch_get

    eps = [_FakeEp("e1", task_text="a"), _FakeEp("e2", task_text="b")]
    m = _FakeMemory(eps)
    out = episode_batch_get(memory=m, episode_ids=["e1", "e2"])
    ids = [e["id"] for e in out["episodes"]]
    assert ids == ["e1", "e2"]
    assert out["missing"] == []


def test_separates_missing():
    from verimem.episode_batch_get import episode_batch_get

    eps = [_FakeEp("e1", task_text="a")]
    m = _FakeMemory(eps)
    out = episode_batch_get(
        memory=m, episode_ids=["e1", "missing1", "missing2"],
    )
    assert [e["id"] for e in out["episodes"]] == ["e1"]
    assert sorted(out["missing"]) == ["missing1", "missing2"]


def test_preserves_input_order():
    from verimem.episode_batch_get import episode_batch_get

    eps = [_FakeEp("a"), _FakeEp("b"), _FakeEp("c")]
    m = _FakeMemory(eps)
    out = episode_batch_get(memory=m, episode_ids=["c", "a", "b"])
    assert [e["id"] for e in out["episodes"]] == ["c", "a", "b"]


def test_payload_shape():
    from verimem.episode_batch_get import episode_batch_get

    m = _FakeMemory([])
    out = episode_batch_get(memory=m, episode_ids=[])
    for k in ("episodes", "missing", "n_found", "n_missing"):
        assert k in out
