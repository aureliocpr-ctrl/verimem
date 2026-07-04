"""Cycle 170 (2026-05-19) — pin the Arm-D self-loop bug from cycle 159.8.

ROADMAP §5b bug #1 (`docs/ROADMAP-2026-05-19.md` line 71-73): team Arm-D
reported that ``_wire_edges`` falls back to ``source_eps = [ep_id]`` when
the cluster's sub-facts have empty ``source_episodes``, producing a
self-edge ``(ep_id, ep_id, narrative_link, 1.0)`` in ``causal_edges``.

A self-edge in a causal graph is semantically degenerate ("this episode
caused itself") and pollutes ``hippo_lineage_trace``. The master node
is *already* reachable via ``facts.source_episodes`` (``_persist_master``
writes ``source_episodes=[ep.id]`` on the master fact at line 456), so
the fallback edge adds zero retrieval value while adding graph noise.

Falsification: the docstring on ``_wire_edges`` argues the fallback
keeps ``lineage_trace`` reachable, but the cycle #52 lineage walker
crosses the ``has_fact`` → ``from_episode`` edges as well, so removing
the self-edge does NOT disconnect the master.

ROADMAP §5b bugs #2 (idempotency probe checks ``proposition`` only)
and #3 (LIKE wildcard injection on prefix) were already closed by
cycle 151 HIGH#1 — verified empirically against main 542da9b
(see ``_cluster_already_consolidated`` line 220 uses ``topic = ?``
equality; all LIKE patterns use compile-time constants, no user input).

This file only pins bug #1.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engram.consolidation import auto_consolidate
from engram.memory import EpisodicMemory
from engram.semantic import Fact, SemanticMemory


@pytest.fixture
def stores(tmp_path: Path):
    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    ep = EpisodicMemory(db_path=tmp_path / "ep.db")

    class _Pair:
        pass
    pair = _Pair()
    pair.sm = sm
    pair.ep = ep
    return pair


def _count_self_edges(ep_store: EpisodicMemory) -> int:
    """Count rows in ``causal_edges`` where src == dst (self-loops)."""
    with ep_store._connect() as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM causal_edges "
            "WHERE src_episode_id = dst_episode_id"
        ).fetchone()
    return int(row["c"])


def _seed_cluster_with_empty_source_episodes(
    sm: SemanticMemory, prefix: str, n: int = 5,
) -> list[str]:
    """Insert ``n`` facts under ``prefix/sub-K`` each with empty
    ``source_episodes``. Returns the list of fact ids.

    The empty ``source_episodes`` is the exact precondition that drives
    ``_wire_edges`` into the buggy fallback branch.
    """
    ids: list[str] = []
    for k in range(n):
        f = Fact(
            proposition=f"cluster claim {k} under {prefix}",
            topic=f"{prefix}/sub-{k}",
            confidence=0.9,
            source_episodes=[],          # ← the trigger
            status="model_claim",
        )
        sm.store(f)
        ids.append(f.id)
    return ids


def test_auto_consolidate_no_self_loop_when_subfacts_have_no_source_eps(
    stores,
) -> None:
    """RED→GREEN: after consolidation, ``causal_edges`` must contain
    zero self-edges. Pre-fix this test fails because ``_wire_edges``
    falls back to ``[ep_id]`` and inserts one self-edge per cluster.

    Note: ``auto_consolidate`` is called with ``min_size=5`` (default)
    and ``prefix_depth=2``. Seeding 5 facts under ``cycle170/test``
    produces exactly one cluster (``cycle170/test``).
    """
    _seed_cluster_with_empty_source_episodes(
        stores.sm, prefix="cycle170/test", n=5,
    )
    stats = auto_consolidate(stores.sm, stores.ep)
    # Sanity: the orchestrator did consolidate the one cluster.
    assert stats["masters_persisted"] == 1, stats
    # The fix: no self-edges should have been inserted.
    assert _count_self_edges(stores.ep) == 0, (
        f"Found self-loop edges in causal_edges; pre-fix this was 1 per "
        f"cluster with empty source_episodes. Stats: {stats}"
    )


def test_auto_consolidate_no_edges_when_subfacts_have_no_source_eps(
    stores,
) -> None:
    """Stronger claim than the previous test: when sub-facts truly have
    no source episodes, ``_wire_edges`` should write NOTHING to
    ``causal_edges`` (not just no self-loop). The master node is still
    reachable from the lineage walker via ``facts.source_episodes`` on
    the master fact (line 456 of consolidation.py).

    Pre-fix: 1 edge per cluster (the self-loop).
    Post-fix: 0 edges total for this cluster.
    """
    _seed_cluster_with_empty_source_episodes(
        stores.sm, prefix="cycle170/empty", n=5,
    )
    stats = auto_consolidate(stores.sm, stores.ep)
    assert stats["masters_persisted"] == 1
    # ``edges_created`` is what the orchestrator returns. With empty
    # source_eps and no fallback, this should be 0.
    assert stats["edges_created"] == 0, stats


def test_auto_consolidate_writes_edges_when_subfacts_have_source_eps(
    stores,
) -> None:
    """Regression guard: the fix must NOT break the happy path. When
    sub-facts have real ``source_episodes``, one edge per distinct
    source episode is still written.
    """
    # 5 facts each pointing at a distinct episode id.
    for k in range(5):
        f = Fact(
            proposition=f"happy claim {k}",
            topic=f"cycle170/happy/sub-{k}",
            confidence=0.9,
            source_episodes=[f"ep_real_{k}"],
            status="model_claim",
        )
        stores.sm.store(f)

    stats = auto_consolidate(stores.sm, stores.ep)
    assert stats["masters_persisted"] == 1
    # Five distinct source eps → five narrative_link edges from master.
    assert stats["edges_created"] == 5, stats
    # And still zero self-edges (none of the ep_real_K equal the master).
    assert _count_self_edges(stores.ep) == 0
