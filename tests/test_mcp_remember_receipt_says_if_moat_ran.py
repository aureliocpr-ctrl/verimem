"""The write channel an AGENT uses says nothing about whether the moat ran.

``verimem save`` prints a receipt line since 2026-07-28 — "grounded 99.9" or
"not verified — no source, so the entailment moat did not run". ``hippo_remember``
is the channel an agent actually writes through, and its reply is:

    {"ok": true, "confidence": 0.9, "status": "model_claim",
     "verified_by": [], "anti_confab_warnings": [], ...}

Nothing there is false, and nothing there says the moat never looked. An agent
reading ``ok: true`` with an empty warnings list concludes the write is fine.

Measured on the live store 2026-07-29, the shape of the damage: of 39 facts
written in 24h, the 28 written before the save rule started prescribing
``--source`` carry NO grounding score, and the 11 written after carry 99.9x.
The cut is exactly the rule change — because passing a source is the CALLER's
choice and the product never mentioned it.

Three states, not two. "No source given" and "source given but no judge
available" are different facts about the world, and collapsing them would
repeat the bug doctor was fixed for: a store it could not read reported as a
store with zero coverage.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from verimem import mcp_server
from verimem.semantic import SemanticMemory


@pytest.fixture
def real_sm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SemanticMemory:
    sm = SemanticMemory(db_path=tmp_path / "s.db")

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = sm

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    monkeypatch.delenv("ENGRAM_VALIDATE_DEFAULT", raising=False)
    monkeypatch.delenv("VERIMEM_MCP_TRUST_GATE_KNOBS", raising=False)
    return sm


async def _invoke(name: str, arguments: dict | None = None) -> dict[str, Any]:
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    text = next(c.text for c in payload.content if hasattr(c, "text"))
    return json.loads(text)


@pytest.mark.asyncio
async def test_a_write_without_a_source_says_the_moat_did_not_run(
    real_sm: SemanticMemory,
) -> None:
    out = await _invoke("hippo_remember", {
        "proposition": "The deployment finished at 4pm.",
        "topic": "test/receipt",
    })
    assert out["ok"] is True
    assert out.get("grounding_score") is None
    moat = out.get("moat", "")
    assert "no source" in moat.lower(), (
        f"the receipt must say the moat never looked; got {moat!r}"
    )
    assert "source" in moat.lower(), "it must name the argument that fixes it"


@pytest.mark.asyncio
async def test_the_receipt_field_is_always_present(
    real_sm: SemanticMemory,
) -> None:
    """Present on EVERY write, not only the interesting ones — a field that
    appears only sometimes is read as an anomaly flag rather than a status."""
    out = await _invoke("hippo_remember", {
        "proposition": "The build number is 4127.",
        "topic": "test/receipt",
        "source": "CI log line: build 4127 completed.",
    })
    assert "moat" in out and "grounding_score" in out


@pytest.mark.asyncio
async def test_a_source_that_could_not_be_judged_is_not_reported_as_unjudged(
    real_sm: SemanticMemory,
) -> None:
    """The UNKNOWN-vs-zero distinction. A caller who DID pass a source and got
    no judge must not read the same sentence as one who passed nothing —
    otherwise the advice ("pass a source") is wrong for the case at hand."""
    out = await _invoke("hippo_remember", {
        "proposition": "The invoice total is 1240 euro.",
        "topic": "test/receipt",
        "source": "Invoice #88: subtotal 1000, VAT 240, total 1240 euro.",
    })
    moat = out.get("moat", "")
    if out.get("grounding_score") is None:
        assert "no source" not in moat.lower(), (
            "a source WAS passed — saying 'no source' sends the caller to fix "
            f"something that is not broken; got {moat!r}"
        )
    else:
        assert str(round(float(out["grounding_score"]))) in moat or "judged" in moat.lower()


@pytest.mark.asyncio
async def test_no_judge_is_reported_as_no_judge_not_as_switched_off(
    real_sm: SemanticMemory, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The case a machine WITHOUT the CE model hits — CI, a fresh install.

    This branch used to read ENGRAM_GROUNDING_WRITE to decide its wording, which
    became wrong the moment this handler started passing ground_write itself: an
    absent env var now means "on by default", so the receipt would have
    announced a switch-off that never happened. Confidently wrong about its own
    state is the exact failure this receipt exists to prevent, so it is worth a
    test of its own rather than a careful reading.
    """
    from verimem import anti_confab_gate
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    monkeypatch.setattr(anti_confab_gate, "local_ce_available", lambda: False,
                        raising=False)

    out = await _invoke("hippo_remember", {
        "proposition": "The invoice total is 1240 euro.",
        "topic": "test/receipt",
        "source": "Invoice 88: subtotal 1000, VAT 240, total 1240 euro.",
    })
    moat = out.get("moat", "").lower()
    if out.get("grounding_score") is None:
        assert "switched off" not in moat and "is off" not in moat, (
            f"claims it is switched off when nothing switched it off: {moat!r}"
        )
        assert "judge" in moat, (
            f"must name the thing that was missing: {moat!r}"
        )
