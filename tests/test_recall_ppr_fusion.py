"""Opt-in PPR fusion in recall (competitor-gap step 2b wiring, 2026-06-14).

ENGRAM_PPR_FUSION (default OFF) keeps recall byte-identical (pure cosine + CE-rerank,
zero regression). ON fuses a query-auto-seeded entity-PPR ranklist into the candidate
pool via RRF before the rerank, surfacing a fact that shares an entity with the query
even when the bi-encoder missed it (the HippoRAG-2 gap) — fail-soft throughout.
"""
from __future__ import annotations

import pytest

from engram.entity_kg import Entity, EntityStore
from engram.entity_populate import entity_kg_path_for
from engram.semantic import Fact, SemanticMemory


@pytest.fixture(autouse=True)
def _disable_corpus_floor(monkeypatch):
    """Dopo il flip default-ON (2026-06-15) il corpus-floor (default 50)
    salterebbe la fusione sui corpus minimi di QUESTI test, dove la fusione E' il
    soggetto sotto test. Disabilitiamo il floor (FLOOR=0) per tutto il file."""
    monkeypatch.setenv("ENGRAM_PPR_FUSION_FLOOR", "0")


def test_fusion_off_is_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "0")  # OFF esplicito (post flip default-ON)
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    hits = [(Fact(proposition="anything", topic="t"), 0.9)]
    # OFF → the exact same list object is returned (no work, no regression).
    assert sm._maybe_fuse_ppr("query about alpha_service", hits, 5) is hits


def test_fusion_on_surfaces_entity_linked_fact_cosine_missed(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "1")
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")

    # gold fact: persisted so self.get() can fetch it; its lexical content is
    # unrelated to the query (simulating a cosine miss).
    gold = Fact(proposition="lorem ipsum unrelated content", topic="t/gold")
    sm.store(gold, embed="auto")

    # populate the entity store at the SAME path sm's recall path uses, linking
    # the gold fact to an entity the query will mention.
    es = EntityStore(db_path=entity_kg_path_for(sm.db_path))
    eid = es.store(Entity(canonical_name="alpha_service", type="module"))
    es.add_edge(eid, eid, "self", weight=1.0)
    es.link_fact(gold.id, eid)

    # dense pool WITHOUT the gold fact (the bi-encoder missed it).
    decoy = Fact(proposition="some decoy", topic="t/decoy")
    sm.store(decoy, embed="auto")
    dense = [(decoy, 0.5)]

    fused = sm._maybe_fuse_ppr("tell me about alpha_service", dense, 5)
    ids = {f.id for f, _ in fused}
    assert gold.id in ids, "PPR fusion must surface the entity-linked fact cosine missed"
    assert decoy.id in ids, "the dense hit is preserved"


def test_fusion_on_no_entities_is_failsoft(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "1")
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    hits = [(Fact(proposition="x", topic="t"), 0.7)]
    # a query with no resolvable entities → dense pool unchanged.
    out = sm._maybe_fuse_ppr("nothing resolvable here", hits, 5)
    assert [f.id for f, _ in out] == [f.id for f, _ in hits]


def test_recall_end_to_end_fusion_surfaces_gold_cosine_missed(tmp_path, monkeypatch):
    """END-TO-END through recall() (closes the critic's wiring-untested caveat):
    a gold fact lexically far from the query (cosine miss) but entity-linked is
    NOT in the top-k with fusion OFF, and IS with fusion ON. Rerank disabled to
    isolate the fusion signal from the CE-rerank's text scoring."""
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")  # isolate fusion from CE-rerank
    monkeypatch.setattr("engram.bm25_rank.bm25_fact_ids", lambda *a, **k: [])  # isolate PPR
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")

    # gold: lexically unrelated to the query → low cosine; entity-linked below.
    gold = Fact(proposition="the quarterly budget spreadsheet was archived in march",
                topic="t/gold")
    sm.store(gold, embed="sync")
    # decoys: lexically close to the query (high cosine), no entity link.
    for i in range(4):
        sm.store(Fact(proposition=f"alpha service deployment runbook step {i}",
                      topic="t/decoy"), embed="sync")

    es = EntityStore(db_path=entity_kg_path_for(sm.db_path))
    eid = es.store(Entity(canonical_name="alpha_service", type="module"))
    es.add_edge(eid, eid, "self", weight=1.0)
    es.link_fact(gold.id, eid)

    q = "alpha_service deployment runbook"

    monkeypatch.setenv("ENGRAM_PPR_FUSION", "0")  # OFF esplicito (post flip default-ON)
    off_ids = {f.id for f, _ in sm.recall(q, k=3)}

    monkeypatch.setenv("ENGRAM_PPR_FUSION", "1")
    sm._recall_es = None  # rebuild the lazy entity store under the flag
    on_ids = {f.id for f, _ in sm.recall(q, k=3)}

    assert gold.id not in off_ids, "baseline: the lexically-far gold is missed by cosine"
    assert gold.id in on_ids, "fusion: entity-PPR surfaces the gold the cosine missed"


def test_recall_fusion_runs_after_rerank_so_ppr_fact_survives(tmp_path, monkeypatch):
    """fusion×rerank fix (2026-06-14): with the CE-rerank ON, a PPR-only fact still
    surfaces because the fusion runs AFTER the rerank — PPR-only facts never reach
    the text-based CE scorer that would drown a text-distant fact. The rerank is
    stubbed to a deterministic identity (CE 'on' but no model load)."""
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "1")
    monkeypatch.setattr("engram.bm25_rank.bm25_fact_ids", lambda *a, **k: [])  # isolate PPR
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    # CE-rerank ON but deterministic: return the pool unchanged (top-k).
    monkeypatch.setattr(type(sm), "_rerank_stage2", lambda self, q, h, k: h[:k])

    gold = Fact(proposition="unrelated archival note about quarterly budgets",
                topic="t/gold")
    sm.store(gold, embed="sync")
    for i in range(3):
        sm.store(Fact(proposition=f"alpha service runbook step {i}", topic="t/d"),
                 embed="sync")
    es = EntityStore(db_path=entity_kg_path_for(sm.db_path))
    eid = es.store(Entity(canonical_name="alpha_service", type="module"))
    es.add_edge(eid, eid, "self", weight=1.0)
    es.link_fact(gold.id, eid)

    ids = {f.id for f, _ in sm.recall("alpha_service runbook deploy", k=3)}
    assert gold.id in ids, (
        "fusion-after-rerank: the entity-linked gold survives even with the rerank on"
    )


def test_recall_fusion_bm25_surfaces_exact_token(tmp_path, monkeypatch):
    """3-signal fusion (step 3b): a fact carrying an exact rare token the query asks
    for is surfaced via the BM25 channel even when cosine ranks it below decoys."""
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")

    # target carries the rare token but is otherwise lexically far from the query.
    target = Fact(proposition="archived snapshot deadcafe9999 kept in cold storage",
                  topic="t/x")
    sm.store(target, embed="sync")
    for i in range(4):  # decoys share the query's common word, not the rare token
        sm.store(Fact(proposition=f"migration status progress note {i}", topic="t/d"),
                 embed="sync")

    q = "migration status deadcafe9999"
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "0")  # OFF esplicito (post flip default-ON)
    off = {f.id for f, _ in sm.recall(q, k=3)}
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "1")
    sm._recall_es = None
    on = {f.id for f, _ in sm.recall(q, k=3)}

    assert target.id not in off, "baseline: cosine ranks the decoys over the rare-token fact"
    assert target.id in on, "fusion: the BM25 channel surfaces the exact-token fact"


def test_fusion_does_not_resurrect_superseded_fact(tmp_path, monkeypatch):
    """Correctness (flip default-ON 2026-06-15, critic note 1bb59e02): il fusion
    fetcha gli extra-id PPR/BM25 via self.get, che di DEFAULT (live_only=False)
    ritorna anche i fatti superseded/orphaned/quarantined. Un fatto RITRATTATO
    entity-linked NON deve riapparire nel recall via il canale PPR/BM25 — stesso
    leak gia' chiuso per anchor/entity in HIGH-2 (get(live_only=True))."""
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "1")
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")

    # gold entity-linked ma RITRATTATO: superseduto da un fatto a trust piu' alto.
    gold = Fact(proposition="old retracted note about alpha_service",
                topic="t/gold", status="model_claim")
    sm.store(gold, embed="auto")
    newer = Fact(proposition="current note about alpha_service",
                 topic="t/gold", status="verified")
    sm.store(newer, embed="auto")
    sm.supersede(gold.id, newer.id, reason="updated")  # gold -> superseded_by

    es = EntityStore(db_path=entity_kg_path_for(sm.db_path))
    eid = es.store(Entity(canonical_name="alpha_service", type="module"))
    es.add_edge(eid, eid, "self", weight=1.0)
    es.link_fact(gold.id, eid)  # il link punta ancora al gold ritrattato

    decoy = Fact(proposition="some decoy", topic="t/decoy")
    sm.store(decoy, embed="auto")
    fused = sm._maybe_fuse_ppr("tell me about alpha_service", [(decoy, 0.5)], 5)
    ids = {f.id for f, _ in fused}
    assert gold.id not in ids, (
        "il fusion non deve resuscitare un fatto superseded via PPR/BM25"
    )


def test_fusion_does_not_resurrect_orphaned_fact(tmp_path, monkeypatch):
    """L'altro ramo di get(live_only=True): un fatto ORPHANED (scrubbed dal
    reconciler L2) entity-linked non deve rientrare via il fusion."""
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "1")
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")

    gold = Fact(proposition="orphaned note about beta_service", topic="t/gold")
    sm.store(gold, embed="auto")
    sm.mark_orphaned(gold.id, reason="L2 reconciler scrub")

    es = EntityStore(db_path=entity_kg_path_for(sm.db_path))
    eid = es.store(Entity(canonical_name="beta_service", type="module"))
    es.add_edge(eid, eid, "self", weight=1.0)
    es.link_fact(gold.id, eid)

    decoy = Fact(proposition="some decoy", topic="t/decoy")
    sm.store(decoy, embed="auto")
    fused = sm._maybe_fuse_ppr("tell me about beta_service", [(decoy, 0.5)], 5)
    ids = {f.id for f, _ in fused}
    assert gold.id not in ids, (
        "il fusion non deve resuscitare un fatto orphaned via PPR/BM25"
    )
