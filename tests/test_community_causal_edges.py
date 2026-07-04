"""community_detector causal-edge branch must actually work (scan #316/#170).

Three stacked bugs made `edges_source in ("causal","both")` a permanent
no-op (verified live: 442 causal_edges, 0 ever reached the graph):
  1. the query ran `SELECT src,dst FROM causal_edges` on SEMANTIC.db,
     where the table does not even exist -> OperationalError swallowed;
  2. real columns are src_episode_id/dst_episode_id, not src/dst;
  3. causal_edges link EPISODE ids while the graph is keyed by FACT ids.

The fix reads causal_edges from episodes.db with the right columns and
projects each episode->episode edge onto the fact graph via
facts.source_episodes (episode -> facts mapping). Backward compatible:
episodes_db defaults to the sibling ../episodes/episodes.db of semantic.db.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from engram.community_detector import _load_graph
from engram.episode import Episode
from engram.memory import EpisodicMemory
from engram.semantic import Fact, SemanticMemory


def _build(tmp_path: Path):
    sem = tmp_path / "semantic" / "semantic.db"
    epdb = tmp_path / "episodes" / "episodes.db"
    sem.parent.mkdir(parents=True)
    epdb.parent.mkdir(parents=True)

    mem = EpisodicMemory(db_path=epdb)
    e1, e2 = Episode(task_text="t1", outcome="success"), Episode(
        task_text="t2", outcome="success")
    mem.store(e1)
    mem.store(e2)
    mem.add_causal_edge(e1.id, e2.id, via_skill_id="s1", weight=1.0)

    sm = SemanticMemory(db_path=sem)
    # Two facts, each rooted in one of the two causally-linked episodes,
    # on UNRELATED topics + no lineage_to so ONLY the causal edge can join.
    f1 = Fact(proposition="fact from episode one about alpha", topic="t/a",
              source_episodes=[e1.id], status="model_claim")
    f2 = Fact(proposition="fact from episode two about beta", topic="t/b",
              source_episodes=[e2.id], status="model_claim")
    sm.store(f1)
    sm.store(f2)
    return sem, epdb, f1.id, f2.id


def test_causal_branch_projects_episode_edges_onto_facts(tmp_path):
    sem, epdb, f1, f2 = _build(tmp_path)
    g = _load_graph(sem, "causal", episodes_db=epdb)
    assert g.has_edge(f1, f2), (
        "an episode->episode causal edge must become a fact<->fact edge "
        "via source_episodes (was a permanent no-op)"
    )


def test_causal_branch_autoderives_sibling_episodes_db(tmp_path):
    sem, epdb, f1, f2 = _build(tmp_path)
    # No episodes_db passed: must derive ../episodes/episodes.db so the
    # existing 2-arg callers get the fix for free.
    g = _load_graph(sem, "causal")
    assert g.has_edge(f1, f2)


def test_causal_branch_no_episodes_db_degrades_gracefully(tmp_path):
    sem, epdb, f1, f2 = _build(tmp_path)
    g = _load_graph(sem, "causal", episodes_db=tmp_path / "nope.db")
    # No edges (graceful), but nodes still present — never raises.
    assert g.number_of_nodes() == 2
    assert g.number_of_edges() == 0


def test_lineage_only_unaffected_by_causal_fix(tmp_path):
    sem, epdb, f1, f2 = _build(tmp_path)
    g = _load_graph(sem, "lineage", episodes_db=epdb)
    # f1/f2 have no lineage_to between them -> no edge on the lineage path.
    assert not g.has_edge(f1, f2)


def test_minimal_schema_without_source_episodes_degrades(tmp_path):
    """Synthetic/legacy DBs (e.g. the second_pass_louvain fixtures) create a
    minimal `facts` table WITHOUT source_episodes. The causal SELECT must
    fall back to lineage-only instead of exploding (the unguarded column
    broke detect_communities into empty results: 'master max size 0')."""
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE facts (id TEXT PRIMARY KEY, topic TEXT, proposition "
        "TEXT, embedding BLOB, lineage_to TEXT, superseded_by TEXT, "
        "status TEXT)"
    )
    conn.execute("INSERT INTO facts (id, lineage_to) VALUES ('a', NULL)")
    conn.execute("INSERT INTO facts (id, lineage_to) VALUES ('b', 'a')")
    conn.commit()
    conn.close()

    g = _load_graph(db, "both")  # must not raise
    assert g.number_of_nodes() == 2
    assert g.has_edge("a", "b"), "lineage edges must survive the fallback"
