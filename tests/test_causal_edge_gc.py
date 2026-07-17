"""GC pass for causal_edges orphaned by episode deletion (scan #20).

decay_prune (and delete_episode) hard-DELETE episodes but deliberately
leave causal_edges that reference them — the docstring says the lineage
graph "deserves its own GC pass", which never existed. Over many sleep
cycles those dangling edges accumulate unbounded and pollute every
causal-graph walk (PPR, lineage_trace).

This adds that pass: gc_orphan_causal_edges() removes any edge whose src
OR dst episode no longer exists, returns the count, and is a no-op when
the graph is clean. It is NOT wired into decay_prune (that would defeat
the undo-log: a restored episode must find its edges intact) — callers
run it after the undo window, like any other GC.
"""
from __future__ import annotations

from verimem.episode import Episode
from verimem.memory import EpisodicMemory


def _seed_chain(mem: EpisodicMemory) -> list[str]:
    eps = [Episode(task_text=f"step {i}", final_answer=f"a{i}",
                   outcome="success") for i in range(3)]
    for ep in eps:
        mem.store(ep)
    a, b, c = (ep.id for ep in eps)
    mem.add_causal_edge(a, b, via_skill_id="s1", weight=1.0)
    mem.add_causal_edge(b, c, via_skill_id="s1", weight=1.0)
    return [a, b, c]


def _edge_count(mem: EpisodicMemory) -> int:
    with mem._connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM causal_edges").fetchone()[0]


def _decay_delete(mem: EpisodicMemory, ep_id: str) -> None:
    """Simulate decay_prune's path: raw DELETE FROM episodes that leaves
    causal_edges behind (unlike delete(), which already wipes its edges)."""
    with mem._connect() as conn:
        conn.execute("DELETE FROM episodes WHERE id = ?", (ep_id,))


def test_gc_removes_edges_touching_deleted_episode(tmp_path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    a, b, c = _seed_chain(mem)
    assert _edge_count(mem) == 2

    _decay_delete(mem, b)  # B gone; edges a->b and b->c now dangle

    removed = mem.gc_orphan_causal_edges()
    assert removed == 2, "both edges touching the deleted episode must be GC'd"
    assert _edge_count(mem) == 0


def test_gc_keeps_edges_between_live_episodes(tmp_path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    a, b, c = _seed_chain(mem)
    # delete C: only b->c dangles, a->b stays (both endpoints alive)
    _decay_delete(mem, c)
    removed = mem.gc_orphan_causal_edges()
    assert removed == 1, "only the edge touching the deleted episode is removed"
    assert _edge_count(mem) == 1


def test_gc_clean_graph_is_noop(tmp_path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    _seed_chain(mem)
    assert mem.gc_orphan_causal_edges() == 0
    assert _edge_count(mem) == 2
