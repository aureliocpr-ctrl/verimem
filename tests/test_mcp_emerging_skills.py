"""Cycle 218 (2026-05-23) — MCP tool ``hippo_emerging_skills_draft``.

RED marker: the new tool must be advertised and callable.

This tool composes:
  cycle 213 detect_emerging_skills
  + cycle 217 draft_skill_from_community
to expose the LLM-free emergence pipeline as a single MCP call.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from engram import mcp_server


def _normalised_emb(seed: int) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.standard_normal(384).astype(np.float32)
    n = np.linalg.norm(arr)
    if n > 0:
        arr = arr / n
    return arr.tobytes()


def _cluster_emb(centroid_seed: int, noise: float, sample_seed: int) -> bytes:
    rng_c = np.random.default_rng(centroid_seed)
    centroid = rng_c.standard_normal(384).astype(np.float32)
    centroid /= np.linalg.norm(centroid) + 1e-9
    rng_n = np.random.default_rng(sample_seed)
    noise_v = rng_n.standard_normal(384).astype(np.float32) * float(noise)
    out = centroid + noise_v
    out /= np.linalg.norm(out) + 1e-9
    return out.tobytes()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT,
    topic TEXT,
    embedding BLOB,
    lineage_to TEXT,
    superseded_by TEXT,
    status TEXT DEFAULT 'model_claim',
    created_at REAL DEFAULT 0.0
);
"""

from tests.causal_fixture_helper import add_causal_clique_edges  # noqa: E402


@pytest.fixture
def populated_semantic_db(tmp_path: Path) -> Path:
    """Two clusters of 4 facts each — used to verify the MCP tool surfaces them."""
    db_path = tmp_path / "semantic" / "semantic.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    rows: list[tuple[Any, ...]] = []
    edges: list[tuple[Any, ...]] = []
    for i in range(4):
        rows.append((
            f"a{i}", f"python fact {i} list comprehension dict", "lang/python",
            _cluster_emb(1, 0.05, 100 + i), None, None, "model_claim",
            float(i),
        ))
        for j in range(4):
            if i != j:
                edges.append((f"a{i}", f"a{j}"))
    for i in range(4):
        rows.append((
            f"b{i}", f"banana fact {i} fruit yellow ripe", "food/fruit",
            _cluster_emb(2, 0.05, 200 + i), None, None, "model_claim",
            float(10 + i),
        ))
        for j in range(4):
            if i != j:
                edges.append((f"b{i}", f"b{j}"))
    rows.append((
        "lonely", "isolated fact x", "noise/topic",
        _normalised_emb(42), None, None, "model_claim", 100.0,
    ))
    conn.executemany(
        "INSERT INTO facts (id, proposition, topic, embedding, lineage_to, "
        "superseded_by, status, created_at) VALUES (?,?,?,?,?,?,?,?)", rows,
    )
    conn.commit()
    conn.close()
    add_causal_clique_edges(db_path, edges)
    return db_path


@pytest.mark.asyncio
async def test_tool_is_advertised() -> None:
    """The MCP server must list `hippo_emerging_skills_draft`."""
    tools = await mcp_server._list_tools_unfiltered()
    names = {tool.name for tool in tools}
    assert "hippo_emerging_skills_draft" in names


@pytest.mark.asyncio
async def test_tool_has_documented_schema() -> None:
    """Tool schema must accept the documented parameters."""
    tools = await mcp_server._list_tools_unfiltered()
    target = next(
        (t for t in tools if t.name == "hippo_emerging_skills_draft"),
        None,
    )
    assert target is not None
    schema = target.inputSchema
    props = schema.get("properties", {})
    for key in (
        "min_community_size", "min_topic_purity",
        "min_cohesion", "max_n",
    ):
        assert key in props


@pytest.mark.asyncio
async def test_tool_returns_drafts_for_synthetic_corpus(
    populated_semantic_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The handler must run detect → draft and return >=1 candidate."""
    # Monkey-patch the agent factory to point semantic.db_path at our fixture.
    import engram.mcp_server as ms

    class _FakeSemantic:
        def __init__(self, db_path: Path) -> None:
            self.db_path = db_path

    class _FakeAgent:
        def __init__(self, db_path: Path) -> None:
            self.semantic = _FakeSemantic(db_path)

    monkeypatch.setattr(
        ms, "_ag", lambda: _FakeAgent(populated_semantic_db),
    )

    handlers = mcp_server.server.request_handlers
    from mcp.types import CallToolRequest, CallToolRequestParams
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(
            name="hippo_emerging_skills_draft",
            arguments={
                "min_community_size": 3,
                "min_topic_purity": 0.5,
                "min_cohesion": 0.1,
                "max_n": 5,
            },
        ),
    )
    result = await handlers[CallToolRequest](req)
    payload = result.root if hasattr(result, "root") else result
    contents = payload.content
    assert contents, "tool returned no content"
    text = contents[0].text  # type: ignore[attr-defined]
    parsed = json.loads(text)
    assert "candidates" in parsed
    # The 2-cluster fixture should surface ≥1 candidate.
    assert len(parsed["candidates"]) >= 1
    first = parsed["candidates"][0]
    for key in (
        "skill_name", "draft_text", "trigger_keywords",
        "fact_ids", "evidence",
    ):
        assert key in first
