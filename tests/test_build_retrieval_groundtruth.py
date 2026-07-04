"""Cycle #113.A (2026-05-17) — build_groundtruth tests.

Tested end-to-end via seeded EpisodicMemory + SemanticMemory. The
fact->episode reverse-index is the contract being locked: every fact
whose source_episodes contains the episode id must appear in that
episode's expected_fact_ids set.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmark.build_retrieval_groundtruth import build_groundtruth
from engram.memory import Episode, EpisodicMemory
from engram.semantic import Fact, SemanticMemory


@pytest.fixture
def stores(tmp_path: Path) -> tuple[EpisodicMemory, SemanticMemory]:
    ep = EpisodicMemory(db_path=tmp_path / "episodes.db")
    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    return ep, sm


def _seed_ep(ep: EpisodicMemory, ep_id: str, task_text: str) -> Episode:
    """Insert a minimal episode and return it for chaining."""
    episode = Episode(
        id=ep_id,
        task_id=f"task-{ep_id}",
        task_text=task_text,
        outcome="success",
        final_answer="ok",
    )
    ep.store(episode)
    return episode


def _seed_fact(
    sm: SemanticMemory, fact_id: str, prop: str,
    source_episodes: list[str],
) -> None:
    sm.store(Fact(
        id=fact_id, proposition=prop, topic="test",
        confidence=0.9, source_episodes=source_episodes,
    ))


def test_groundtruth_empty_corpus(
    stores: tuple[EpisodicMemory, SemanticMemory],
) -> None:
    ep, sm = stores
    envelope = build_groundtruth(episodes=ep, semantic=sm)
    assert envelope["n_queries"] == 0
    assert envelope["n_facts_total"] == 0
    assert envelope["n_episodes_total"] == 0
    assert envelope["queries"] == []


def test_groundtruth_one_episode_one_fact(
    stores: tuple[EpisodicMemory, SemanticMemory],
) -> None:
    ep, sm = stores
    _seed_ep(ep, "e1", "what is the NEXUS test count?")
    _seed_fact(sm, "f1", "NEXUS has 17280 tests", ["e1"])
    envelope = build_groundtruth(episodes=ep, semantic=sm)
    assert envelope["n_queries"] == 1
    pair = envelope["queries"][0]
    assert pair["episode_id"] == "e1"
    assert pair["query"] == "what is the NEXUS test count?"
    assert pair["expected_fact_ids"] == ["f1"]
    assert pair["n_expected"] == 1


def test_groundtruth_multiple_facts_per_episode(
    stores: tuple[EpisodicMemory, SemanticMemory],
) -> None:
    ep, sm = stores
    _seed_ep(ep, "e1", "describe cycle 109 provenance schema migration")
    _seed_fact(sm, "f1", "verified_by column added", ["e1"])
    _seed_fact(sm, "f2", "status column with enum", ["e1"])
    _seed_fact(sm, "f3", "source_signature optional hash", ["e1"])
    envelope = build_groundtruth(episodes=ep, semantic=sm)
    assert envelope["n_queries"] == 1
    assert set(envelope["queries"][0]["expected_fact_ids"]) == {"f1", "f2", "f3"}


def test_groundtruth_shared_fact_across_episodes(
    stores: tuple[EpisodicMemory, SemanticMemory],
) -> None:
    """A fact with multiple source_episodes must appear in EACH episode's
    expected set."""
    ep, sm = stores
    _seed_ep(ep, "e1", "first reference to the schema")
    _seed_ep(ep, "e2", "second reference to the same schema")
    _seed_fact(sm, "shared", "verified_by column added", ["e1", "e2"])
    envelope = build_groundtruth(episodes=ep, semantic=sm)
    by_ep = {p["episode_id"]: p["expected_fact_ids"] for p in envelope["queries"]}
    assert by_ep["e1"] == ["shared"]
    assert by_ep["e2"] == ["shared"]


def test_groundtruth_skips_episodes_without_facts(
    stores: tuple[EpisodicMemory, SemanticMemory],
) -> None:
    """An episode with no key_facts derived (no fact references it)
    must NOT appear in the ground truth — useless for the bench."""
    ep, sm = stores
    _seed_ep(ep, "e_with", "this one has a key_fact derived from it")
    _seed_ep(ep, "e_without", "this one is just narrative, no key_fact")
    _seed_fact(sm, "f1", "a key fact", ["e_with"])
    envelope = build_groundtruth(episodes=ep, semantic=sm)
    assert envelope["n_queries"] == 1
    assert envelope["queries"][0]["episode_id"] == "e_with"


def test_groundtruth_skips_short_task_text(
    stores: tuple[EpisodicMemory, SemanticMemory],
) -> None:
    ep, sm = stores
    _seed_ep(ep, "e_short", "ok")  # 2 chars < default 8
    _seed_ep(ep, "e_long", "a proper task description here please")
    _seed_fact(sm, "f1", "p1", ["e_short"])
    _seed_fact(sm, "f2", "p2", ["e_long"])
    envelope = build_groundtruth(
        episodes=ep, semantic=sm, min_query_chars=8,
    )
    ids = [p["episode_id"] for p in envelope["queries"]]
    assert "e_long" in ids
    assert "e_short" not in ids


def test_groundtruth_max_queries_caps_output(
    stores: tuple[EpisodicMemory, SemanticMemory],
) -> None:
    ep, sm = stores
    for i in range(10):
        _seed_ep(ep, f"e{i:02d}", f"long task description number {i}")
        _seed_fact(sm, f"f{i:02d}", f"prop {i}", [f"e{i:02d}"])
    envelope = build_groundtruth(
        episodes=ep, semantic=sm, max_queries=3,
    )
    assert envelope["n_queries"] == 3


def test_groundtruth_ordering_is_deterministic(
    stores: tuple[EpisodicMemory, SemanticMemory],
) -> None:
    ep, sm = stores
    for ep_id in ("e-zz", "e-aa", "e-mm"):
        _seed_ep(ep, ep_id, f"task for {ep_id}")
        _seed_fact(sm, f"f-{ep_id}", "p", [ep_id])
    envelope = build_groundtruth(episodes=ep, semantic=sm)
    ids = [p["episode_id"] for p in envelope["queries"]]
    assert ids == sorted(ids), f"non-deterministic order: {ids}"


def test_groundtruth_envelope_serializes_to_json(
    stores: tuple[EpisodicMemory, SemanticMemory], tmp_path: Path,
) -> None:
    """End-to-end round-trip via JSON (catches any non-serializable
    type that sneaks in)."""
    ep, sm = stores
    _seed_ep(ep, "e1", "serializable check")
    _seed_fact(sm, "f1", "p", ["e1"])
    envelope = build_groundtruth(episodes=ep, semantic=sm)
    out = tmp_path / "gt.json"
    out.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    back = json.loads(out.read_text(encoding="utf-8"))
    assert back["n_queries"] == 1
    assert back["queries"][0]["expected_fact_ids"] == ["f1"]
