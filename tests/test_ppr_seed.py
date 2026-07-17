"""Query-auto-seeded entity-PPR fact ranklist (competitor-gap step 2a, 2026-06-14).

Closes HippoRAG-2's seeding gap: a free-text query -> entities -> PPR -> fact ids,
so a gold fact sharing an entity with the query is surfaced even when the bi-encoder
misses it. Fail-soft so the future RRF fusion degrades to pure cosine.
"""
from __future__ import annotations

from verimem.entity_kg import Entity, EntityStore
from verimem.ppr_seed import ppr_seeded_fact_ids


def _store(tmp_path):
    return EntityStore(db_path=tmp_path / "ekg.db")


def test_fail_soft_paths_return_empty(tmp_path):
    es = _store(tmp_path)
    assert ppr_seeded_fact_ids("", es) == []          # empty query
    assert ppr_seeded_fact_ids("anything", None) == []  # no store
    assert ppr_seeded_fact_ids(None, es) == []          # None query
    # a query whose entities resolve to nothing in the store -> []
    assert ppr_seeded_fact_ids("what about nonexistent_module here", es) == []


def test_auto_seed_surfaces_entity_linked_fact(tmp_path):
    es = _store(tmp_path)
    a = es.store(Entity(canonical_name="alpha_service", type="module"))
    b = es.store(Entity(canonical_name="beta_service", type="module"))
    es.add_edge(a, b, "rel", weight=1.0)
    es.link_fact("factX", a)  # factX is linked to alpha_service

    # the query mentions alpha_service -> PPR seeds it -> factX ranked
    ids = ppr_seeded_fact_ids("what changed in alpha_service recently", es)
    assert "factX" in ids


def test_camelcase_query_resolves_and_ranks(tmp_path):
    es = _store(tmp_path)
    a = es.store(Entity(canonical_name="AlphaService", type="code_camel"))
    es.link_fact("factCamel", a)
    es.add_edge(a, a, "self", weight=1.0)  # ensure a node/edge exists for PPR
    ids = ppr_seeded_fact_ids("tell me about AlphaService internals", es)
    assert "factCamel" in ids


def test_unresolved_entities_degrade_to_empty(tmp_path):
    es = _store(tmp_path)
    # entities are extracted (user_auth) but never stored -> no seeds -> []
    assert ppr_seeded_fact_ids("the user_auth module broke", es) == []
