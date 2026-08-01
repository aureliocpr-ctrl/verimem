"""A local read hides the moat's verdict; the remote read of the same store shows it.

``_remote_row`` already carries ``grounding_score`` — its docstring says fields
the REST surface cannot compute are "omitted rather than invented (A1/A2)". The
LOCAL serialiser at the ``hippo_facts_search`` branch does not carry it, so the
same store answers two different truths depending on which path reached it.

What that costs is not cosmetic. Measured on the live store 2026-07-29
(``~/.engram/semantic/semantic.db``, 4729 facts not superseded):

    judged by the moat      n=  11   confidence 0.5   (min = max)
    never judged            n=4719   confidence 0.866 (max 1.0)

``confidence`` is a per-CHANNEL default — 0.5 from the CLI, 0.9 from
``hippo_remember`` — and the moat never writes it. So the only trust number a
reader gets back is ANTI-correlated with having been verified, and one fact
judged 0.49 (rejected: the source did not entail it) is indistinguishable by
confidence from one judged 99.99.

Exposing the score does not change any verdict and does not rank anything. It
gives the reader the axis that exists in the row and was being dropped on the
way out.
"""
from __future__ import annotations

import json
import time
from typing import Any

import pytest

from verimem import mcp_server


class _Fact:
    def __init__(self, fid: str, *, proposition: str, topic: str = "",
                 confidence: float = 0.9, grounding_score: float | None = None,
                 created_at: float | None = None) -> None:
        self.id = fid
        self.proposition = proposition
        self.topic = topic
        self.confidence = confidence
        self.created_at = created_at or time.time()
        self.source_episodes: list[str] = []
        self.status = "model_claim"
        self.verified_by: list[str] = []
        if grounding_score is not None:
            self.grounding_score = grounding_score


class _Semantic:
    """Mirrors the live store's shape: the judged fact carries the LOWER
    confidence, because the two numbers come from unrelated places."""

    def __init__(self) -> None:
        self._facts = [
            _Fact("judged", proposition="the branch has twenty-one commits",
                  topic="handoff", confidence=0.5, grounding_score=99.96,
                  created_at=2000.0),
            _Fact("rejected", proposition="the branch has twenty-one commits "
                  "and the suite is green", topic="handoff", confidence=0.5,
                  grounding_score=0.49, created_at=1900.0),
            _Fact("unjudged", proposition="the branch has twenty-one commits, "
                  "unverified", topic="handoff", confidence=0.9,
                  created_at=1800.0),
        ]

    def search_facts(self, query: str, *, limit: int = 20, **_kw: Any) -> list[_Fact]:
        ql = (query or "").strip().lower()
        out = [f for f in self._facts if not ql or ql in f.proposition.lower()]
        out.sort(key=lambda f: f.created_at, reverse=True)
        return out[:limit]

    def all(self) -> list[_Fact]:
        return list(self._facts)

    def list_facts(self, *, limit: int = 100, offset: int = 0) -> list[_Fact]:
        return list(self._facts)[offset:offset + limit]


class _Agent:
    def __init__(self) -> None:
        self.semantic = _Semantic()


async def _invoke(name: str, arguments: dict[str, Any] | None = None):
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


@pytest.fixture
def agent(monkeypatch: pytest.MonkeyPatch) -> _Agent:
    a = _Agent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


@pytest.mark.asyncio
async def test_a_local_read_carries_the_moat_score(agent: _Agent) -> None:
    """The field the remote row already carries."""
    payload = json.loads((await _invoke("hippo_facts_search",
                                        {"query": "commits"}))[0])
    by_id = {it["id"]: it for it in payload["items"]}
    assert "grounding_score" in by_id["judged"], (
        "a local read drops the moat verdict that the remote read carries"
    )
    assert by_id["judged"]["grounding_score"] == pytest.approx(99.96)


@pytest.mark.asyncio
async def test_a_fact_the_moat_rejected_is_distinguishable(agent: _Agent) -> None:
    """0.49 means the source did not entail the claim. By confidence alone it
    is identical to the fact judged 99.96 — both 0.5."""
    payload = json.loads((await _invoke("hippo_facts_search",
                                        {"query": "commits"}))[0])
    by_id = {it["id"]: it for it in payload["items"]}
    assert by_id["rejected"]["confidence"] == by_id["judged"]["confidence"]
    assert by_id["rejected"]["grounding_score"] != by_id["judged"]["grounding_score"]


@pytest.mark.asyncio
async def test_a_never_judged_fact_says_so_instead_of_reading_as_zero(
    agent: _Agent,
) -> None:
    """None is not 0.0: never asked must not look like asked-and-failed, which
    is the same distinction doctor makes between UNKNOWN coverage and zero."""
    payload = json.loads((await _invoke("hippo_facts_search",
                                        {"query": "commits"}))[0])
    by_id = {it["id"]: it for it in payload["items"]}
    assert by_id["unjudged"]["grounding_score"] is None
    assert by_id["unjudged"]["confidence"] > by_id["judged"]["confidence"], (
        "the live store's inversion: the unverified default (0.9) sits above "
        "the verified one (0.5) — this is what makes the score necessary"
    )


@pytest.mark.parametrize("tool,args", [
    ("hippo_facts_list", {"limit": 10}),
    ("hippo_facts_by_agent", {"agent_id": "", "include_shared": True}),
])
@pytest.mark.asyncio
async def test_every_listing_surface_carries_the_verdict(
    agent: _Agent, tool: str, args: dict[str, Any],
) -> None:
    """The sweep, not the point fix. ``hippo_facts_recall`` has carried the
    score since 2026-06-20 with a comment saying why — "so the agent can
    prefer/assert from grounded facts and hedge low-grounding ones". These two
    return facts to the same kind of consumer and dropped it, so which tool an
    agent happened to call decided whether it could tell a verified fact from
    an unverified one."""
    blocks = await _invoke(tool, args)
    payload = json.loads(blocks[0])
    items = payload.get("items") or payload.get("facts") or []
    assert items, f"{tool} returned nothing to check"
    by_id = {it["id"]: it for it in items}
    assert by_id["judged"].get("grounding_score") == pytest.approx(99.96), (
        f"{tool} drops the moat verdict"
    )
    assert by_id["unjudged"].get("grounding_score") is None
    assert "status" in by_id["judged"], f"{tool} drops the status"
