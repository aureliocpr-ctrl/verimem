"""P3 minimal — RED test entity_attrs + anchor_set + anchor_recall.

Spec: docs/specs/p3-self-model-multi-anchor.md.

P3 estende self_model cycle #67 single-row a multi-anchor entity-based:
ogni anchor = entity type='anchor' + entity_attrs key='half_life_days'
+ entity_attrs key='created_anchor_at'. Decay temporale exp(-Δt/τ)
sui pesi PPR personalization.

Schema delta (migration v6):
  entity_attrs (entity_id, key, value_json, created_at, updated_at)
  PRIMARY KEY (entity_id, key) — UPSERT idempotente.

Test fake-faithful (SQLite REAL tmp_path, no mocks).
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import pytest

# ---------- entity_attrs schema + set/get -----------------------------


def test_entity_attrs_table_exists(tmp_path: Path) -> None:
    """RED: migration v6 crea tabella entity_attrs con colonne attese."""
    import sqlite3

    from verimem.entity_kg import EntityStore

    db_path = tmp_path / "p3.db"
    EntityStore(db_path=db_path)

    conn = sqlite3.connect(db_path)
    cols = {
        r[1] for r in conn.execute(
            "PRAGMA table_info(entity_attrs)"
        ).fetchall()
    }
    assert {"entity_id", "key", "value_json",
            "created_at", "updated_at"}.issubset(cols), (
        f"missing columns: {cols}"
    )
    conn.close()


def test_set_attr_and_get_attrs(tmp_path: Path) -> None:
    """RED: set_attr poi get_attrs ritorna dict con key→value JSON-decoded."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "p3.db")
    eid = store.store(Entity(canonical_name="X", type="anchor"))
    store.set_attr(eid, "half_life_days", 7.0)
    store.set_attr(eid, "payload",
                    {"label": "focus", "tags": ["urgent"]})

    attrs = store.get_attrs(eid)
    assert attrs["half_life_days"] == 7.0
    assert attrs["payload"]["label"] == "focus"
    assert attrs["payload"]["tags"] == ["urgent"]


def test_set_attr_upsert_no_duplicate(tmp_path: Path) -> None:
    """RED: set_attr 2 volte stessa key → update, no duplicate."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "p3.db")
    eid = store.store(Entity(canonical_name="Y", type="anchor"))
    store.set_attr(eid, "label", "v1")
    store.set_attr(eid, "label", "v2")

    attrs = store.get_attrs(eid)
    assert attrs["label"] == "v2"

    # Singola riga in DB
    import sqlite3
    conn = sqlite3.connect(store.db_path)
    n = conn.execute(
        "SELECT COUNT(*) FROM entity_attrs WHERE entity_id = ?",
        (eid,),
    ).fetchone()[0]
    assert n == 1
    conn.close()


# ---------- anchor_set / anchor_recall via MCP -----------------------


class _FakeAgent:
    def __init__(self, entity_kg) -> None:
        self.entity_kg = entity_kg
        self.semantic = _NoopSemantic()


class _NoopSemantic:
    def search_facts(self, *args, **kwargs):
        return []


@pytest.fixture
def fake_agent_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    from verimem import mcp_server
    from verimem.entity_kg import EntityStore

    store = EntityStore(db_path=tmp_path / "p3.db")
    a = _FakeAgent(entity_kg=store)
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


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
async def test_anchor_tools_listed(fake_agent_anchor) -> None:
    """RED: hippo_anchor_set + hippo_anchor_recall in tools/list."""
    from mcp.types import ListToolsRequest, PaginatedRequestParams

    from verimem import mcp_server

    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(
        method="tools/list", params=PaginatedRequestParams(),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_anchor_set" in names
    assert "hippo_anchor_recall" in names


@pytest.mark.asyncio
async def test_anchor_set_creates_typed_entity(
    fake_agent_anchor,
) -> None:
    """RED: hippo_anchor_set crea entity type='anchor' +
    entity_attrs row con half_life_days + payload."""
    a = fake_agent_anchor
    blocks = await _invoke_tool(
        "hippo_anchor_set",
        {
            "name": "Engram",
            "half_life_days": 7.0,
            "payload": {"label": "Project focus", "stage": "P2"},
        },
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    eid = payload["entity_id"]

    # Entity creata con type='anchor'
    ent = a.entity_kg.get_by_name("Engram")
    assert ent is not None
    assert ent.id == eid
    assert ent.type == "anchor"

    # Attrs salvati
    attrs = a.entity_kg.get_attrs(eid)
    assert attrs["half_life_days"] == 7.0
    assert attrs["payload"]["label"] == "Project focus"


@pytest.mark.asyncio
async def test_anchor_set_promotes_existing_entity_type(
    fake_agent_anchor,
) -> None:
    """RED round 2 P3 — counterexample 0.85: se entity con
    canonical_name esiste già con type != 'anchor', anchor_set deve
    promuovere il type a 'anchor', altrimenti silent failure
    (anchor_recall.list_anchors filtra WHERE type='anchor' e l'esclude).
    """
    a = fake_agent_anchor
    from verimem.entity_kg import Entity

    # Pre-esistente: entity "Engram" type='project'
    eid_pre = a.entity_kg.store(
        Entity(canonical_name="Engram", type="project"),
    )

    # anchor_set su stesso nome
    blocks = await _invoke_tool(
        "hippo_anchor_set",
        {"name": "Engram", "half_life_days": 7.0},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    assert payload["entity_id"] == eid_pre, (
        "idempotente: stessa entity, NON duplicata"
    )

    # Verifica type promosso
    ent = a.entity_kg.get_by_name("Engram")
    assert ent is not None
    assert ent.type == "anchor", (
        f"type deve essere promosso a 'anchor', got {ent.type!r}"
    )

    # E quindi anchor_recall la include
    blocks = await _invoke_tool(
        "hippo_anchor_recall", {"damping": 0.5, "k": 10},
    )
    out = json.loads(blocks[0])
    anchor_ids = {a_["entity_id"] for a_ in out["anchors"]}
    assert eid_pre in anchor_ids, (
        "anchor promosso deve apparire in anchor_recall, "
        f"got anchors={out['anchors']}"
    )


@pytest.mark.asyncio
async def test_anchor_recall_uses_decay(
    fake_agent_anchor,
) -> None:
    """RED: anchor recent (created_anchor_at = now) vs anchor old
    (created_anchor_at = 30 days ago) con τ=7 → peso recent > peso old."""
    a = fake_agent_anchor
    now = time.time()
    one_month_ago = now - 30 * 86400.0

    # Anchor recent
    blocks = await _invoke_tool(
        "hippo_anchor_set",
        {"name": "RecentFocus", "half_life_days": 7.0},
    )
    eid_recent = json.loads(blocks[0])["entity_id"]

    # Anchor old (forziamo created_anchor_at vecchio via set_attr)
    blocks = await _invoke_tool(
        "hippo_anchor_set",
        {"name": "OldFocus", "half_life_days": 7.0},
    )
    eid_old = json.loads(blocks[0])["entity_id"]
    a.entity_kg.set_attr(eid_old, "created_anchor_at",
                          one_month_ago)

    # Recall: pesi devono riflettere decay
    blocks = await _invoke_tool(
        "hippo_anchor_recall", {"damping": 0.5, "k": 10},
    )
    out = json.loads(blocks[0])
    anchors_by_id = {
        a_dict["entity_id"]: a_dict
        for a_dict in out["anchors"]
    }
    w_recent = anchors_by_id[eid_recent]["weight"]
    w_old = anchors_by_id[eid_old]["weight"]
    assert w_recent > w_old, (
        f"recent anchor weight ({w_recent}) must exceed "
        f"old ({w_old}) under exp decay"
    )
    # Old anchor a 30 giorni con τ=7 → peso < 0.06 (4 half-lives)
    expected_old_ratio = math.exp(-30.0 / 7.0)
    # Solo bound loose: peso_old / peso_recent ≤ 0.1
    assert w_old / max(w_recent, 1e-9) < 0.1, (
        f"old/recent ratio {w_old / max(w_recent, 1e-9):.4f} "
        f"must be < 0.1 (expected ~{expected_old_ratio:.4f})"
    )


@pytest.mark.asyncio
async def test_anchor_recall_returns_ranked_and_facts(
    fake_agent_anchor,
) -> None:
    """RED: hippo_anchor_recall ritorna ranked entities + facts (come
    ppr() — anchor entrano in personalization PPR)."""
    a = fake_agent_anchor
    # Setup: 1 anchor + 1 entity NON-anchor + edge + fact
    blocks = await _invoke_tool(
        "hippo_anchor_set",
        {"name": "Focus", "half_life_days": 30.0},
    )
    eid_anchor = json.loads(blocks[0])["entity_id"]

    from verimem.entity_kg import Entity
    eid_concept = a.entity_kg.store(
        Entity(canonical_name="MIT", type="org"),
    )
    a.entity_kg.add_edge(
        eid_anchor, eid_concept, predicate="related_to",
    )
    a.entity_kg.link_fact("f_focus_1", eid_anchor)
    a.entity_kg.link_fact("f_mit_1", eid_concept)

    blocks = await _invoke_tool(
        "hippo_anchor_recall", {"damping": 0.5, "k": 20},
    )
    out = json.loads(blocks[0])
    assert "anchors" in out
    assert "ranked" in out
    assert "facts" in out

    # Anchor MIT correlato via edge entra nel ranking
    ranked_ids = [r["entity_id"] for r in out["ranked"]]
    assert eid_anchor in ranked_ids
    assert eid_concept in ranked_ids
    # Anchor (seed) dovrebbe avere score >= concept (non-seed)
    score_anchor = next(
        r["score"] for r in out["ranked"]
        if r["entity_id"] == eid_anchor
    )
    score_concept = next(
        r["score"] for r in out["ranked"]
        if r["entity_id"] == eid_concept
    )
    assert score_anchor >= score_concept

    # Facts unione
    assert "f_focus_1" in out["facts"]
    assert "f_mit_1" in out["facts"]
