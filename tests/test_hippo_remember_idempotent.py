"""Cycle #46b — genuine idempotency for hippo_remember entry point.

Critic-found 2026-05-14 (cycle #46 job 18fcf29972455067, counterexample
confidence 0.90): `_build_fact` constructs Fact() without explicit id;
the default_factory is `uuid.uuid4().hex[:12]` (RANDOM, NOT content-hash).
Consequence: two `hippo_remember` calls with the SAME (proposition, topic)
produce TWO distinct random ids → two distinct rows → audit reports
2× ok_new, 0× ok_replaced. The observability infrastructure added in
cycle #46 was correctly wired but the entry point never triggered it.

This cycle (46b) fixes the root cause: `_build_fact` now derives the id
deterministically from `(proposition, topic)` via SHA256-truncated-12.
- Two identical calls → SAME id → SELECT pre-INSERT matches →
  was_replaced=True → audit outcome `ok_replaced`.
- Different proposition OR different topic → DIFFERENT id → fresh row.

Trade-off: this is a BEHAVIOR CHANGE. Pre-#46b: 2 identical calls
produced 2 rows. Post-#46b: 2 identical calls produce 1 row with
observable overwrite. Caller code that relied on accidental duplication
will see fewer rows — but no caller actually relied on that (it was a
bug, not a feature, per cycle #46 decision-trajectory 685d31c9d85b
which chose "keep idempotency + add observability").
"""
from __future__ import annotations

import json

import pytest
from mcp.types import CallToolRequest, CallToolRequestParams

from verimem import mcp_server

# ---------------------------------------------------------------------------
# Stub agent: hippo_remember handler only touches `a.semantic`, mock that.
# ---------------------------------------------------------------------------


class _FakeSemantic:
    """In-memory semantic store that mimics SemanticMemory.store(return_replaced)."""

    def __init__(self) -> None:
        self._facts: dict[str, dict] = {}  # id -> {proposition, topic, ...}

    def store(self, fact, *, return_replaced: bool = False,
               coherence_hook=None, embed: str = "sync"):
        # Cycle #125: accept coherence_hook kwarg (added by cycle 119
        # wire in mcp_server.py) for back-compat; the fake never
        # invokes it — pure observability extension.
        # 2026-06-05: accept embed kwarg (non-blocking store wiring).
        _ = (coherence_hook, embed)
        existed = fact.id in self._facts
        self._facts[fact.id] = {
            "id": fact.id,
            "proposition": fact.proposition,
            "topic": fact.topic,
            "confidence": fact.confidence,
        }
        return existed if return_replaced else None

    def count(self) -> int:
        return len(self._facts)


class _StubAgent:
    def __init__(self) -> None:
        self.semantic = _FakeSemantic()
        self.skills = None
        self.memory = None


@pytest.fixture
def agent(monkeypatch: pytest.MonkeyPatch) -> _StubAgent:
    a = _StubAgent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    monkeypatch.setattr(mcp_server, "_agent", a, raising=False)
    return a


async def _invoke_remember(
    proposition: str, topic: str = "", confidence: float = 0.9,
) -> dict:
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(
            name="hippo_remember",
            arguments={"proposition": proposition, "topic": topic,
                       "confidence": confidence},
        ),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    text_blocks = [c.text for c in payload.content if hasattr(c, "text")]
    assert text_blocks
    return json.loads(text_blocks[0])


# ---------------------------------------------------------------------------
# RED tests — must fail pre-#46b (random uuid, no idempotency),
# pass post-#46b (content-hash deterministic id).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_identical_calls_produce_single_row(agent: _StubAgent) -> None:
    """Two identical (proposition, topic) calls → 1 row in DB.

    Pre-fix: 2 random uuids → 2 distinct rows. Test FAILS (count==2).
    Post-fix: same content-hash id → 1 row. Test PASSES.
    """
    out1 = await _invoke_remember("Pi is 3.14159", topic="math/constants")
    out2 = await _invoke_remember("Pi is 3.14159", topic="math/constants")

    assert agent.semantic.count() == 1, (
        f"Expected 1 row after identical calls, got {agent.semantic.count()}"
    )
    # ids must match (deterministic from content)
    assert out1["id"] == out2["id"]


@pytest.mark.asyncio
async def test_identical_calls_emit_ok_replaced_on_second(
    agent: _StubAgent,
) -> None:
    """Second identical call MUST report replaced=True."""
    out1 = await _invoke_remember("e is 2.71828", topic="math/constants")
    out2 = await _invoke_remember("e is 2.71828", topic="math/constants")

    assert out1.get("replaced") is False, f"first call replaced field: {out1}"
    assert out2.get("replaced") is True, (
        f"second call must show replaced=True, got: {out2}"
    )


@pytest.mark.asyncio
async def test_different_proposition_different_id(agent: _StubAgent) -> None:
    """Different propositions → different content-hash ids → 2 rows."""
    out1 = await _invoke_remember("first fact", topic="t/a")
    out2 = await _invoke_remember("second fact", topic="t/a")

    assert out1["id"] != out2["id"]
    assert agent.semantic.count() == 2


@pytest.mark.asyncio
async def test_different_topic_different_id(agent: _StubAgent) -> None:
    """Same proposition, different topic → different id → 2 rows.

    Topic is part of the identity (a fact is qualified by its topic).
    """
    out1 = await _invoke_remember("water boils at 100C", topic="physics/basic")
    out2 = await _invoke_remember("water boils at 100C", topic="cooking/recipes")

    assert out1["id"] != out2["id"]
    assert agent.semantic.count() == 2


@pytest.mark.asyncio
async def test_id_deterministic_across_processes(agent: _StubAgent) -> None:
    """The id derivation must be a pure function — same input, same output,
    regardless of process state. We can test this by calling the internal
    _build_fact factory directly."""
    f1 = mcp_server._build_fact("the cat is on the mat", topic="lit/example")
    f2 = mcp_server._build_fact("the cat is on the mat", topic="lit/example")
    assert f1.id == f2.id
    # And different from a different content
    f3 = mcp_server._build_fact("the dog is on the mat", topic="lit/example")
    assert f1.id != f3.id


@pytest.mark.asyncio
async def test_confidence_does_not_affect_id(agent: _StubAgent) -> None:
    """Confidence is data, not identity — different confidence on same
    (proposition, topic) should overwrite, not duplicate."""
    out1 = await _invoke_remember("X is true", topic="t/x", confidence=0.5)
    out2 = await _invoke_remember("X is true", topic="t/x", confidence=0.95)
    assert agent.semantic.count() == 1
    assert out1["id"] == out2["id"]


# ---------------------------------------------------------------------------
# Critic-counterexample (job c57a5e9c4dbb1628 worker 'counterexample' 0.85):
# the first draft of _content_hash_id used `f"{prop}\x00{topic}"` which is
# NOT injective under NUL injection. Two semantically distinct (prop, topic)
# pairs could hash to the same id, silently overwriting and emitting a false
# `ok_replaced` audit outcome. These tests pin the FIX (json.dumps payload).
# ---------------------------------------------------------------------------


def test_content_hash_no_nul_separator_collision() -> None:
    """NUL bytes in proposition or topic must not cause id collision.

    Adversarial input: NUL is valid in Python str, passes through JSON-RPC,
    and is not stripped by .strip(). Pre-fix payload f"{p}\\x00{t}" gives:
      ("A", "B\\x00C") → b"A\\x00B\\x00C" → same as
      ("A\\x00B", "C") → b"A\\x00B\\x00C" → COLLISION

    Post-fix (json.dumps) gives different payloads:
      ["A", "B\\x00C"] → '["A", "B\\u0000C"]'   (length-prefixed by quotes+commas)
      ["A\\x00B", "C"] → '["A\\u0000B", "C"]'   (different bytes)
    → different SHA256 → different ids.
    """
    id_a = mcp_server._content_hash_id("A", "B\x00C")
    id_b = mcp_server._content_hash_id("A\x00B", "C")
    assert id_a != id_b, (
        f"NUL injection collision: ('A', 'B\\x00C') and ('A\\x00B', 'C') "
        f"BOTH hashed to {id_a!r} — _content_hash_id is not injective"
    )


def test_content_hash_no_quote_injection_collision() -> None:
    """Similar adversarial: quote injection between proposition and topic.

    Pre-fix with f-string concat, no encoding of structural chars, an
    attacker (or accidental input) could craft strings that collapse to
    the same payload. json.dumps escapes quotes inside strings, so
    structural quote characters in the payload remain meaningful.
    """
    id_a = mcp_server._content_hash_id('X"', '"Y')
    id_b = mcp_server._content_hash_id('X""Y', '')
    assert id_a != id_b


def test_content_hash_topic_empty_distinct_from_topic_word() -> None:
    """Empty topic and explicit short topic must produce different ids."""
    assert (
        mcp_server._content_hash_id("hello", "")
        != mcp_server._content_hash_id("hello", "a")
    )


def test_content_hash_unicode_handled() -> None:
    """Unicode in proposition/topic produces stable, distinct ids."""
    id_caffe = mcp_server._content_hash_id("café", "drinks")
    id_caffe_again = mcp_server._content_hash_id("café", "drinks")
    id_cafe = mcp_server._content_hash_id("cafe", "drinks")
    assert id_caffe == id_caffe_again  # deterministic
    assert id_caffe != id_cafe  # unicode-precise
