"""PPR fact ranking (2026-06-10) — from wide union to useful top-k.

After the entity-live merge the KG is real (7 570 entities) but
``ppr()['facts']`` is the UNORDERED union of every fact linked to any
top-k entity — the live probe for "Engram" returned 1 039 facts, which
no recall consumer can use. HippoRAG's actual retrieval signal is the
graph score: rank each fact by the SUM of the PPR scores of the top-k
entities that link it (a fact touched by several high-score entities
beats a fact hanging off one hub).

Contract pinned here:
  - ppr() and ppr_weighted() return a new ``facts_ranked`` list of
    {fact_id, score, n_entities}, sorted by (-score, fact_id), capped
    at ``k_facts`` (default 20);
  - the legacy ``facts`` union is UNCHANGED (back-compat: callers and
    the backfill probe rely on it);
  - empty graph → ``facts_ranked == []``.

RED marker: the ``facts_ranked`` key does not exist pre-fix.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engram.entity_kg import Entity, EntityStore


@pytest.fixture
def kg(tmp_path: Path) -> EntityStore:
    """A tiny graph with a known multi-hop winner.

    Entities: hub, a, b (all interlinked so PPR gives them mass from
    the seed), plus an isolated noise entity.
    Facts:
      f_multi  -> linked to hub AND a AND b   (sum of 3 scores: top)
      f_two    -> linked to hub AND a          (sum of 2 scores)
      f_single -> linked to hub only           (1 score)
      f_noise  -> linked to the isolated entity (not in top-k mass)
    """
    store = EntityStore(db_path=tmp_path / "kg.db")
    with store.session():
        hub = store.store(Entity(canonical_name="hub_thing", type="code"))
        a = store.store(Entity(canonical_name="alpha_thing", type="code"))
        b = store.store(Entity(canonical_name="beta_thing", type="code"))
        noise = store.store(Entity(canonical_name="noise_thing", type="code"))
        for src, dst in ((hub, a), (a, hub), (hub, b), (b, hub), (a, b), (b, a)):
            store.add_edge(src, dst, "co_occurs", weight=1.0,
                           source_fact_id="seed")
        for fid, eids in (
            ("f_multi", (hub, a, b)),
            ("f_two", (hub, a)),
            ("f_single", (hub,)),
            ("f_noise", (noise,)),
        ):
            for eid in eids:
                store.link_fact(fid, eid)
    store._ids = {"hub": hub, "a": a, "b": b, "noise": noise}  # type: ignore[attr-defined]
    return store


def test_facts_ranked_key_present(kg: EntityStore) -> None:
    out = kg.ppr([kg._ids["hub"]], k=3)  # type: ignore[attr-defined]
    assert "facts_ranked" in out, "ppr() must expose the ranked fact list"


def test_multi_entity_fact_outranks_single(kg: EntityStore) -> None:
    out = kg.ppr([kg._ids["hub"]], k=3)  # type: ignore[attr-defined]
    ranked = out["facts_ranked"]
    ids = [r["fact_id"] for r in ranked]
    assert ids[0] == "f_multi", f"3-entity fact must rank first, got {ids}"
    assert ids.index("f_multi") < ids.index("f_single")
    assert ids.index("f_two") < ids.index("f_single")


def test_scores_are_summed_entity_scores(kg: EntityStore) -> None:
    out = kg.ppr([kg._ids["hub"]], k=3)  # type: ignore[attr-defined]
    ent_score = {r["entity_id"]: r["score"] for r in out["ranked"]}
    by_id = {r["fact_id"]: r for r in out["facts_ranked"]}
    expected_multi = sum(
        ent_score[kg._ids[n]] for n in ("hub", "a", "b")  # type: ignore[attr-defined]
    )
    assert by_id["f_multi"]["score"] == pytest.approx(expected_multi)
    assert by_id["f_multi"]["n_entities"] == 3
    assert by_id["f_single"]["n_entities"] == 1


def test_k_facts_caps_output(kg: EntityStore) -> None:
    out = kg.ppr([kg._ids["hub"]], k=3, k_facts=2)  # type: ignore[attr-defined]
    assert len(out["facts_ranked"]) == 2
    assert out["facts_ranked"][0]["fact_id"] == "f_multi"


def test_legacy_union_unchanged(kg: EntityStore) -> None:
    """facts (union, insertion-ordered) must stay byte-identical to the
    pre-ranking behavior — consumers depend on it."""
    out = kg.ppr([kg._ids["hub"]], k=3)  # type: ignore[attr-defined]
    facts = out["facts"]
    assert set(facts) == {"f_multi", "f_two", "f_single"}
    # union semantics: every fact appears exactly once
    assert len(facts) == len(set(facts))


def test_deterministic_tiebreak_by_fact_id(tmp_path: Path) -> None:
    """Two facts linked to the SAME single entity have equal scores —
    order must be fact_id asc, stable across runs."""
    store = EntityStore(db_path=tmp_path / "kg.db")
    with store.session():
        e = store.store(Entity(canonical_name="solo_thing", type="code"))
        store.link_fact("f_bbb", e)
        store.link_fact("f_aaa", e)
    out = store.ppr([e], k=1)
    ids = [r["fact_id"] for r in out["facts_ranked"]]
    assert ids == ["f_aaa", "f_bbb"]


def test_empty_graph_returns_empty_ranked(tmp_path: Path) -> None:
    store = EntityStore(db_path=tmp_path / "kg.db")
    out = store.ppr(["nope"], k=5)
    assert out["facts_ranked"] == []


def test_ppr_weighted_same_contract(kg: EntityStore) -> None:
    hub = kg._ids["hub"]  # type: ignore[attr-defined]
    out = kg.ppr_weighted({hub: 1.0}, k=3)
    assert "facts_ranked" in out
    ids = [r["fact_id"] for r in out["facts_ranked"]]
    assert ids[0] == "f_multi"
