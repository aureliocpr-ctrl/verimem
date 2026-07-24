"""P0 evidence-before-belief, ciclo 2c: the rule reaches the real write paths.

Ciclo 2b made the gate able to ask the question; if nobody hands it the two
inputs (who is writing, which document store), the telemetry is dead code and
the observe phase measures nothing. There are three write paths through
`run_validation_gate` — the SDK, `hippo_remember`, and the `key_facts` loop of
`hippo_record_episode` — and the ciclo-1 critic found the third one exactly by
looking for the call-site nobody had swept. Same sweep here.

The store is opened LAZILY: a write that never reaches the rule (no L1
escalation, no document refs) must not pay for a sqlite connection.
"""
from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from verimem.client import Memory
from verimem.documents import DocumentStore
from verimem.evidence_independence import LazyDocumentStore
from verimem.semantic import SemanticMemory

CLAIM = "The migration was completed and all tests pass."


def _layers(warnings) -> set[str]:
    return {(w or {}).get("layer", "") for w in (warnings or [])}


@pytest.fixture()
def signed_docs(tmp_path, monkeypatch):
    """A document vouched for by the gateway, in an isolated store."""
    monkeypatch.setenv("HIPPO_DOCUMENTS_DB", str(tmp_path / "docs.db"))
    ds = DocumentStore()
    ds.ingest("release-notes", "Migration 42 finished; suite green.",
              principal="gw:team-alpha")
    return ds


# --- the lazy store -------------------------------------------------------

def test_lazy_store_opens_nothing_until_asked():
    opened = []

    def _factory():
        opened.append(1)
        raise AssertionError("must not be called")

    LazyDocumentStore(_factory)          # constructing is free
    assert opened == []


def test_lazy_store_forwards_and_opens_once():
    calls = []

    class _Real:
        def list_versions(self, source_id):
            calls.append(source_id)
            return ["v1"]

    opened = []

    def _factory():
        opened.append(1)
        return _Real()

    lazy = LazyDocumentStore(_factory)
    assert lazy.list_versions("a") == ["v1"]
    assert lazy.list_versions("b") == ["v1"]
    assert calls == ["a", "b"]
    assert opened == [1], "the store must be built once, not per question"


def test_lazy_store_never_raises_on_a_broken_factory():
    lazy = LazyDocumentStore(lambda: (_ for _ in ()).throw(OSError("no disk")))
    assert lazy.list_versions("a") == []


# --- SDK path -------------------------------------------------------------

def test_sdk_write_records_the_observe_note(signed_docs, tmp_path):
    m = Memory(path=tmp_path / "m.db")
    r = m.add(CLAIM, topic="t", verified_by=["doc:release-notes"])
    assert r["status"] == "quarantined", "observe mode must not change outcomes"
    assert "P0_INDEPENDENCE-observe" in _layers(r["warnings"])


def test_sdk_enforce_admits_the_independently_evidenced_claim(
        signed_docs, tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_P0_INDEPENDENCE", "1")
    m = Memory(path=tmp_path / "m.db")
    r = m.add(CLAIM, topic="t", verified_by=["doc:release-notes"])
    assert r["status"] != "quarantined"
    assert "P0_INDEPENDENCE" in _layers(r["warnings"])


def test_sdk_self_citation_stays_quarantined(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_DOCUMENTS_DB", str(tmp_path / "docs.db"))
    monkeypatch.setenv("ENGRAM_P0_INDEPENDENCE", "1")
    DocumentStore().ingest("mine", "Migration 42 finished.",
                           principal="sdk:local")
    m = Memory(path=tmp_path / "m.db")          # claimant is sdk:local too
    r = m.add(CLAIM, topic="t", verified_by=["doc:mine"])
    assert r["status"] == "quarantined"


# --- MCP paths ------------------------------------------------------------

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

    def store(self, episode, **kw) -> str:
        return getattr(episode, "id", "ep-stub")


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
    return " ".join(c.text for c in payload.content if hasattr(c, "text"))


@pytest.mark.asyncio
async def test_mcp_remember_records_the_observe_note(
        signed_docs, tmp_path, monkeypatch):
    from verimem import mcp_server

    sm = SemanticMemory(db_path=tmp_path / "semantic" / "facts.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _Agent(sm))
    out = await _invoke_tool("hippo_remember", {
        "proposition": CLAIM, "topic": "t",
        "verified_by": ["doc:release-notes"],
    })
    assert "P0_INDEPENDENCE-observe" in out
    with sqlite3.connect(sm.db_path) as c:
        row = c.execute("SELECT status FROM facts WHERE proposition = ?",
                        (CLAIM,)).fetchone()
    assert row and row[0] == "quarantined", "observe must not change outcomes"


@pytest.mark.asyncio
async def test_mcp_record_episode_key_facts_also_asks_the_question(
        signed_docs, tmp_path, monkeypatch):
    """The third write path — the one the ciclo-1 critic caught."""
    from verimem import mcp_server

    sm = SemanticMemory(db_path=tmp_path / "semantic" / "facts.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _Agent(sm))
    monkeypatch.setenv("ENGRAM_P0_INDEPENDENCE", "1")
    await _invoke_tool("hippo_record_episode", {
        "task_text": "run the migration", "final_answer": "done",
        "outcome": "success",
        "key_facts": [{"proposition": CLAIM, "topic": "kf",
                       "verified_by": ["doc:release-notes"]}],
    })
    with sqlite3.connect(sm.db_path) as c:
        row = c.execute("SELECT status FROM facts WHERE proposition = ?",
                        (CLAIM,)).fetchone()
    assert row is not None, "key_facts write did not persist"
    assert row[0] != "quarantined", (
        "the key_facts path never asked the independence question")
