"""P0 evidence-before-belief, ciclo 1: principal plumbing (WS4.2 foundation).

Adversarial design review 2026-07-22 (glm-5.2 + kimi-k3, convergent 2/2):
the ONLY thing that breaks self-claim laundering and poison-then-cite is a
SERVER-STAMPED write/index principal — `author_principal(source) != claimant`
can't be evaluated if nobody records WHO wrote and WHO indexed. Caller-declared
fields (the writer_role precedent) are S4-class: advisory, never identity.

This cycle is pure plumbing — NO gate behaviour changes:
  * facts gain `writer_principal` (nullable, migration-laddered);
  * SDK stamps "sdk:local" by default, operator can declare an identity
    (in-process = trusted by definition), per-call override wins;
  * the MCP server stamps "mcp:unbound" ITSELF — a client-supplied
    writer_principal argument must be ignored (the trust boundary);
  * the REST gateway stamps "gw:<tenant>" — a body-supplied principal must
    be ignored (same boundary);
  * DocumentStore.ingest records indexed_by/indexed_at in doc meta when a
    principal is given; ABSENT when not (absence = untrusted class for the
    future AND-rule, never a fake default).
"""
from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from verimem.client import Memory
from verimem.documents import DocumentStore
from verimem.semantic import SemanticMemory


def _fact_principal(db_path, fact_id: str) -> str | None:
    with sqlite3.connect(db_path) as c:
        row = c.execute(
            "SELECT writer_principal FROM facts WHERE id = ?", (fact_id,)
        ).fetchone()
    assert row is not None, f"fact {fact_id} not found in {db_path}"
    return row[0]


# --- SDK ------------------------------------------------------------------

def test_sdk_stamps_default_principal(tmp_path):
    m = Memory(path=tmp_path / "m.db")
    r = m.add("The quarterly report was filed on Monday.", topic="t")
    assert r.get("stored"), r
    assert _fact_principal(m.semantic.db_path, r["id"]) == "sdk:local"


def test_sdk_operator_declared_principal(tmp_path):
    m = Memory(path=tmp_path / "m.db", principal="ops-1")
    r = m.add("The quarterly report was filed on Monday.", topic="t")
    assert r.get("stored"), r
    assert _fact_principal(m.semantic.db_path, r["id"]) == "ops-1"


def test_sdk_per_call_override_wins(tmp_path):
    m = Memory(path=tmp_path / "m.db", principal="ops-1")
    r = m.add("The quarterly report was filed on Monday.", topic="t",
              principal="gw:acme")
    assert r.get("stored"), r
    assert _fact_principal(m.semantic.db_path, r["id"]) == "gw:acme"


# --- migration ------------------------------------------------------------

def test_migration_adds_writer_principal_to_old_db(tmp_path):
    """A pre-P0 facts table gains the column via the ALTER ladder."""
    db = tmp_path / "old.db"
    with sqlite3.connect(db) as c:
        c.execute(
            """CREATE TABLE facts (
                id TEXT PRIMARY KEY,
                proposition TEXT NOT NULL,
                topic TEXT NOT NULL,
                confidence REAL NOT NULL,
                source_episodes TEXT NOT NULL,
                created_at REAL NOT NULL,
                embedding BLOB NOT NULL
            )"""
        )
    SemanticMemory(db_path=db)
    with sqlite3.connect(db) as c:
        cols = {r[1] for r in c.execute("PRAGMA table_info(facts)")}
    assert "writer_principal" in cols


# --- DocumentStore --------------------------------------------------------

def test_ingest_stamps_indexed_by_and_at(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    r = ds.ingest("spec-1", "The API returns 429 on rate limit.",
                  principal="mcp:unbound")
    meta = ds.get(r["id"]).meta
    assert meta["indexed_by"] == "mcp:unbound"
    assert isinstance(meta["indexed_at"], (int, float)) and meta["indexed_at"] > 0


def test_ingest_without_principal_records_nothing(tmp_path):
    """Absence stays absent — no fake default that could read as trusted."""
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    r = ds.ingest("spec-2", "The API returns 429 on rate limit.")
    meta = ds.get(r["id"]).meta
    assert "indexed_by" not in meta
    assert "indexed_at" not in meta


# --- REST gateway ---------------------------------------------------------

def test_gateway_stamps_tenant_and_ignores_body_principal(tmp_path):
    fastapi = pytest.importorskip("fastapi")  # noqa: F841
    from fastapi.testclient import TestClient

    from verimem.gateway import GatewayKeys, create_app

    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    key = keys.create(tenant_id="team-alpha", name="ci")
    client = TestClient(create_app(data_dir=tmp_path, keys=keys))
    r = client.post(
        "/v1/memories",
        json={"content": "The quarterly report was filed on Monday.",
              "principal": "evil-injected"},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("stored"), body
    db = tmp_path / "tenants" / "team-alpha" / "memory.db"
    assert _fact_principal(db, body["id"]) == "gw:team-alpha"


# --- MCP server -----------------------------------------------------------

class _StubSkills:
    def all(self, status: str | None = None) -> list:
        return []

    def count(self, status: str | None = None) -> int:
        return 0


class _StubMemory:
    def all(self, limit: int | None = None) -> list:
        return []

    def count(self, outcome_filter=None) -> int:
        return 0


class _Agent:
    def __init__(self, semantic: SemanticMemory) -> None:
        self.memory = _StubMemory()
        self.skills = _StubSkills()
        self.semantic = semantic


async def _invoke_tool(name: str, arguments: dict[str, Any] | None = None):
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
async def test_mcp_remember_stamps_server_principal_ignoring_client(
        tmp_path, monkeypatch):
    """The MCP layer stamps its OWN principal; a client-supplied
    writer_principal argument is a spoof attempt and must be ignored."""
    from verimem import mcp_server

    sm = SemanticMemory(db_path=tmp_path / "semantic" / "facts.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _Agent(sm))
    prop = "The quarterly report was filed on Monday."
    await _invoke_tool("hippo_remember", {
        "proposition": prop, "topic": "t",
        "writer_principal": "evil-spoof",
    })
    with sqlite3.connect(sm.db_path) as c:
        row = c.execute(
            "SELECT writer_principal FROM facts WHERE proposition = ?",
            (prop,)).fetchone()
    assert row is not None, "MCP remember did not persist the fact"
    assert row[0] == "mcp:unbound"
