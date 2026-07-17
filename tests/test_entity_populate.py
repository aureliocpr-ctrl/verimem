"""End-to-end entity-live pipeline: facts -> KG -> PPR returns real hits.

This is THE contract that flips entity retrieval from built-not-live
(0 hits on real data, as the README declared) to live: populate from a
semantic.db, then Personalized PageRank must surface the related fact.
"""
from __future__ import annotations

from pathlib import Path

from verimem.entity_kg import EntityStore
from verimem.entity_populate import populate_entity_graph
from verimem.semantic import Fact, SemanticMemory


def _corpus(tmp_path: Path) -> Path:
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    sm = SemanticMemory(db_path=db)
    sm.store(Fact(
        proposition=(
            "il reranker in engram/semantic.py usa McNemar su LongMemEval "
            "per la validazione del default"
        ),
        topic="project/engram/retrieval", source_episodes=["e1"],
    ), embed="sync")
    sm.store(Fact(
        proposition=(
            "LongMemEval misura recall di sessione; il harness comparativo "
            "vive in benchmark/comparative_retrieval.py"
        ),
        topic="project/engram/bench", source_episodes=["e2"],
    ), embed="sync")
    sm.store(Fact(
        proposition="la carbonara richiede guanciale e pecorino",
        topic="cucina/ricette", source_episodes=["e3"],
    ), embed="sync")
    return db


def test_populate_links_and_wires_edges(tmp_path):
    db = _corpus(tmp_path)
    kg = EntityStore(db_path=tmp_path / "kg" / "entity_kg.db")
    stats = populate_entity_graph(db, kg)
    assert stats["facts_scanned"] == 3
    assert stats["facts_with_entities"] >= 2, stats
    assert stats["entities_total"] >= 3, stats
    assert stats["edges_wired"] > 0, "PPR needs co-occurrence edges"


def test_populate_is_idempotent(tmp_path):
    db = _corpus(tmp_path)
    kg = EntityStore(db_path=tmp_path / "kg" / "entity_kg.db")
    s1 = populate_entity_graph(db, kg)
    s2 = populate_entity_graph(db, kg)
    assert s2["entities_total"] == s1["entities_total"], (
        "re-run must converge, not duplicate entities"
    )


def test_ppr_surfaces_related_fact_after_populate(tmp_path):
    """The built-not-live gap, closed: PPR from a real entity must return
    the facts it appears in (>0 hits on populated data)."""
    db = _corpus(tmp_path)
    kg = EntityStore(db_path=tmp_path / "kg" / "entity_kg.db")
    populate_entity_graph(db, kg)

    seed = kg.get_by_name("LongMemEval")
    assert seed is not None, "extractor must have created LongMemEval"
    out = kg.ppr([seed.id], k=10)
    assert out["graph_size"]["edges"] > 0
    assert len(out["facts"]) > 0, "PPR must surface linked facts (was 0)"
    # Multi-hop sanity: LongMemEval co-occurs with the comparative harness
    # path in fact 2 — the harness entity must rank among PPR results.
    ranked_ids = {r["entity_id"] for r in out["ranked"]}
    harness = kg.get_by_name("benchmark/comparative_retrieval.py")
    assert harness is not None
    assert harness.id in ranked_ids, (
        "1-hop neighbour must appear in PPR ranking"
    )


def test_bad_fact_does_not_kill_backfill(tmp_path):
    db = _corpus(tmp_path)
    kg = EntityStore(db_path=tmp_path / "kg" / "entity_kg.db")

    calls = {"n": 0}

    def _flaky(text: str):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom on first fact")
        from verimem.entity_extract_lite import extract_entities_lite
        return extract_entities_lite(text)

    stats = populate_entity_graph(db, kg, extract_fn=_flaky)
    assert stats["facts_scanned"] == 3
    assert stats["facts_with_entities"] >= 1, (
        "one bad fact must not kill the rest of the backfill"
    )
