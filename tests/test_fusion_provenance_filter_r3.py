"""Audit 3-round R3 #3 (correctness): the default-ON PPR/BM25 fusion must re-apply
the caller's PROVENANCE filters (exclude_legacy / min_status / include_conversational),
not just the scope + live filters.

The fusion fetches extra fact-ids from the WHOLE corpus. get(live_only=True) drops
superseded/orphaned/quarantined, but NOT legacy_unverified, low-min_status, or
unverified-conversational facts — which the SQL/cache path explicitly filters out
of the dense hits. With fusion default-ON, those lower-trust facts re-entered the
recall above the trust floor. The fix threads the filters into _maybe_fuse_ppr.
"""
from __future__ import annotations

import pytest

from verimem.entity_kg import Entity, EntityStore
from verimem.entity_populate import entity_kg_path_for
from verimem.semantic import Fact, SemanticMemory


@pytest.fixture(autouse=True)
def _no_floor(monkeypatch):
    monkeypatch.setenv("ENGRAM_PPR_FUSION_FLOOR", "0")
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "1")
    monkeypatch.setenv("ENGRAM_PPR_FUSION_BUDGET_S", "0")  # synchronous


def _link(sm: SemanticMemory, fact: Fact, entity: str) -> None:
    es = EntityStore(db_path=entity_kg_path_for(sm.db_path))
    eid = es.store(Entity(canonical_name=entity, type="module"))
    es.add_edge(eid, eid, "self", weight=1.0)
    es.link_fact(fact.id, eid)


def test_fusion_drops_legacy_when_exclude_legacy(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    legacy = Fact(proposition="legacy note about alpha_service", topic="t",
                  status="legacy_unverified", source_episodes=["e"])
    sm.store(legacy, embed="auto")
    _link(sm, legacy, "alpha_service")
    decoy = Fact(proposition="decoy", topic="t/d")
    sm.store(decoy, embed="auto")

    # without the filter the legacy fact may be fused in (PPR-seeded by entity);
    # with exclude_legacy it must be dropped from the fused pool.
    fused = sm._maybe_fuse_ppr(
        "tell me about alpha_service", [(decoy, 0.5)], 5, exclude_legacy=True)
    assert legacy.id not in {f.id for f, _ in fused}, \
        "exclude_legacy must drop a legacy_unverified fact re-pescato dal fusion"


def test_fusion_respects_min_status(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    low = Fact(proposition="low-trust note about beta_service", topic="t",
               status="model_claim", confidence=0.3, source_episodes=["e"])
    sm.store(low, embed="auto")
    _link(sm, low, "beta_service")
    decoy = Fact(proposition="decoy two", topic="t/d")
    sm.store(decoy, embed="auto")

    fused = sm._maybe_fuse_ppr(
        "tell me about beta_service", [(decoy, 0.5)], 5, min_status="verified")
    assert low.id not in {f.id for f, _ in fused}, \
        "min_status=verified must drop a model_claim fused in below the floor"
