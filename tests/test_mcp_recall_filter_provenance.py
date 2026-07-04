"""Cycle #109 S4-A — MCP dispatch tests for provenance recall filter.

Verifies that ``hippo_facts_recall`` and ``hippo_facts_search`` MCP
tools default to ``include_legacy=False`` (drop pre-cycle-109 unverified
inheritance), support ``min_status`` trust floor, and expose ``status``
+ ``verified_by`` in their JSON output.

Why the safe default matters (Aurelio sfida 2026-05-16): the live
corpus has 815 ``legacy_unverified`` rows out of 858 — pre-fix they
would dominate any recall and the agent would treat them as memory.
The MCP-level safe default protects external callers; the core
``recall()`` / ``search_facts()`` stays retro-compatible.
"""
from __future__ import annotations

import json
import time
from typing import Any

import pytest

from engram import mcp_server

# ---------- Fakes --------------------------------------------------------


class _FakeFact:
    """Minimal Fact stand-in carrying provenance fields."""
    def __init__(
        self, fid: str, *,
        proposition: str,
        topic: str = "lessons/test",
        confidence: float = 0.8,
        status: str = "model_claim",
        verified_by: list[str] | None = None,
        source_signature: str | None = None,
        created_at: float | None = None,
    ) -> None:
        self.id = fid
        self.proposition = proposition
        self.topic = topic
        self.confidence = confidence
        self.source_episodes: list[str] = []
        self.created_at = created_at or time.time()
        self.status = status
        self.verified_by = verified_by or []
        self.source_signature = source_signature


_STATUS_RANK = {
    "legacy_unverified": 0,
    "provisional": 1,
    "model_claim": 2,
    "verified": 3,
}


class _FakeSemantic:
    """Stand-in for SemanticMemory implementing the new filter contract."""
    def __init__(self) -> None:
        self._facts = {
            "f-verified": _FakeFact(
                "f-verified",
                proposition="alpha verified knowledge",
                status="verified",
                verified_by=["bash:pytest:exit0"],
                source_signature="sha256:abc",
                created_at=1000.0,
            ),
            "f-model": _FakeFact(
                "f-model",
                proposition="alpha model claim knowledge",
                status="model_claim",
                created_at=1100.0,
            ),
            "f-prov": _FakeFact(
                "f-prov",
                proposition="alpha provisional research finding",
                topic="research/test",
                status="provisional",
                created_at=1200.0,
            ),
            "f-legacy": _FakeFact(
                "f-legacy",
                proposition="alpha legacy unverified inheritance",
                status="legacy_unverified",
                created_at=900.0,
            ),
        }

    def _filter(
        self, facts: list[_FakeFact], *,
        exclude_legacy: bool, min_status: str | None,
    ) -> list[_FakeFact]:
        if min_status is not None and min_status not in _STATUS_RANK:
            raise ValueError(
                f"min_status must be one of {sorted(_STATUS_RANK)!r}, "
                f"got {min_status!r}"
            )
        out: list[_FakeFact] = []
        for f in facts:
            if exclude_legacy and f.status == "legacy_unverified":
                continue
            if min_status is not None and (
                _STATUS_RANK.get(f.status, 0) < _STATUS_RANK[min_status]
            ):
                continue
            out.append(f)
        return out

    def search_facts(
        self, query: str, *, limit: int = 20,
        topic: str | None = None,
        exclude_legacy: bool = False,
        min_status: str | None = None,
        tokenize: bool = False,
        require_all_tokens: bool = False,
        topic_prefix: str | None = None,
    ) -> list[_FakeFact]:
        ql = (query or "").strip().lower()
        # Mirror SemanticMemory.search_facts multi-word semantics so the
        # AND-first/OR-fallback dispatcher path is faithfully exercised.
        toks = [t for t in ql.split() if len(t) >= 2] if (
            tokenize or require_all_tokens
        ) else []
        candidates: list[_FakeFact] = []
        for f in self._facts.values():
            pl = f.proposition.lower()
            if ql:
                if len(toks) > 1:
                    ok = (all(t in pl for t in toks) if require_all_tokens
                          else any(t in pl for t in toks))
                elif len(toks) == 1:
                    ok = toks[0] in pl
                else:
                    ok = ql in pl
                if not ok:
                    continue
            if topic and f.topic != topic:
                continue
            if topic_prefix and not f.topic.startswith(topic_prefix):
                continue
            candidates.append(f)
        candidates = self._filter(
            candidates,
            exclude_legacy=exclude_legacy,
            min_status=min_status,
        )
        candidates.sort(key=lambda f: f.created_at, reverse=True)
        return candidates[:limit]

    def recall(
        self, query: str, k: int = 5, topic: str | None = None,
        *,
        exclude_legacy: bool = False,
        min_status: str | None = None,
        trust_signals: bool = False,  # cycle #119 wire — fake ignores
    ) -> list[tuple[_FakeFact, float]]:
        # Deterministic "score" = confidence (no embedding magic in fakes).
        # Cycle #119: trust_signals kwarg is accepted for back-compat,
        # but the fake never returns 3-tuples, so existing assertions stay.
        _ = trust_signals  # mark as used
        candidates: list[_FakeFact] = []
        for f in self._facts.values():
            if topic and f.topic != topic:
                continue
            candidates.append(f)
        candidates = self._filter(
            candidates,
            exclude_legacy=exclude_legacy,
            min_status=min_status,
        )
        candidates.sort(key=lambda f: f.confidence, reverse=True)
        return [(f, float(f.confidence)) for f in candidates[:k]]


class _FakeAgent:
    def __init__(self) -> None:
        self.semantic = _FakeSemantic()


# ---------- Helpers ------------------------------------------------------


async def _invoke_tool(name: str, arguments: dict[str, Any] | None = None):
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
def fake_agent(monkeypatch: pytest.MonkeyPatch) -> _FakeAgent:
    a = _FakeAgent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


def _payload(blocks: list[str]) -> dict[str, Any]:
    return json.loads(blocks[0])


# ---------- hippo_facts_search ------------------------------------------


class TestFactsSearchDefaultExcludesLegacy:

    @pytest.mark.asyncio
    async def test_default_excludes_legacy(self, fake_agent: _FakeAgent) -> None:
        blocks = await _invoke_tool(
            "hippo_facts_search", {"query": "alpha"},
        )
        payload = _payload(blocks)
        statuses = {it["status"] for it in payload["items"]}
        assert "legacy_unverified" not in statuses
        # the other three statuses survive
        assert {"verified", "model_claim", "provisional"} <= statuses

    @pytest.mark.asyncio
    async def test_include_legacy_true_returns_all(
        self, fake_agent: _FakeAgent,
    ) -> None:
        blocks = await _invoke_tool(
            "hippo_facts_search",
            {"query": "alpha", "include_legacy": True},
        )
        payload = _payload(blocks)
        statuses = {it["status"] for it in payload["items"]}
        assert "legacy_unverified" in statuses

    @pytest.mark.asyncio
    async def test_min_status_verified(
        self, fake_agent: _FakeAgent,
    ) -> None:
        blocks = await _invoke_tool(
            "hippo_facts_search",
            {"query": "alpha", "min_status": "verified"},
        )
        payload = _payload(blocks)
        ids = [it["id"] for it in payload["items"]]
        assert ids == ["f-verified"]


class TestFactsSearchOutputCarriesProvenance:

    @pytest.mark.asyncio
    async def test_items_include_status_field(
        self, fake_agent: _FakeAgent,
    ) -> None:
        blocks = await _invoke_tool(
            "hippo_facts_search",
            {"query": "alpha", "include_legacy": True},
        )
        payload = _payload(blocks)
        for it in payload["items"]:
            assert "status" in it
            assert "verified_by" in it
            assert isinstance(it["verified_by"], list)

    @pytest.mark.asyncio
    async def test_invalid_min_status_returns_error(
        self, fake_agent: _FakeAgent,
    ) -> None:
        """The MCP protocol layer enforces the enum schema before dispatch.

        Result is an ``isError=True`` payload with a plain-text
        ``Input validation error: ...`` message, not the dispatch-layer
        JSON error envelope.
        """
        from mcp.types import CallToolRequest, CallToolRequestParams
        handler = mcp_server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(
                name="hippo_facts_search",
                arguments={"query": "alpha", "min_status": "totally_bogus"},
            ),
        )
        result = await handler(req)
        payload = result.root if hasattr(result, "root") else result
        assert payload.isError is True
        text = payload.content[0].text
        assert "Input validation error" in text
        assert "totally_bogus" in text


# ---------- hippo_facts_recall ------------------------------------------


class TestFactsRecallDefaultExcludesLegacy:

    @pytest.mark.asyncio
    async def test_default_excludes_legacy(self, fake_agent: _FakeAgent) -> None:
        blocks = await _invoke_tool(
            "hippo_facts_recall", {"query": "alpha", "k": 10},
        )
        payload = _payload(blocks)
        statuses = {it["status"] for it in payload["items"]}
        assert "legacy_unverified" not in statuses

    @pytest.mark.asyncio
    async def test_include_legacy_true_returns_all(
        self, fake_agent: _FakeAgent,
    ) -> None:
        blocks = await _invoke_tool(
            "hippo_facts_recall",
            {"query": "alpha", "k": 10, "include_legacy": True},
        )
        payload = _payload(blocks)
        ids = [it["id"] for it in payload["items"]]
        assert "f-legacy" in ids

    @pytest.mark.asyncio
    async def test_min_status_model_claim(
        self, fake_agent: _FakeAgent,
    ) -> None:
        blocks = await _invoke_tool(
            "hippo_facts_recall",
            {"query": "alpha", "k": 10, "min_status": "model_claim"},
        )
        payload = _payload(blocks)
        ids = {it["id"] for it in payload["items"]}
        # verified + model_claim, not provisional, not legacy
        assert ids == {"f-verified", "f-model"}


class TestFactsRecallOutputCarriesProvenance:

    @pytest.mark.asyncio
    async def test_items_include_status_and_verified_by(
        self, fake_agent: _FakeAgent,
    ) -> None:
        blocks = await _invoke_tool(
            "hippo_facts_recall",
            {"query": "alpha", "k": 10, "include_legacy": True},
        )
        payload = _payload(blocks)
        # the verified fact carries its proof
        verified_items = [it for it in payload["items"] if it["status"] == "verified"]
        assert verified_items
        assert verified_items[0]["verified_by"] == ["bash:pytest:exit0"]

    @pytest.mark.asyncio
    async def test_invalid_min_status_returns_error(
        self, fake_agent: _FakeAgent,
    ) -> None:
        """Symmetric to hippo_facts_search: protocol enum gate fires first."""
        from mcp.types import CallToolRequest, CallToolRequestParams
        handler = mcp_server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(
                name="hippo_facts_recall",
                arguments={"query": "alpha", "min_status": "totally_bogus"},
            ),
        )
        result = await handler(req)
        payload = result.root if hasattr(result, "root") else result
        assert payload.isError is True
        text = payload.content[0].text
        assert "Input validation error" in text
        assert "totally_bogus" in text


class TestPayloadEchoesFilterParams:
    """The response echoes the resolved filter — useful for caller logs."""

    @pytest.mark.asyncio
    async def test_search_payload_echoes_params(
        self, fake_agent: _FakeAgent,
    ) -> None:
        blocks = await _invoke_tool(
            "hippo_facts_search",
            {"query": "alpha", "include_legacy": True, "min_status": "model_claim"},
        )
        payload = _payload(blocks)
        assert payload["include_legacy"] is True
        assert payload["min_status"] == "model_claim"

    @pytest.mark.asyncio
    async def test_recall_payload_echoes_params(
        self, fake_agent: _FakeAgent,
    ) -> None:
        blocks = await _invoke_tool(
            "hippo_facts_recall",
            {"query": "alpha", "include_legacy": False},
        )
        payload = _payload(blocks)
        assert payload["include_legacy"] is False
        # default min_status is None → echoed as null
        assert payload["min_status"] is None
