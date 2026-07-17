"""Cycle #144 (2026-05-18 sera) — auto-consolidation orchestrator.

Aurelio direttiva post-vista frammentazione memoria: 'non dobbiamo
frammentare, dobbiamo concatenare'. Cycle 142 ha aperto coding-failure
side, 143 coding-learning side. Cycle 144 attacca il root cause: i
master node sono stati creati MANUALMENTE dall'altra sessione (6
verticali + proposta 9 orizzontali), ma il sistema HippoAgent non sa
auto-concatenare i propri fact appena salvati.

Risultato: ogni cycle N aggiunge fact con topic ``project/hippoagent/
cycleN-*`` che diventano singleton fra 25+ sotto-topic dello stesso
namespace. Senza orchestrator, la frammentazione cresce monotonamente
e dipende da consolidamenti 1-shot ricorrenti da operator/altra
sessione.

Cycle 144 = orchestrator AUTO che:
    1. Detecta cluster (fact con topic prefix comune ≥ N atomi)
    2. Propone master node draft (proposition + ≤3 key_facts atomi)
    3. Persist master Episode + Fact + narrative_link causal_edges
       verso i sub-fact/sub-ep del cluster
    4. Idempotency: re-run non duplica master su cluster già consolidato

Pipeline esistente sfruttata:
    • verimem.episode.Episode dataclass
    • verimem.semantic.Fact dataclass
    • verimem.memory.EpisodicMemory.store + causal_edges schema
    • verimem.semantic.SemanticMemory.store

API contract (cycle 144 MVP):
    detect_cluster_candidates(sm, *, min_size=5, prefix_depth=2)
        → list[{topic_prefix, fact_ids, fact_count}]

    propose_master_node(sm, cluster)
        → {proposition, topic, key_facts}

    auto_consolidate(sm, mem, *, min_size=5, prefix_depth=2,
                     dry_run=False)
        → {clusters_detected, masters_proposed, masters_persisted,
           edges_created, duration_ms}

TDD strict RED→GREEN: this file must fail import on
verimem.consolidation (does not yet exist).
"""
from __future__ import annotations

from pathlib import Path

import pytest

# RED MARKER
from verimem.consolidation import (
    auto_consolidate,
    detect_cluster_candidates,
    propose_master_node,
)
from verimem.memory import EpisodicMemory
from verimem.semantic import Fact, SemanticMemory


def _seed_facts(
    sm: SemanticMemory, topic: str, n: int, *, with_source_eps: bool = True,
) -> list[str]:
    """Insert n facts under the same topic, return their ids.

    Cycle 170 (2026-05-19): seed defaults now carry a synthetic
    ``source_episodes`` entry per fact so the post-fix ``_wire_edges``
    can produce real edges. Tests that need to exercise the
    empty-source-eps branch (the cycle 170 self-loop fix) pass
    ``with_source_eps=False`` explicitly.
    """
    ids: list[str] = []
    for i in range(n):
        f = Fact(
            proposition=f"Atom #{i} in {topic} — content {i}",
            topic=topic,
            confidence=0.7,
            source_episodes=(
                [f"ep_seed_{topic.replace('/', '_')}_{i}"]
                if with_source_eps else []
            ),
            verified_by=[f"test:seed:cluster-{topic}:{i}"],
            status="model_claim",
        )
        sm.store(f)
        ids.append(f.id)
    return ids


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


@pytest.fixture
def mem(tmp_path: Path) -> EpisodicMemory:
    return EpisodicMemory(db_path=tmp_path / "ep.db")


class TestDetectClusters:
    """detect_cluster_candidates groups facts by topic prefix."""

    def test_returns_cluster_for_prefix_with_min_size(
        self, sm: SemanticMemory,
    ) -> None:
        _seed_facts(sm, "project/foo/sub-a", 10)
        clusters = detect_cluster_candidates(sm, min_size=5, prefix_depth=2)
        assert clusters, (
            f"cycle 144: 10 facts under one prefix must yield ≥1 cluster, "
            f"got {clusters!r}"
        )
        c = next((c for c in clusters if c["topic_prefix"] == "project/foo"), None)
        assert c is not None, (
            f"cycle 144: cluster prefix must be 'project/foo' (depth=2), "
            f"got {[c['topic_prefix'] for c in clusters]!r}"
        )
        assert c["fact_count"] >= 10

    def test_filters_below_min_size(self, sm: SemanticMemory) -> None:
        _seed_facts(sm, "project/tiny/x", 3)
        clusters = detect_cluster_candidates(sm, min_size=5, prefix_depth=2)
        assert all(c["topic_prefix"] != "project/tiny" for c in clusters), (
            f"cycle 144: cluster with 3<5 facts must be filtered out, "
            f"got {clusters!r}"
        )

    def test_prefix_depth_2_groups_sub_topics(
        self, sm: SemanticMemory,
    ) -> None:
        # Seed two distinct deep topics that share a depth-2 prefix.
        _seed_facts(sm, "project/bar/cycle-a", 4)
        _seed_facts(sm, "project/bar/cycle-b", 4)
        clusters = detect_cluster_candidates(sm, min_size=5, prefix_depth=2)
        bar = [c for c in clusters if c["topic_prefix"] == "project/bar"]
        assert bar, (
            f"cycle 144: 4+4 same depth-2 prefix must merge to 1 cluster, "
            f"got {clusters!r}"
        )
        assert bar[0]["fact_count"] >= 8


class TestProposeMasterNode:
    """propose_master_node returns a draft master fact for one cluster."""

    def test_returns_dict_with_required_keys(
        self, sm: SemanticMemory,
    ) -> None:
        _seed_facts(sm, "project/baz/area-x", 6)
        clusters = detect_cluster_candidates(sm, min_size=5)
        assert clusters
        master = propose_master_node(sm, clusters[0])
        for k in ("proposition", "topic", "key_facts"):
            assert k in master, (
                f"cycle 144: master missing key {k!r}, got {master.keys()!r}"
            )

    def test_proposition_non_empty_and_mentions_prefix(
        self, sm: SemanticMemory,
    ) -> None:
        _seed_facts(sm, "project/quz/area-y", 6)
        clusters = detect_cluster_candidates(sm, min_size=5)
        master = propose_master_node(sm, clusters[0])
        assert master["proposition"], (
            f"cycle 144: master proposition must be non-empty, got {master!r}"
        )
        assert "project/quz" in master["topic"], (
            f"cycle 144: master topic must root at cluster prefix, "
            f"got {master['topic']!r}"
        )

    def test_key_facts_at_most_3(self, sm: SemanticMemory) -> None:
        _seed_facts(sm, "project/big/area-z", 12)
        clusters = detect_cluster_candidates(sm, min_size=5)
        master = propose_master_node(sm, clusters[0])
        assert 0 < len(master["key_facts"]) <= 3, (
            f"cycle 144: key_facts must be 1..3 atomi, got "
            f"{len(master['key_facts'])} items"
        )


class TestAutoConsolidate:
    """auto_consolidate runs end-to-end (detect + propose + persist)."""

    def test_dry_run_no_persistence(
        self, sm: SemanticMemory, mem: EpisodicMemory,
    ) -> None:
        _seed_facts(sm, "project/dry/area", 6)
        before = sm.count() if hasattr(sm, "count") else _count_facts(sm)
        out = auto_consolidate(sm, mem, min_size=5, dry_run=True)
        after = sm.count() if hasattr(sm, "count") else _count_facts(sm)
        assert out["clusters_detected"] >= 1
        assert out["masters_persisted"] == 0, (
            f"cycle 144: dry_run must persist 0 masters, got "
            f"{out['masters_persisted']!r}"
        )
        assert after == before, (
            f"cycle 144: dry_run must not change fact count "
            f"({before}→{after})"
        )

    def test_apply_persists_master_and_edges(
        self, sm: SemanticMemory, mem: EpisodicMemory,
    ) -> None:
        _seed_facts(sm, "project/apply/area", 7)
        facts_before = _count_facts(sm)
        eps_before = _count_episodes(mem)
        edges_before = _count_edges(mem)
        out = auto_consolidate(sm, mem, min_size=5, dry_run=False)
        assert out["masters_persisted"] >= 1, (
            f"cycle 144: apply must persist ≥1 master, got {out!r}"
        )
        assert out["edges_created"] >= 1, (
            f"cycle 144: apply must create ≥1 narrative_link edge "
            f"(master ep → sub fact source-eps OR self-link). Got {out!r}"
        )
        assert _count_facts(sm) > facts_before, (
            f"cycle 144: facts must grow after apply "
            f"({facts_before}→{_count_facts(sm)})"
        )
        assert _count_episodes(mem) > eps_before, (
            f"cycle 144: master Episode must be created "
            f"({eps_before}→{_count_episodes(mem)})"
        )
        assert _count_edges(mem) > edges_before, (
            f"cycle 144: causal_edges must grow "
            f"({edges_before}→{_count_edges(mem)})"
        )

    def test_idempotent_second_run_zero_new(
        self, sm: SemanticMemory, mem: EpisodicMemory,
    ) -> None:
        _seed_facts(sm, "project/idem/area", 6)
        first = auto_consolidate(sm, mem, min_size=5, dry_run=False)
        assert first["masters_persisted"] >= 1
        second = auto_consolidate(sm, mem, min_size=5, dry_run=False)
        assert second["masters_persisted"] == 0, (
            f"cycle 144: second run on same cluster must persist 0 new "
            f"masters (idempotency), got {second!r}"
        )


# ---- low-level helpers -----------------------------------------------
def _count_facts(sm: SemanticMemory) -> int:
    with sm._connect() as conn:  # noqa: SLF001
        return int(conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL",
        ).fetchone()[0])


def _count_episodes(mem: EpisodicMemory) -> int:
    with mem._connect() as conn:  # noqa: SLF001
        return int(conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0])


def _count_edges(mem: EpisodicMemory) -> int:
    with mem._connect() as conn:  # noqa: SLF001
        return int(conn.execute(
            "SELECT COUNT(*) FROM causal_edges",
        ).fetchone()[0])
