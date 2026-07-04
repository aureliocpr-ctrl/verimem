"""Cycle #154 (2026-05-19) — refactor _persist_master + _wire_edges tests.

Cycle 153 honeycomb mesh review ha identificato ``auto_consolidate``
come God Function con cyclomatic complexity ~9 e responsabilità inline
multi-stage (consenso 5/6 angoli: architect, maintainability,
performance, ux, security). Le 3 responsabilità (Episode store, Fact
store, edge wiring) erano impossibili da unit-testare in isolamento.

Cycle 154 ha estratto due helper private:
  • ``_persist_master(sm, mem, cluster, master) → (ep_id, fact_id, edges)``
  • ``_wire_edges(sm, mem, ep_id, fact_ids) → int``

Questo file aggiunge unit test in isolamento per i due helper —
qualcosa che pre-cycle 154 era impossibile.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engram.consolidation import (
    _persist_master,
    _wire_edges,
    propose_master_node,
)
from engram.memory import EpisodicMemory
from engram.semantic import Fact, SemanticMemory


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


@pytest.fixture
def mem(tmp_path: Path) -> EpisodicMemory:
    return EpisodicMemory(db_path=tmp_path / "ep.db")


def _seed_cluster(
    sm: SemanticMemory, topic: str, n: int, *, with_source_eps: bool = True,
) -> dict:
    """Build a cluster dict for _persist_master tests.

    Cycle 170 (2026-05-19): seed defaults now carry a synthetic
    ``source_episodes`` entry per fact so the post-fix ``_wire_edges``
    can produce real edges. Tests that need to exercise the
    empty-source-eps branch (the cycle 170 self-loop fix) pass
    ``with_source_eps=False`` explicitly.
    """
    fact_ids: list[str] = []
    for i in range(n):
        f = Fact(
            proposition=f"Atom #{i} in {topic} — content {i}",
            topic=topic,
            confidence=0.7,
            source_episodes=(
                [f"ep_seed_{topic.replace('/', '_')}_{i}"]
                if with_source_eps else []
            ),
            verified_by=[f"test:cycle154:{i}"],
            status="model_claim",
        )
        sm.store(f)
        fact_ids.append(f.id)
    cluster_prefix = "/".join(topic.split("/")[:2])
    return {
        "topic_prefix": cluster_prefix,
        "fact_ids": fact_ids,
        "fact_count": n,
    }


def test_persist_master_returns_triplet_of_ids_and_count(
    sm: SemanticMemory, mem: EpisodicMemory,
) -> None:
    """``_persist_master`` returns ``(ep_id, fact_id, edges_n)``.

    All three must be non-empty/positive when the cluster has at least
    one source-episode chain or falls back to self-edge.
    """
    cluster = _seed_cluster(sm, "project/cycle154/triplet", 5)
    master = propose_master_node(sm, cluster)

    result = _persist_master(sm, mem, cluster, master)

    assert isinstance(result, tuple)
    assert len(result) == 3
    ep_id, fact_id, edges_n = result
    assert isinstance(ep_id, str) and ep_id, "ep_id must be non-empty"
    assert isinstance(fact_id, str) and fact_id, "fact_id must be non-empty"
    assert isinstance(edges_n, int) and edges_n >= 1, (
        f"edges_n must be ≥1 (self-edge fallback or real source-eps), "
        f"got {edges_n!r}"
    )


def test_persist_master_creates_episode_and_fact_rows(
    sm: SemanticMemory, mem: EpisodicMemory,
) -> None:
    """``_persist_master`` writes one Episode row + one Fact row + ≥1
    causal_edge row. Verified via direct SQLite counts.
    """
    cluster = _seed_cluster(sm, "project/cycle154/rows", 6)
    master = propose_master_node(sm, cluster)

    with mem._connect() as conn:  # noqa: SLF001
        eps_before = int(
            conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0],
        )
        edges_before = int(
            conn.execute("SELECT COUNT(*) FROM causal_edges").fetchone()[0],
        )
    with sm._connect() as conn:  # noqa: SLF001
        facts_before = int(
            conn.execute(
                "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL",
            ).fetchone()[0],
        )

    ep_id, fact_id, edges_n = _persist_master(sm, mem, cluster, master)

    with mem._connect() as conn:  # noqa: SLF001
        eps_after = int(
            conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0],
        )
        edges_after = int(
            conn.execute("SELECT COUNT(*) FROM causal_edges").fetchone()[0],
        )
    with sm._connect() as conn:  # noqa: SLF001
        facts_after = int(
            conn.execute(
                "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL",
            ).fetchone()[0],
        )

    assert eps_after == eps_before + 1, (
        f"exactly 1 master Episode must be created, got delta "
        f"{eps_after - eps_before}"
    )
    assert facts_after == facts_before + 1, (
        f"exactly 1 master Fact must be created, got delta "
        f"{facts_after - facts_before}"
    )
    assert edges_after >= edges_before + 1, (
        f"≥1 causal_edge must be wired, got delta "
        f"{edges_after - edges_before}"
    )
    assert edges_n == edges_after - edges_before, (
        f"returned edges_n {edges_n} must equal actual db delta "
        f"{edges_after - edges_before}"
    )


def test_wire_edges_no_edges_when_no_source_eps(
    sm: SemanticMemory, mem: EpisodicMemory,
) -> None:
    """Cycle 170 (2026-05-19, ROADMAP §5b bug #1): when ``fact_ids``
    have no ``source_episodes``, ``_wire_edges`` must write NOTHING.

    Pre-cycle-170: the function fell back to ``source_eps = [ep_id]``
    and wrote one self-edge ``(ep_id, ep_id, narrative_link, 1.0)`` —
    a semantically-degenerate "episode caused itself" row that
    polluted ``hippo_lineage_trace``. The master Episode is already
    reachable via ``facts.source_episodes`` on the master Fact, so
    the self-edge added zero retrieval value.

    Post-cycle-170: zero edges, zero pollution.
    """
    # Seed facts with EMPTY source_episodes (override the cycle 170
    # default which now carries synthetic eps).
    cluster = _seed_cluster(
        sm, "project/cycle154/self-fallback", 3, with_source_eps=False,
    )
    # Verify the seeding actually produced empty source_episodes.
    with sm._connect() as conn:  # noqa: SLF001
        rows = conn.execute(
            "SELECT source_episodes FROM facts WHERE id IN ("
            + ",".join(["?"] * len(cluster["fact_ids"])) + ")",
            tuple(cluster["fact_ids"]),
        ).fetchall()
    for r in rows:
        assert r["source_episodes"] in (None, "", "[]"), (
            f"test precondition: source_episodes must be empty/null, "
            f"got {r['source_episodes']!r}"
        )

    # Create a master Episode manually so we have a real ep_id to wire from.
    from engram.episode import Episode
    ep = Episode(
        task_id="project/cycle154/self-fallback/auto-MASTER",
        task_text="test wire_edges no-source-eps post-cycle-170",
        final_answer="no-edge test",
        outcome="success",
    )
    mem.store(ep)

    edges_n = _wire_edges(sm, mem, ep.id, cluster["fact_ids"])
    assert edges_n == 0, (
        f"_wire_edges with empty source_episodes must produce zero "
        f"edges (cycle 170 fix), got {edges_n}"
    )

    # Verify NO self-edge in db.
    with mem._connect() as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT * FROM causal_edges WHERE src_episode_id = ? "
            "AND dst_episode_id = ?",
            (ep.id, ep.id),
        ).fetchone()
    assert row is None, (
        "self-edge row found in causal_edges — cycle 170 fix regressed"
    )
