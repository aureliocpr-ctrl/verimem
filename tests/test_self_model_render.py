"""P3-bis — RED test render_anchor_block + hippo_self_model_render.

Spec: docs/specs/p3bis-sessionstart-anchor-integration.md.

P3-bis sostituisce/affianca il blob statico self_model_current con un
blocco Markdown live da `EntityStore.list_anchors` decay-pesato. Output
≤ max_bytes (UTF-8 counted), top-K fact per anchor, ordine weight desc.

4 RED:
1. Render 3 anchor → markdown ordinato weight desc, top-3 fact per anchor.
2. max_bytes=512 con 10 anchor → output ≤ 512 byte UTF-8, truncated=True.
3. KG vuoto → markdown="", n_anchors=0, no exception.
4. Tool MCP `hippo_self_model_render` listed + dispatchato.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

# ---------- _FakeSemantic with fact storage --------------------------


class _FakeFact:
    def __init__(self, fid: str, proposition: str, topic: str = "") -> None:
        self.id = fid
        self.proposition = proposition
        self.topic = topic


class _FakeSemantic:
    """Stub SemanticMemory che memorizza fact e supporta get_fact(id)."""

    def __init__(self) -> None:
        self.facts: dict[str, _FakeFact] = {}

    def add(self, prop: str, topic: str = "") -> str:
        fid = uuid.uuid4().hex
        self.facts[fid] = _FakeFact(fid, prop, topic)
        return fid

    def get(self, fid: str) -> _FakeFact | None:
        return self.facts.get(fid)

    def search_facts(self, *args, **kwargs):
        return []


class _FakeAgent:
    def __init__(self, entity_kg, sem) -> None:
        self.entity_kg = entity_kg
        self.semantic = sem


@pytest.fixture
def fake_agent_render(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    from engram import mcp_server
    from engram.entity_kg import EntityStore

    store = EntityStore(db_path=tmp_path / "p3bis.db")
    sem = _FakeSemantic()
    a = _FakeAgent(entity_kg=store, sem=sem)
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


async def _invoke_tool(
    name: str, arguments: dict[str, Any] | None = None,
) -> list[str]:
    from mcp.types import CallToolRequest, CallToolRequestParams

    from engram import mcp_server

    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


def _seed_anchor(
    store, sem: _FakeSemantic, name: str, *,
    half_life_days: float, created_anchor_at: float | None = None,
    facts: list[str] | None = None,
) -> str:
    """Helper: create anchor entity + attrs + linked facts."""
    from engram.entity_kg import Entity
    eid = store.store(Entity(canonical_name=name, type="anchor"))
    store.set_attr(eid, "half_life_days", float(half_life_days))
    if created_anchor_at is None:
        created_anchor_at = time.time()
    store.set_attr(eid, "created_anchor_at", float(created_anchor_at))
    store.set_attr(eid, "payload",
                   {"label": name, "origin": "test"})
    if facts:
        for prop in facts:
            fid = sem.add(prop, topic=f"test/{name}")
            store.link_fact(fid, eid)
    return eid


# ---------- RED #1: render 3 anchor decay-pesati ---------------------


def test_render_anchor_block_3_anchors_weight_desc(
    fake_agent_render,
) -> None:
    """RED #1: 3 anchor con (half_life, age) diversi → markdown ha 3
    sezioni in ordine weight desc, top-3 fact per anchor."""
    from engram.self_model import render_anchor_block

    a = fake_agent_render
    now = time.time()
    # Engram: hl=14d, age=1d → weight ≈ 2^(-1/14) ≈ 0.95
    _seed_anchor(
        a.entity_kg, a.semantic, "Engram",
        half_life_days=14.0,
        created_anchor_at=now - 86400.0,
        facts=[f"Engram fact #{i} sul progetto" for i in range(5)],
    )
    # Nexus: hl=7d, age=3d → weight ≈ 2^(-3/7) ≈ 0.74
    _seed_anchor(
        a.entity_kg, a.semantic, "Nexus",
        half_life_days=7.0,
        created_anchor_at=now - 3 * 86400.0,
        facts=[f"Nexus cybersec fact #{i}" for i in range(5)],
    )
    # Beacon: hl=30d, age=60d → weight ≈ 2^(-2) = 0.25
    _seed_anchor(
        a.entity_kg, a.semantic, "Beacon",
        half_life_days=30.0,
        created_anchor_at=now - 60 * 86400.0,
        facts=[f"Beacon philosophy fact #{i}" for i in range(5)],
    )

    result = render_anchor_block(
        a.entity_kg, sem=a.semantic, max_bytes=4096,
    )
    assert result["n_anchors"] == 3
    md = result["markdown"]
    assert isinstance(md, str)
    assert md  # non vuoto

    # Ordine weight desc: Engram (0.95) prima di Nexus (0.74) prima di Beacon (0.25)
    pos_engram = md.find("Engram")
    pos_nexus = md.find("Nexus")
    pos_beacon = md.find("Beacon")
    assert 0 <= pos_engram < pos_nexus < pos_beacon, (
        f"weight ordering broken: Engram@{pos_engram} "
        f"Nexus@{pos_nexus} Beacon@{pos_beacon}"
    )

    # Top-3 fact per anchor: 9 fact totali (3 per ogni anchor)
    fact_lines = [
        ln for ln in md.split("\n")
        if "fact #" in ln or "cybersec fact" in ln or "philosophy fact" in ln
    ]
    # Almeno 3 per anchor visibili (di 5 totali per anchor)
    # Tolleranza: cap top-3 implicito
    assert len(fact_lines) >= 9, (
        f"expected ≥9 fact lines (3 per anchor × 3 anchors), got "
        f"{len(fact_lines)}:\n{md}"
    )
    assert len(fact_lines) <= 15, (
        f"expected ≤15 fact lines (cap top-3 too loose?), got "
        f"{len(fact_lines)}"
    )


# ---------- RED #2: max_bytes truncation -----------------------------


def test_render_anchor_block_max_bytes_truncation(
    fake_agent_render,
) -> None:
    """RED #2: max_bytes=512 con 10 anchor con tanti fact ciascuno →
    output troncato a ≤512 byte UTF-8, truncated=True."""
    from engram.self_model import render_anchor_block

    a = fake_agent_render
    now = time.time()
    for i in range(10):
        _seed_anchor(
            a.entity_kg, a.semantic, f"Anchor{i:02d}",
            half_life_days=7.0,
            created_anchor_at=now - i * 86400.0,
            facts=[
                f"Fact {j} per Anchor{i:02d} con testo abbastanza lungo "
                f"per occupare byte significativi nel rendering"
                for j in range(5)
            ],
        )

    result = render_anchor_block(
        a.entity_kg, sem=a.semantic, max_bytes=512,
    )
    md = result["markdown"]
    size = len(md.encode("utf-8"))
    assert size <= 512, (
        f"truncation failed: {size} byte > 512 cap. "
        f"markdown (head):\n{md[:200]}"
    )
    assert result["truncated"] is True


# ---------- RED #3: empty KG -----------------------------------------


def test_render_anchor_block_empty_kg(fake_agent_render) -> None:
    """RED #3: KG vuoto (0 anchor) → markdown="", n_anchors=0,
    truncated=False, no exception."""
    from engram.self_model import render_anchor_block

    a = fake_agent_render
    # nessun anchor seedato
    result = render_anchor_block(
        a.entity_kg, sem=a.semantic, max_bytes=4096,
    )
    assert result["n_anchors"] == 0
    assert result["markdown"] == ""
    assert result["truncated"] is False


# ---------- RED #3-bis: store=None fallback graceful -----------------


def test_render_anchor_block_store_none_returns_empty() -> None:
    """RED: store=None (entity_kg non disponibile sull'agent) →
    output vuoto, no AttributeError."""
    from engram.self_model import render_anchor_block

    result = render_anchor_block(None, sem=None, max_bytes=4096)
    assert result["n_anchors"] == 0
    assert result["markdown"] == ""
    assert result["truncated"] is False


# ---------- RED #4: tool MCP listed + dispatch -----------------------


@pytest.mark.asyncio
async def test_hippo_self_model_render_tool_listed(
    fake_agent_render,
) -> None:
    """RED #4a: tool listed in tools/list."""
    from mcp.types import ListToolsRequest, PaginatedRequestParams

    from engram import mcp_server

    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(
        method="tools/list", params=PaginatedRequestParams(),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_self_model_render" in names


@pytest.mark.asyncio
async def test_hippo_self_model_render_tool_dispatch(
    fake_agent_render,
) -> None:
    """RED #4b: dispatch tool → ritorna {markdown, n_anchors, truncated}."""
    a = fake_agent_render
    now = time.time()
    _seed_anchor(
        a.entity_kg, a.semantic, "Engram",
        half_life_days=14.0, created_anchor_at=now - 86400.0,
        facts=["Fact Engram A", "Fact Engram B"],
    )

    blocks = await _invoke_tool(
        "hippo_self_model_render", {"max_bytes": 2048},
    )
    payload = json.loads(blocks[0])
    assert payload.get("ok") is True
    assert "markdown" in payload
    assert "n_anchors" in payload
    assert "truncated" in payload
    assert payload["n_anchors"] == 1
    assert "Engram" in payload["markdown"]
