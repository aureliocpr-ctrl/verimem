"""A source given to the MCP channel must actually be checked, not just stored.

anti_confab_gate:1318 resolves the moat from two switches:

    _ground_on = _grounding_write_on() if ground_write is None else bool(ground_write)

The SDK's ``balanced`` preset passes ``ground=True``, so the CLI judges. The MCP
handler passed nothing and fell through to ENGRAM_GROUNDING_WRITE, which nothing
in the source tree sets — so a write carrying a real source landed with
grounding_score NULL and an ``ok: true`` reply, indistinguishable from a write
carrying none (measured on the live store 2026-07-29).

This is not a new default. Commit ebab6e92 (2026-07-17) documented "the moat is
ON by default" and was accurate — of the SDK path. Its evidence line reads
"Verified by the hardening-audit moat probe", and that probe runs on the path
that already had it right. This makes the second channel keep the contract the
first one already advertised.

Cost, measured the same day over 4 MCP writes on a temp store:

    off   first 0.24s   steady 0.10s
    on    first 28.8s   steady 0.46s     (+0.36s per write; 28.8s is the CE
                                          cold-load, once per PROCESS — once
                                          per session on a long-lived server)

An explicit ENGRAM_GROUNDING_WRITE=0 still wins: an operator who has switched
the moat off stays switched off.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from verimem import anti_confab_gate, mcp_server
from verimem.semantic import SemanticMemory


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    """Wrap the real gate so the flow stays real and the kwarg is observed."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")

    class _A:
        def __init__(self) -> None:
            self.semantic = sm

    monkeypatch.setattr(mcp_server, "_ag", lambda: _A())
    monkeypatch.delenv("ENGRAM_VALIDATE_DEFAULT", raising=False)
    monkeypatch.delenv("VERIMEM_MCP_TRUST_GATE_KNOBS", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)

    seen: dict[str, Any] = {}
    real = anti_confab_gate.run_validation_gate

    def _spy(**kwargs: Any):
        seen["ground_write"] = kwargs.get("ground_write")
        seen["source"] = kwargs.get("source")
        # Judge-less: no llm injected and the local CE may or may not be on
        # disk. What is asserted here is the REQUEST, not the verdict.
        return real(**{**kwargs, "grounding_llm": None})

    monkeypatch.setattr(anti_confab_gate, "run_validation_gate", _spy)
    return seen


async def _invoke(name: str, arguments: dict | None = None) -> dict[str, Any]:
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return json.loads(next(c.text for c in payload.content if hasattr(c, "text")))


@pytest.mark.asyncio
async def test_a_source_makes_the_channel_ask_for_the_moat(
    captured: dict[str, Any],
) -> None:
    await _invoke("hippo_remember", {
        "proposition": "The invoice total is 1240 euro.",
        "topic": "test/moat",
        "source": "Invoice 88: subtotal 1000, VAT 240, total 1240 euro.",
    })
    assert captured["source"], "the source never reached the gate"
    assert captured["ground_write"] is True, (
        "the MCP channel stored a sourced write without asking for the "
        "entailment check the SDK channel asks for"
    )


@pytest.mark.asyncio
async def test_without_a_source_nothing_is_requested(
    captured: dict[str, Any],
) -> None:
    """No source means nothing to entail — asking would buy a cold-load for a
    check that cannot run."""
    await _invoke("hippo_remember", {
        "proposition": "The deployment finished at 4pm.",
        "topic": "test/moat",
    })
    assert captured["ground_write"] is not True


@pytest.mark.asyncio
async def test_an_operator_who_switched_it_off_stays_off(
    captured: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The env keeps its power to DISABLE. Changing a default must not take
    away a switch someone is already using."""
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "0")
    await _invoke("hippo_remember", {
        "proposition": "The invoice total is 1240 euro.",
        "topic": "test/moat",
        "source": "Invoice 88: subtotal 1000, VAT 240, total 1240 euro.",
    })
    assert captured["ground_write"] is False
