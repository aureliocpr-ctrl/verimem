"""Tests for episodic memory + recall + clustering."""
from __future__ import annotations

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory


def _ep(task_id, text, outcome="success", final="x"):
    return Episode(
        task_id=task_id, task_text=text, outcome=outcome, final_answer=final,
        traces=[Trace(step=1, thought="t", action="a", action_input="{}", observation="o")],
        tokens_used=10,
    )


def test_store_and_get(tmp_data_dir):
    m = EpisodicMemory(tmp_data_dir / "episodes" / "ep.db")
    e = _ep("t1", "Define fib")
    m.store(e)
    got = m.get(e.id)
    assert got is not None
    assert got.task_text == "Define fib"
    assert len(got.traces) == 1


def test_recall_semantic(tmp_data_dir):
    m = EpisodicMemory(tmp_data_dir / "episodes" / "ep.db")
    m.store(_ep("t1", "Define fibonacci function"))
    m.store(_ep("t2", "Sort a list ascending"))
    m.store(_ep("t3", "Compute Fibonacci numbers"))
    results = m.recall("fibonacci", k=2)
    assert len(results) == 2
    # Both top results should be about Fibonacci, not about sorting
    assert all("ib" in ep.task_text.lower() for ep, _ in results)


def test_filter_by_outcome(tmp_data_dir):
    m = EpisodicMemory(tmp_data_dir / "episodes" / "ep.db")
    m.store(_ep("a", "x", outcome="success"))
    m.store(_ep("b", "y", outcome="failure"))
    m.store(_ep("c", "z", outcome="success"))
    assert len(m.by_outcome("success")) == 2
    assert len(m.by_outcome("failure")) == 1


def test_clustering(tmp_data_dir):
    m = EpisodicMemory(tmp_data_dir / "episodes" / "ep.db")
    m.store(_ep("a", "Reverse a string"))
    m.store(_ep("b", "Reverse the characters of a string"))
    m.store(_ep("c", "Compute factorial"))
    clusters = m.cluster_similar(eps_threshold=0.5)
    sizes = sorted(len(c) for c in clusters)
    # At least one cluster should group the two "reverse string" tasks
    assert max(sizes) >= 2


def test_causal_graph(tmp_data_dir):
    m = EpisodicMemory(tmp_data_dir / "episodes" / "ep.db")
    e1 = _ep("a", "x"); e2 = _ep("b", "y")
    m.store(e1); m.store(e2)
    m.add_causal_edge(e1.id, e2.id, via_skill_id="sk1", weight=0.7)
    g = m.causal_graph()
    assert g.has_edge(e1.id, e2.id)
    assert g[e1.id][e2.id]["skill"] == "sk1"
