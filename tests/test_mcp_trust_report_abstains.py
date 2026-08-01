"""The dossier promised abstention and shipped with both checks inert.

The MCP server's own instructions say: "on a question it cannot support it
ABSTAINS ('I don't know') instead of stitching a guess from weak matches". The
handler called build_trust_report without ``ce_gate`` and without ``llm``, so
the two things that produce an abstention were both off:

    "verify": {"ce_gate": "off", "sufficiency": "off"},  "abstained": false

Measured on the live store 2026-07-29, ten questions — five the corpus supports
and five plausible inventions:

    ce_gate OFF   abstentions 0/5   false abstentions 0/5   1.47s avg
    ce_gate ON    abstentions 4/5   false abstentions 0/5   5.82s avg

Zero false abstentions is what makes the default safe to flip: the gate never
withheld an answer the corpus could support. "quale database usa il modulo di
fatturazione di verimem" — a module that does not exist — returned five facts
about CI and roadmaps at relevance 0.85, and the CLI `trust` command called an
invention with an ISO 27001 date "TRUSTED, adequate evidence".

The remaining 1/5 is NOT closed by this and is not claimed to be: "chi è il
responsabile marketing" keeps a fact that is on-topic (CE +1.01) and names a
person in a different role. That needs the question-aware sufficiency judge,
which needs an llm — so the llm the agent already carries is passed through
here, and ``verify`` keeps declaring which checks actually ran.

Same shape as the comment two lines above the call: "critic O3 caveat
2026-07-06: the floor was SDK-only". A critic flagged the SDK-only class three
weeks ago; min_relevance was wired and ce_gate was left behind.
"""
from __future__ import annotations

import json
import types
from pathlib import Path
from typing import Any

import pytest

from verimem import mcp_server, trust_report


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    from verimem.semantic import SemanticMemory
    sm = SemanticMemory(db_path=tmp_path / "s.db")

    class _A:
        def __init__(self) -> None:
            self.semantic = sm
            self.wake = types.SimpleNamespace(llm=object())

    monkeypatch.setattr(mcp_server, "_ag", lambda: _A())

    seen: dict[str, Any] = {}
    real = trust_report.build_trust_report

    def _spy(sm_, query, **kw):
        seen.update(kw)
        # never let the real CE load in a unit test
        return real(sm_, query, **{**kw, "ce_gate": False, "llm": None})

    monkeypatch.setattr(trust_report, "build_trust_report", _spy)
    return seen


async def _invoke(name: str, arguments: dict | None = None) -> dict[str, Any]:
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    result = await handler(CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    ))
    payload = result.root if hasattr(result, "root") else result
    return json.loads(next(c.text for c in payload.content if hasattr(c, "text")))


@pytest.mark.asyncio
async def test_the_abstention_gate_is_on_by_default(spy: dict[str, Any]) -> None:
    await _invoke("hippo_trust_report", {"query": "quale database usa il "
                                         "modulo di fatturazione"})
    assert spy.get("ce_gate") is True, (
        "the dossier that advertises abstention asked for it to be skipped"
    )


@pytest.mark.asyncio
async def test_the_judge_the_agent_carries_is_passed_through(
    spy: dict[str, Any],
) -> None:
    """sufficiency needs an llm and the handler had none to give — so the
    check that closes the on-topic-but-not-an-answer residual could never run,
    no matter how the server was configured."""
    await _invoke("hippo_trust_report", {"query": "una domanda qualunque"})
    assert spy.get("llm") is not None, (
        "the agent's judge never reached the sufficiency check"
    )


@pytest.mark.asyncio
async def test_a_caller_can_still_turn_it_off(spy: dict[str, Any]) -> None:
    """Flipping a default must not remove the choice — a caller who wants the
    raw nearest-matches (debugging retrieval, say) asks for them."""
    await _invoke("hippo_trust_report", {"query": "x", "ce_gate": False})
    assert spy.get("ce_gate") is False
