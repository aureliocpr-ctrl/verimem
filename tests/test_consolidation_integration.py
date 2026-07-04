"""Cycle #145 Agent C (QA-Eng, 2026-05-18) — integration edge cases for
the cycle 144 auto-consolidation orchestrator (``engram.consolidation``).

The 9 unit tests in ``tests/test_consolidation.py`` cover the happy path:
detect/propose/persist/idempotent for fresh clusters. This file targets
edge cases not exercised by them:

1. **Superseded sub-facts must NOT inflate fact_count.**
   ``detect_cluster_candidates`` filters ``WHERE superseded_by IS NULL``
   (consolidation.py:84). Seed 5 facts under one prefix, mark 2 as
   superseded via direct SQL UPDATE, run detect → cluster.fact_count
   must be 3 not 5.

2. **Malformed JSON in ``source_episodes`` does not crash the pipeline.**
   ``_source_episodes_for_facts`` parses each fact's ``source_episodes``
   with json.loads inside try/except (consolidation.py:203-206). Seed
   5 facts where one has ``source_episodes='{broken-not-json'`` written
   via raw SQL UPDATE. auto_consolidate must complete with
   masters_persisted >= 1 (the bad row is silently skipped, no crash).

3. **Back-to-back apply runs are idempotent (no race on the LIKE probe).**
   ``_cluster_already_consolidated`` uses a LIKE on the master
   proposition (consolidation.py:178-180). Two consecutive
   ``auto_consolidate(..., dry_run=False)`` calls must yield
   masters_persisted=1 on the first and 0 on the second, even when fired
   back-to-back within the same millisecond.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engram.consolidation import auto_consolidate, detect_cluster_candidates
from engram.memory import EpisodicMemory
from engram.semantic import Fact, SemanticMemory


# ---- fixtures (mirror tests/test_consolidation.py:76-83) -------------
@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


@pytest.fixture
def mem(tmp_path: Path) -> EpisodicMemory:
    return EpisodicMemory(db_path=tmp_path / "ep.db")


def _seed_facts(sm: SemanticMemory, topic: str, n: int) -> list[str]:
    """Insert n facts under one topic, return their ids."""
    ids: list[str] = []
    for i in range(n):
        f = Fact(
            proposition=f"Atom #{i} in {topic} — integration content {i}",
            topic=topic,
            confidence=0.7,
            verified_by=[f"test:integration:{topic}:{i}"],
            status="model_claim",
        )
        sm.store(f)
        ids.append(f.id)
    return ids


# ---- Scenario 1: superseded facts excluded from cluster count --------
def test_detect_skips_superseded_facts_in_cluster(
    sm: SemanticMemory,
) -> None:
    """Cluster fact_count must reflect only live (superseded_by IS NULL)
    rows. 5 seeded - 2 superseded = 3 live.
    """
    ids = _seed_facts(sm, "project/x/sub", 5)
    assert len(ids) == 5

    # Supersede 2 of the 5 via direct SQL UPDATE (mark them as
    # superseded_by pointing at a sentinel id — value doesn't matter,
    # only NOT NULL does for the detect filter at consolidation.py:84).
    with sm._connect() as conn:  # noqa: SLF001
        for fid in ids[:2]:
            conn.execute(
                "UPDATE facts SET superseded_by = ? WHERE id = ?",
                ("REPLACED-BY-NEWER", fid),
            )

    clusters = detect_cluster_candidates(sm, min_size=3, prefix_depth=2)
    x_cluster = next(
        (c for c in clusters if c["topic_prefix"] == "project/x"), None,
    )
    assert x_cluster is not None, (
        f"cycle 145: expected a 'project/x' cluster with the 3 live facts, "
        f"got prefixes {[c['topic_prefix'] for c in clusters]!r}"
    )
    assert x_cluster["fact_count"] == 3, (
        f"cycle 145: cluster must drop the 2 superseded facts "
        f"(expected fact_count=3, got {x_cluster['fact_count']}). "
        f"fact_ids returned: {x_cluster['fact_ids']!r}"
    )
    # Sanity: superseded ids are absent from fact_ids
    for bad_id in ids[:2]:
        assert bad_id not in x_cluster["fact_ids"], (
            f"cycle 145: superseded fact {bad_id} leaked into cluster "
            f"fact_ids {x_cluster['fact_ids']!r}"
        )


# ---- Scenario 2: malformed JSON in source_episodes is tolerated ------
def test_auto_consolidate_tolerates_malformed_source_episodes_json(
    sm: SemanticMemory, mem: EpisodicMemory,
) -> None:
    """One sub-fact has a broken JSON string in source_episodes. The
    orchestrator's _source_episodes_for_facts catches json.JSONDecodeError
    (consolidation.py:205) and continues. End-to-end run must NOT crash
    and must persist the master node.
    """
    ids = _seed_facts(sm, "project/badjson/area", 6)

    # Corrupt source_episodes on one row with an invalid JSON literal.
    # The other rows keep their (valid JSON, possibly empty list) state.
    with sm._connect() as conn:  # noqa: SLF001
        conn.execute(
            "UPDATE facts SET source_episodes = ? WHERE id = ?",
            ("not-json-{broken", ids[0]),
        )
        # Give the other 5 a valid source_episodes list so the master
        # gets at least one real edge target alongside the broken row.
        for fid in ids[1:]:
            conn.execute(
                "UPDATE facts SET source_episodes = ? WHERE id = ?",
                (json.dumps([f"ep-stub-{fid[:8]}"]), fid),
            )

    # Must NOT raise — the bad row is silently dropped by the JSON guard.
    out = auto_consolidate(sm, mem, min_size=5, dry_run=False)

    assert out["masters_persisted"] >= 1, (
        f"cycle 145: malformed JSON in 1/6 sub-facts must not block "
        f"consolidation. masters_persisted expected ≥1, got {out!r}"
    )
    assert out["edges_created"] >= 1, (
        f"cycle 145: master should still wire ≥1 edge from the 5 valid "
        f"rows (or a self-edge fallback). Got {out!r}"
    )
    # Cross-check the master fact actually landed and the corrupted row
    # was not promoted by accident.
    with sm._connect() as conn:  # noqa: SLF001
        master_count = int(conn.execute(
            "SELECT COUNT(*) FROM facts "
            "WHERE topic LIKE ? AND superseded_by IS NULL",
            ("project/badjson/%auto-MASTER",),
        ).fetchone()[0])
    assert master_count == 1, (
        f"cycle 145: exactly 1 auto-MASTER fact must exist for "
        f"project/badjson, got {master_count}"
    )


# ---- Scenario 3: back-to-back idempotency (same-ms race) -------------
def test_auto_consolidate_back_to_back_is_idempotent(
    sm: SemanticMemory, mem: EpisodicMemory,
) -> None:
    """Two ``auto_consolidate(...)`` invocations fired back-to-back must
    not double-persist. The idempotency probe
    ``_cluster_already_consolidated`` (consolidation.py:169-182) is keyed
    on the master proposition prefix, not on a timestamp, so even if both
    calls land in the same millisecond the second must see the master
    written by the first and skip the cluster.
    """
    _seed_facts(sm, "project/race/area", 6)

    first = auto_consolidate(sm, mem, min_size=5, dry_run=False)
    # Second call: no sleep, fired immediately. Must be a clean no-op.
    second = auto_consolidate(sm, mem, min_size=5, dry_run=False)

    assert first["masters_persisted"] == 1, (
        f"cycle 145: first apply on a single 6-fact cluster must persist "
        f"exactly 1 master, got {first!r}"
    )
    assert second["masters_persisted"] == 0, (
        f"cycle 145: second back-to-back apply must persist 0 masters "
        f"(idempotency probe must fire). Got {second!r}. "
        f"This is the same-millisecond race guard."
    )
    assert second["edges_created"] == 0, (
        f"cycle 145: second run must not create new edges either. "
        f"Got {second!r}"
    )
    # And the cluster still gets DETECTED on the second pass — that's
    # the whole point of the LIKE probe: detect→skip, not detect→fail.
    assert second["clusters_detected"] >= 1, (
        f"cycle 145: second run must still detect the cluster (just skip "
        f"it). Got clusters_detected={second['clusters_detected']!r}"
    )
