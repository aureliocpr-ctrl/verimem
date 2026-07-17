"""FORGIA pezzo #276 — Wave 75: recent failures only (last N)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _FakeEp:
    id: str
    task_text: str = ""
    outcome: str = "success"
    created_at: float = 0.0


def test_empty():
    from verimem.episode_recent_failures import recent_failures

    out = recent_failures([])
    assert out["episodes"] == []


def test_only_failures():
    from verimem.episode_recent_failures import recent_failures

    eps = [
        _FakeEp("ok", outcome="success", created_at=100.0),
        _FakeEp("bad1", outcome="failure", created_at=200.0),
        _FakeEp("bad2", outcome="failure", created_at=300.0),
    ]
    out = recent_failures(eps)
    ids = [e["id"] for e in out["episodes"]]
    assert "ok" not in ids
    assert "bad1" in ids
    assert "bad2" in ids


def test_newest_first():
    from verimem.episode_recent_failures import recent_failures

    eps = [
        _FakeEp("old", outcome="failure", created_at=100.0),
        _FakeEp("new", outcome="failure", created_at=300.0),
    ]
    out = recent_failures(eps)
    ids = [e["id"] for e in out["episodes"]]
    assert ids == ["new", "old"]


def test_top_k():
    from verimem.episode_recent_failures import recent_failures

    eps = [
        _FakeEp(f"e{i}", outcome="failure", created_at=float(i))
        for i in range(10)
    ]
    out = recent_failures(eps, top_k=3)
    assert len(out["episodes"]) == 3


def test_payload_shape():
    from verimem.episode_recent_failures import recent_failures

    out = recent_failures([])
    for k in ("episodes", "n_total_failures"):
        assert k in out
