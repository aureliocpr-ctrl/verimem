"""P2.b — RED test PPR retrieval + entity edges + entity neighbors.

Spec: docs/specs/p2b-ppr-entity-neighbors.md.

Schema delta (migration v5): tabella `entity_edges(src, dst,
predicate, weight, source_fact_id, created_at)` con PRIMARY KEY
composito (src, dst, predicate). 3 tool MCP nuovi:

  - hippo_entity_link(src, dst, predicate, weight, source_fact_id)
  - hippo_entity_neighbors(entity_id|name, k, hops)
  - hippo_ppr_retrieve(query_entities, damping, k)

Pattern test: SQLite REAL in tmp_path (no fake — cycle #70 lezione
ribadita). Per il PPR usiamo networkx.pagerank diretto sul grafo
costruito dal store; verifichiamo ranking deterministico + topk
stable.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# ---------- Unit tests EntityStore.add_edge / neighbors / ppr ---------


def test_entity_edges_table_exists(tmp_path: Path) -> None:
    """RED: dopo init EntityStore la tabella entity_edges deve esistere
    con le colonne attese (PK su (src, dst, predicate))."""
    import sqlite3

    from verimem.entity_kg import EntityStore

    db_path = tmp_path / "entity_kg.db"
    EntityStore(db_path=db_path)  # init + migrations

    conn = sqlite3.connect(db_path)
    cur = conn.execute("PRAGMA table_info(entity_edges)")
    cols = {r[1] for r in cur.fetchall()}
    assert {
        "src_entity", "dst_entity", "predicate",
        "weight", "source_fact_id", "created_at",
    }.issubset(cols), f"missing columns: {cols}"
    conn.close()


def test_add_edge_idempotent(tmp_path: Path) -> None:
    """RED: add_edge(src, dst, predicate) due volte non duplica."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid_a = store.store(Entity(canonical_name="Tonegawa", type="person"))
    eid_b = store.store(Entity(canonical_name="MIT", type="org"))

    store.add_edge(eid_a, eid_b, predicate="affiliated_with",
                   weight=1.0)
    store.add_edge(eid_a, eid_b, predicate="affiliated_with",
                   weight=2.5)  # stessa tripla, weight diverso

    edges = store.edges_from(eid_a)
    assert len(edges) == 1, "duplicate (src,dst,predicate) must dedupe"
    # Politica: INSERT OR IGNORE → weight resta quello originario
    assert edges[0]["weight"] == 1.0
    assert edges[0]["predicate"] == "affiliated_with"


def test_neighbors_hops_1(tmp_path: Path) -> None:
    """RED: neighbors(X, hops=1) ritorna i diretti adiacenti con
    distance=1."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid_a = store.store(Entity(canonical_name="A"))
    eid_b = store.store(Entity(canonical_name="B"))
    eid_c = store.store(Entity(canonical_name="C"))
    store.add_edge(eid_a, eid_b, predicate="links_to")
    store.add_edge(eid_a, eid_c, predicate="links_to")

    nbrs = store.neighbors(eid_a, k=10, hops=1)
    ids = {n["entity_id"] for n in nbrs}
    assert ids == {eid_b, eid_c}
    assert all(n["distance"] == 1 for n in nbrs)


def test_neighbors_hops_2(tmp_path: Path) -> None:
    """RED: neighbors(X, hops=2) include entity a 2 hop di distanza,
    cap k limita l'output finale."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid_a = store.store(Entity(canonical_name="A"))
    eid_b = store.store(Entity(canonical_name="B"))
    eid_c = store.store(Entity(canonical_name="C"))
    eid_d = store.store(Entity(canonical_name="D"))
    store.add_edge(eid_a, eid_b, predicate="p1")  # 1-hop
    store.add_edge(eid_b, eid_c, predicate="p2")  # 2-hop da A
    store.add_edge(eid_b, eid_d, predicate="p3")  # 2-hop da A

    nbrs2 = store.neighbors(eid_a, k=10, hops=2)
    ids = {n["entity_id"] for n in nbrs2}
    assert ids == {eid_b, eid_c, eid_d}

    distances = {n["entity_id"]: n["distance"] for n in nbrs2}
    assert distances[eid_b] == 1
    assert distances[eid_c] == 2
    assert distances[eid_d] == 2

    # k cap rispettato
    nbrs2_k1 = store.neighbors(eid_a, k=1, hops=2)
    assert len(nbrs2_k1) == 1


def test_ppr_retrieve_ranking_seed_first(tmp_path: Path) -> None:
    """RED: ppr_retrieve([X]) su grafo X→Y deve ritornare ranking
    dove X (seed) ha score >= Y (non-seed). Convenzione PPR: il seed
    accumula own-mass dalla personalization."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid_x = store.store(Entity(canonical_name="X"))
    eid_y = store.store(Entity(canonical_name="Y"))
    store.add_edge(eid_x, eid_y, predicate="links_to", weight=1.0)

    result = store.ppr(
        query_entities=[eid_x], damping=0.5, k=10,
    )
    ranked = result["ranked"]
    assert len(ranked) >= 2
    # Primo elemento deve essere il seed X (own-mass dominante)
    assert ranked[0]["entity_id"] == eid_x
    # Y presente nel top-k
    ranked_ids = [r["entity_id"] for r in ranked]
    assert eid_y in ranked_ids
    # Score X > Score Y (personalization 1.0 vs damping diffusion)
    score_x = next(r["score"] for r in ranked if r["entity_id"] == eid_x)
    score_y = next(r["score"] for r in ranked if r["entity_id"] == eid_y)
    assert score_x > score_y


def test_ppr_retrieve_deterministic(tmp_path: Path) -> None:
    """RED: 3 chiamate consecutive con stesso input → stesso ranking
    + stesso score (deterministic, no seed random)."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    ids = []
    for name in ("A", "B", "C", "D"):
        ids.append(store.store(Entity(canonical_name=name)))
    store.add_edge(ids[0], ids[1], predicate="p")
    store.add_edge(ids[1], ids[2], predicate="p")
    store.add_edge(ids[2], ids[3], predicate="p")
    store.add_edge(ids[3], ids[0], predicate="p")  # ciclo

    out1 = store.ppr(query_entities=[ids[0]], damping=0.5, k=10)
    out2 = store.ppr(query_entities=[ids[0]], damping=0.5, k=10)
    out3 = store.ppr(query_entities=[ids[0]], damping=0.5, k=10)

    # Stessa sequenza di entity_id, stessi score
    rank1 = [(r["entity_id"], round(r["score"], 9)) for r in out1["ranked"]]
    rank2 = [(r["entity_id"], round(r["score"], 9)) for r in out2["ranked"]]
    rank3 = [(r["entity_id"], round(r["score"], 9)) for r in out3["ranked"]]
    assert rank1 == rank2 == rank3, (
        f"PPR non deterministic: {rank1} vs {rank2} vs {rank3}"
    )


def test_ppr_retrieve_aggregates_facts(tmp_path: Path) -> None:
    """RED: ppr_retrieve ritorna anche i fact_id collegati alle entity
    top-k via entity_facts (unione, no duplicate)."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid_x = store.store(Entity(canonical_name="X"))
    eid_y = store.store(Entity(canonical_name="Y"))
    store.add_edge(eid_x, eid_y, predicate="p")
    store.link_fact("f1", eid_x)
    store.link_fact("f2", eid_y)
    store.link_fact("f3", eid_x)

    out = store.ppr(query_entities=[eid_x], damping=0.5, k=10)
    assert set(out["facts"]) == {"f1", "f2", "f3"}


# ---------- MCP tool integration ------------------------------------


class _FakeAgent:
    def __init__(self, entity_kg) -> None:
        self.entity_kg = entity_kg
        self.semantic = _NoopSemantic()


class _NoopSemantic:
    def search_facts(self, query: str, *, limit: int = 20,
                     topic: str | None = None):
        return []


@pytest.fixture
def fake_agent_with_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    """Build a fake agent with a real EntityStore + 3 entity + 2 edge."""
    from verimem import mcp_server
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid_a = store.store(Entity(canonical_name="EntityA", type="t"))
    eid_b = store.store(Entity(canonical_name="EntityB", type="t"))
    eid_c = store.store(Entity(canonical_name="EntityC", type="t"))
    store.add_edge(eid_a, eid_b, predicate="links_to")
    store.add_edge(eid_b, eid_c, predicate="links_to")
    store.link_fact("f_a1", eid_a)
    store.link_fact("f_b1", eid_b)

    a = _FakeAgent(entity_kg=store)
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a, (eid_a, eid_b, eid_c)


async def _invoke_tool(
    name: str, arguments: dict[str, Any] | None = None,
) -> list[str]:
    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server

    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


@pytest.mark.asyncio
async def test_three_new_tools_listed(fake_agent_with_graph) -> None:
    """RED: i 3 tool nuovi devono apparire in tools/list."""
    from mcp.types import ListToolsRequest, PaginatedRequestParams

    from verimem import mcp_server

    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(
        method="tools/list", params=PaginatedRequestParams(),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_entity_link" in names
    assert "hippo_entity_neighbors" in names
    assert "hippo_ppr_retrieve" in names


@pytest.mark.asyncio
async def test_hippo_entity_neighbors_tool(fake_agent_with_graph) -> None:
    """RED: tool MCP hippo_entity_neighbors ritorna i diretti
    adiacenti (hops=1)."""
    _, (eid_a, eid_b, _eid_c) = fake_agent_with_graph
    blocks = await _invoke_tool(
        "hippo_entity_neighbors",
        {"entity_id": eid_a, "k": 10, "hops": 1},
    )
    payload = json.loads(blocks[0])
    nbr_ids = {n["entity_id"] for n in payload["neighbors"]}
    assert eid_b in nbr_ids


@pytest.mark.asyncio
async def test_hippo_ppr_retrieve_tool(fake_agent_with_graph) -> None:
    """RED: tool MCP hippo_ppr_retrieve ritorna ranked + facts."""
    _, (eid_a, _eid_b, _eid_c) = fake_agent_with_graph
    blocks = await _invoke_tool(
        "hippo_ppr_retrieve",
        {"query_entities": [eid_a], "damping": 0.5, "k": 10},
    )
    payload = json.loads(blocks[0])
    assert payload["ranked"]
    assert payload["ranked"][0]["entity_id"] == eid_a
    # Fact aggregati dalle entity top-k
    assert "f_a1" in payload["facts"]


@pytest.mark.asyncio
async def test_hippo_entity_link_tool(fake_agent_with_graph) -> None:
    """RED: tool MCP hippo_entity_link aggiunge edge persistente."""
    a, (eid_a, _eid_b, eid_c) = fake_agent_with_graph
    blocks = await _invoke_tool(
        "hippo_entity_link",
        {
            "src": eid_a, "dst": eid_c, "predicate": "links_to_directly",
            "weight": 1.5,
        },
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    # Verifica edge persistito via store
    edges = a.entity_kg.edges_from(eid_a)
    new = [e for e in edges if e["predicate"] == "links_to_directly"]
    assert len(new) == 1
    assert new[0]["dst_entity"] == eid_c
    assert new[0]["weight"] == 1.5
