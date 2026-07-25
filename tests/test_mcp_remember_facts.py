"""FORGIA pezzo #202 — MCP tools Wave 7 (DIRECT semantic memory).

Aurelio asked: "if I say 'save that my account is X', does it get
remembered?". Wave 7 closes the gap: a direct semantic-memory write/read
path that doesn't require an episode + sleep cycle.

* ``hippo_remember``      — store one Fact directly (proposition,
                             topic, confidence). Returns the fact id.
* ``hippo_facts_recall``  — semantic search over facts (cosine).
* ``hippo_facts_list``    — paginated listing of all facts.
* ``hippo_fact_forget``   — delete one fact by id (privacy/GDPR).
"""
from __future__ import annotations

import json
import time
from typing import Any

import pytest

from verimem import mcp_server

# ---------- Fakes --------------------------------------------------------


class _FakeFact:
    def __init__(self, fid: str, *, proposition: str, topic: str = "",
                  confidence: float = 0.9,
                  source_episodes: list[str] | None = None,
                  created_at: float | None = None) -> None:
        self.id = fid
        self.proposition = proposition
        self.topic = topic
        self.confidence = confidence
        self.source_episodes = source_episodes or []
        self.created_at = created_at or time.time()


class _FakeSemantic:
    def __init__(self) -> None:
        # Pre-populate with 2 facts.
        self._facts = {
            "f1": _FakeFact(
                "f1", proposition="The user's preferred editor is VS Code",
                topic="user_preferences",
                created_at=1000.0,
            ),
            "f2": _FakeFact(
                "f2", proposition="The user lives in Italy",
                topic="user_facts",
                created_at=1100.0,
            ),
        }
        self._stored: list[_FakeFact] = []
        self._deleted: list[str] = []

    def store(self, fact: _FakeFact, *,
               return_replaced: bool = False,
               coherence_hook=None, **_kw) -> bool | None:
        # Cycle #125: accept return_replaced + coherence_hook (cycle 119
        # wire) for back-compat with the production handler. Fake never
        # invokes the hook. **_kw tolerates future store kwargs (embed=...
        # on the quarantine path — 0.8 WS1 knob-policy tests).
        _ = coherence_hook
        existed = fact.id in self._facts
        self._facts[fact.id] = fact
        self._stored.append(fact)
        return existed if return_replaced else None

    def recall(self, query: str, k: int = 5,
                topic: str | None = None,
                *,
                exclude_legacy: bool = False,
                min_status: str | None = None,
                trust_signals: bool = False,  # cycle #119 wire — fake ignores
                ) -> list[tuple[_FakeFact, float]]:
        # Cycle #109 S4-A: accept new kw-only filters; fakes have no
        # ``status`` field so default filter is a no-op here.
        # Cycle #119: accept trust_signals kwarg for back-compat; fake
        # never returns 3-tuples, so existing tests stay correct.
        _ = trust_signals  # mark as used
        candidates = list(self._facts.values())
        if topic:
            candidates = [f for f in candidates if f.topic == topic]
        # Naive scoring: 1.0 if substring overlaps, 0.5 else.
        scored = []
        ql = (query or "").lower()
        for f in candidates:
            score = 1.0 if ql and ql in f.proposition.lower() else 0.5
            scored.append((f, score))
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:k]

    def all(self) -> list[_FakeFact]:
        return sorted(self._facts.values(), key=lambda f: f.created_at,
                       reverse=True)

    def count(self) -> int:
        return len(self._facts)

    def delete(self, fact_id: str, *, principal: str = "test:fake",
               action: str = "delete") -> bool:
        # Mirror the real core's 0.8 mutation-audit signature (keyword-only
        # principal + audit action label) so the MCP handler can call it.
        if fact_id in self._facts:
            del self._facts[fact_id]
            self._deleted.append(fact_id)
            return True
        return False


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
    # Patch _build_fact factory used by the handler so it returns a fake.
    def _factory(proposition: str, topic: str = "",
                  confidence: float = 0.9,
                  source_episodes: list[str] | None = None,
                  *,
                  verified_by: list[str] | None = None,
                  status: str = "model_claim",
                  source_signature: str | None = None,
                  writer_role: str = "agent_inference",
                  meta_narrative: bool = False,
                  **_kw) -> _FakeFact:  # tollera kw futuri (valid_until, ...)
        # Cycle #109 S2/S4-A: accept the new kw-only provenance fields.
        # Cycle 2026-05-27 round 12 F-fix: also accept writer_role +
        # meta_narrative (schema v6). The fake doesn't persist them
        # (not exercised by this suite), but it must not error when the
        # dispatch passes them.
        import uuid
        return _FakeFact(
            uuid.uuid4().hex[:12],
            proposition=proposition, topic=topic,
            confidence=confidence,
            source_episodes=source_episodes or [],
        )
    monkeypatch.setattr(mcp_server, "_build_fact", _factory, raising=False)
    return a


# ---------- listing -----------------------------------------------------


@pytest.mark.asyncio
async def test_wave7_tools_listed(fake_agent: _FakeAgent) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    for n in ("hippo_remember", "hippo_facts_recall",
              "hippo_facts_list", "hippo_fact_forget"):
        assert n in names, f"missing tool: {n}"


# ---------- hippo_remember ---------------------------------------------


@pytest.mark.asyncio
async def test_remember_stores_fact(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_remember",
        {"proposition": "User email is user@example.com",
         "topic": "user_facts",
         "confidence": 0.95},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    assert "id" in payload
    assert payload["proposition"] == "User email is user@example.com"
    assert payload["topic"] == "user_facts"
    assert payload["confidence"] == 0.95
    assert len(fake_agent.semantic._stored) == 1


@pytest.mark.asyncio
async def test_remember_minimal_inputs(fake_agent: _FakeAgent) -> None:
    """Topic and confidence are optional; defaults apply."""
    blocks = await _invoke_tool(
        "hippo_remember",
        {"proposition": "The sky is blue"},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    assert payload["topic"] == ""
    assert payload["confidence"] == 0.9  # default


@pytest.mark.asyncio
async def test_remember_empty_proposition_rejected(
    fake_agent: _FakeAgent,
) -> None:
    blocks = await _invoke_tool("hippo_remember", {"proposition": ""})
    payload = json.loads(blocks[0])
    assert "error" in payload


# ---------- hippo_facts_recall -----------------------------------------


@pytest.mark.asyncio
async def test_facts_recall_finds_match(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_facts_recall", {"query": "Italy", "k": 3},
    )
    payload = json.loads(blocks[0])
    items = payload["items"]
    assert any("Italy" in it["proposition"] for it in items)


@pytest.mark.asyncio
async def test_facts_recall_topic_filter(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_facts_recall",
        {"query": "anything", "topic": "user_preferences"},
    )
    payload = json.loads(blocks[0])
    items = payload["items"]
    assert all(it["topic"] == "user_preferences" for it in items)
    # Only f1 in user_preferences
    assert len(items) == 1


# ---------- hippo_facts_list -------------------------------------------


@pytest.mark.asyncio
async def test_facts_list_default(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool("hippo_facts_list", {})
    payload = json.loads(blocks[0])
    assert payload["total"] == 2
    items = payload["items"]
    assert len(items) == 2
    # Newest first.
    assert items[0]["id"] == "f2"
    assert items[1]["id"] == "f1"


@pytest.mark.asyncio
async def test_facts_list_pagination(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_facts_list", {"limit": 1, "offset": 1},
    )
    payload = json.loads(blocks[0])
    items = payload["items"]
    assert len(items) == 1
    assert items[0]["id"] == "f1"


# ---------- hippo_fact_forget -----------------------------------------


@pytest.mark.asyncio
async def test_fact_forget_deletes(fake_agent: _FakeAgent) -> None:
    # Cycle 15 FIX 6: gate is OFF by default in dev. These tests don't
    # need _user_confirmed since the gate is short-circuited unless the
    # ENGRAM_CAPABILITY_GATE env var is set.
    blocks = await _invoke_tool(
        "hippo_fact_forget",
        {"fact_id": "f1"},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    assert "f1" in fake_agent.semantic._deleted


@pytest.mark.asyncio
async def test_fact_forget_unknown(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_fact_forget",
        {"fact_id": "ghost"},
    )
    payload = json.loads(blocks[0])
    assert "error" in payload


# ---------- gate-knob policy (0.8 WS1: untrusted args can't weaken) ------
#
# The MCP surface is UNTRUSTED (shared server; args come from any client),
# yet `validate="off"` skipped the anti-confab gate entirely and
# `force_persist=True` overrode a downgrade/reject verdict. Policy: the
# WEAKENING knobs are honoured only when the OPERATOR opted in via
# VERIMEM_MCP_TRUST_GATE_KNOBS=1; otherwise they are neutralized and the
# response says so (`gate_knobs_denied`) — observable, never silent.
# Strengthening values (validate="full", gate_mode="reject") always pass.

#: First-person software self-claim — the L1 agent-confab pin class the
#: 0.7.0 domain-precision cycle kept escalating (never admitted bare).
_SELF_CLAIM = "I have completed the migration and everything works perfectly now"


@pytest.fixture
def spy_agent(monkeypatch: pytest.MonkeyPatch) -> dict:
    """fake_agent variant whose _build_fact records the status the handler
    computed — the direct signal of whether the gate actually ran."""
    a = _FakeAgent()
    seen: dict[str, Any] = {"agent": a}
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)

    def _factory(proposition: str, topic: str = "", confidence: float = 0.9,
                 source_episodes: list[str] | None = None, *,
                 status: str = "model_claim", **_kw) -> _FakeFact:
        import uuid
        seen["status"] = status
        return _FakeFact(uuid.uuid4().hex[:12], proposition=proposition,
                         topic=topic, confidence=confidence,
                         source_episodes=source_episodes or [])

    monkeypatch.setattr(mcp_server, "_build_fact", _factory, raising=False)
    monkeypatch.delenv("VERIMEM_MCP_TRUST_GATE_KNOBS", raising=False)
    return seen


@pytest.mark.asyncio
async def test_validate_off_denied_by_default(spy_agent: dict) -> None:
    blocks = await _invoke_tool(
        "hippo_remember", {"proposition": _SELF_CLAIM, "validate": "off"})
    payload = json.loads(blocks[0])
    assert payload.get("gate_knobs_denied") == ["validate=off"]
    # the gate really ran: the self-claim was downgraded, not admitted
    assert spy_agent.get("status") == "quarantined"


@pytest.mark.asyncio
async def test_force_persist_denied_by_default(spy_agent: dict) -> None:
    blocks = await _invoke_tool(
        "hippo_remember", {"proposition": _SELF_CLAIM, "force_persist": True})
    payload = json.loads(blocks[0])
    assert payload.get("gate_knobs_denied") == ["force_persist"]
    assert spy_agent.get("status") == "quarantined"


@pytest.mark.asyncio
async def test_operator_opt_in_restores_legacy_knobs(
        spy_agent: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERIMEM_MCP_TRUST_GATE_KNOBS", "1")
    blocks = await _invoke_tool(
        "hippo_remember", {"proposition": _SELF_CLAIM, "validate": "off"})
    payload = json.loads(blocks[0])
    assert not payload.get("gate_knobs_denied")
    assert spy_agent.get("status") == "model_claim"  # gate skipped, as asked


@pytest.mark.asyncio
async def test_denied_validate_off_defers_to_operator_default(
        spy_agent: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """Critic counterexample on 4a37b09: neutralizing validate="off" to the
    CONSTANT "fast" still let an untrusted client downgrade an operator who
    configured ENGRAM_VALIDATE_DEFAULT=full (L3 contradiction checks run only
    at full). The refused knob must defer to the operator's default — the
    gate must receive validate=None, never a handler-chosen constant."""
    import verimem.anti_confab_gate as acg
    seen_kw: dict = {}
    real_gate = acg.run_validation_gate

    def spy_gate(**kw):
        seen_kw.update(kw)
        return real_gate(**kw)

    # the handler does `from .anti_confab_gate import run_validation_gate`
    # inside the function body, so patch the SOURCE module attribute
    monkeypatch.setattr(acg, "run_validation_gate", spy_gate)
    blocks = await _invoke_tool(
        "hippo_remember", {"proposition": _SELF_CLAIM, "validate": "off"})
    payload = json.loads(blocks[0])
    assert payload.get("gate_knobs_denied") == ["validate=off"]
    assert seen_kw.get("validate") is None, (
        "a refused weakening knob must fall back to the operator default "
        f"(None), not a constant — got {seen_kw.get('validate')!r}")


@pytest.mark.asyncio
async def test_strengthening_values_never_denied(spy_agent: dict) -> None:
    blocks = await _invoke_tool(
        "hippo_remember",
        {"proposition": "The sky is blue", "validate": "fast",
         "gate_mode": "reject"})
    payload = json.loads(blocks[0])
    assert not payload.get("gate_knobs_denied")
    assert payload["ok"] is True
