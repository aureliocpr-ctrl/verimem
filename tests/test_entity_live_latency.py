"""Entity-live latency hardening (2026-06-10) — CI regression fix.

The first wiring commit (93bf114) made store() pay the EntityStore init
(mkdir + 6 schema migrations) on EVERY SemanticMemory even when the fact
extracts zero entities, and ~76 connection open/close per fact when it
does extract — measured 122 ms/store locally, and 4.2 s (> the 3.0 s
anti-hang guard of test_store_auto_defers_under_slow_encode_no_hang) on
the cold windows-py3.11 CI runner.

Pins the two latency fixes:
  - lazy-skip: a fact with no extractable entities must never touch /
    create the KG db at all (extract is a pure ~1 ms regex pass);
  - EntityStore.session(): one shared connection per ingest batch,
    thread-isolated (store_within_budget runs store() on daemon threads),
    commit on exit, rollback on error, nested re-use.

RED marker: EntityStore.session must exist; store() must not create the
KG dir for entity-less facts.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from verimem.entity_kg import Entity, EntityStore
from verimem.entity_populate import (
    entity_kg_path_for,
    populate_entities_for_fact,
)
from verimem.semantic import Fact, SemanticMemory

ENTITY_PROP = "community_detector fix shipped in engram/semantic.py via TDD"
PLAIN_PROP = "hang-safety integration"  # extracts nothing (no snake/path/Proper)


# ── lazy-skip: entity-less store must never touch the KG ────────────────────

def test_store_entityless_never_creates_kg(tmp_path: Path) -> None:
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    mem = SemanticMemory(db_path=db)
    mem.store(Fact(proposition=PLAIN_PROP, topic="t"), embed="defer")
    kg_path = entity_kg_path_for(db)
    assert not kg_path.parent.exists(), (
        "zero-entity store must skip EntityStore init entirely "
        "(the init cost broke the CI anti-hang guard)"
    )
    # the fact itself persisted normally
    assert any(f.proposition == PLAIN_PROP for f in mem.list_facts())


def test_store_with_entities_still_populates(tmp_path: Path) -> None:
    """The lazy-skip must not break the populated path."""
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    mem = SemanticMemory(db_path=db)
    f = Fact(proposition=ENTITY_PROP, topic="t")
    mem.store(f, embed="defer")
    kg = EntityStore(db_path=entity_kg_path_for(db))
    e = kg.get_by_name("community_detector")
    assert e is not None
    assert f.id in kg.facts_for_entity(e.id)


# ── EntityStore.session(): one connection per batch ─────────────────────────

def test_session_writes_visible_after_exit(tmp_path: Path) -> None:
    kg = EntityStore(db_path=tmp_path / "kg.db")
    with kg.session():
        eid_a = kg.store(Entity(canonical_name="alpha_thing", type="code"))
        eid_b = kg.store(Entity(canonical_name="beta_thing", type="code"))
        kg.link_fact("f1", eid_a)
        kg.add_edge(eid_a, eid_b, "co_occurs", weight=1.0, source_fact_id="f1")
    assert kg.get_by_name("alpha_thing") is not None
    assert kg.facts_for_entity(eid_a) == ["f1"]
    assert any(e["dst_entity"] == eid_b for e in kg.edges_from(eid_a))


def test_session_reads_see_uncommitted_writes(tmp_path: Path) -> None:
    """store() dedup does SELECT-then-INSERT — inside one session the
    second store of the same name must see the first (same connection)."""
    kg = EntityStore(db_path=tmp_path / "kg.db")
    with kg.session():
        e1 = kg.store(Entity(canonical_name="gamma_thing", type="code"))
        e2 = kg.store(Entity(canonical_name="gamma_thing", type="code"))
    assert e1 == e2, "dedup must work within a session"
    assert kg.count() == 1


def test_session_rolls_back_on_error(tmp_path: Path) -> None:
    kg = EntityStore(db_path=tmp_path / "kg.db")
    try:
        with kg.session():
            kg.store(Entity(canonical_name="doomed_thing", type="code"))
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert kg.get_by_name("doomed_thing") is None, (
        "an aborted session must not leave partial writes"
    )


def test_session_nested_reuses_outer(tmp_path: Path) -> None:
    kg = EntityStore(db_path=tmp_path / "kg.db")
    with kg.session():
        kg.store(Entity(canonical_name="outer_thing", type="code"))
        with kg.session():  # nested: must reuse, not deadlock/close
            kg.store(Entity(canonical_name="inner_thing", type="code"))
        # outer session still usable after the nested one exits
        kg.store(Entity(canonical_name="after_thing", type="code"))
    assert kg.count() == 3


def test_session_thread_isolated(tmp_path: Path) -> None:
    """Two threads in session() concurrently must not share a connection
    (sqlite conns are not cross-thread; store() runs on daemon threads
    via store_within_budget)."""
    kg = EntityStore(db_path=tmp_path / "kg.db")
    errs: list[BaseException] = []

    def _work(n: int) -> None:
        try:
            with kg.session():
                for i in range(5):
                    kg.store(Entity(canonical_name=f"thread{n}_e{i}",
                                    type="code"))
                    time.sleep(0.005)
        except BaseException as exc:  # noqa: BLE001 — collected for assert
            errs.append(exc)

    ts = [threading.Thread(target=_work, args=(n,)) for n in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=30)
    assert not errs, f"concurrent sessions must not error: {errs!r}"
    assert kg.count() == 10


def test_populate_uses_one_connection_inside_session(tmp_path: Path) -> None:
    """populate_entities_for_fact must run inside ONE session (the latency
    fix): trace sqlite3.connect calls during the populate."""
    kg = EntityStore(db_path=tmp_path / "kg.db")  # init outside the count
    calls: list[str] = []
    real_connect = sqlite3.connect

    def _counting_connect(*a: object, **k: object):
        calls.append(str(a[0]) if a else "?")
        return real_connect(*a, **k)

    sqlite3.connect = _counting_connect  # type: ignore[assignment]
    try:
        linked, edges = populate_entities_for_fact("f1", ENTITY_PROP, kg)
    finally:
        sqlite3.connect = real_connect  # type: ignore[assignment]
    assert linked >= 2 and edges >= 2
    kg_opens = [c for c in calls if "kg.db" in c]
    assert len(kg_opens) <= 1, (
        f"populate must open at most ONE kg connection, got {len(kg_opens)} "
        "(the ~76-connection pattern is the 122 ms/store regression)"
    )
