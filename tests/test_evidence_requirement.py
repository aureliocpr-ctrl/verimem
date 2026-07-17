"""Tier-1 evidence requirement (deterministic anti-confab-sottile).

A new fact asserting a SPECIFIC checkable value (a quantity or a year) with
NO `verified_by` evidence is not hype (L1) nor a contradiction (L3) — the
keyword/contradiction gates miss it. But a specific claim with zero
provenance is exactly the subtle-confab risk, so we don't fully TRUST it: its
confidence is CAPPED (it ranks below sourced/corroborated facts and reads as
unverified) until sourced or corroborated. Deterministic, opt-in (default
OFF). Confidence — not a new status — because `provisional` is reserved by
the store layer for URL-backed hypotheses.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from verimem import mcp_server
from verimem.evidence_requirement import (
    UNSOURCED_SPECIFIC_CEILING,
    evidence_requirement_enabled,
    is_specific_claim,
    resolve_write_confidence,
)
from verimem.semantic import SemanticMemory

# ---------- is_specific_claim -------------------------------------------


def test_specific_claim_detects_quantity_and_year() -> None:
    assert is_specific_claim("The cache holds 1024 entries.")
    assert is_specific_claim("Sessions expire after 30 minutes.")
    assert is_specific_claim("The library shipped in 2024.")  # year


def test_generic_claim_is_not_specific() -> None:
    assert not is_specific_claim("The system is fast and reliable.")
    assert not is_specific_claim("Authentication uses a hashing scheme.")
    # commit SHAs / versions are NOT quantities (anchor) → not 'specific'
    assert not is_specific_claim("Shipped commit a64d252 to main.")


# ---------- resolve_write_confidence ------------------------------------


def test_caps_specific_unsourced_confidence() -> None:
    c = resolve_write_confidence(
        "The cache holds 4096 entries.", [],
        requested_confidence=0.9, enabled=True,
    )
    assert c == UNSOURCED_SPECIFIC_CEILING == 0.6


def test_sourced_specific_confidence_unchanged() -> None:
    c = resolve_write_confidence(
        "The cache holds 4096 entries.", ["file:engram/cache.py:88"],
        requested_confidence=0.9, enabled=True,
    )
    assert c == 0.9


def test_generic_confidence_unchanged() -> None:
    c = resolve_write_confidence(
        "The system is fast.", [],
        requested_confidence=0.9, enabled=True,
    )
    assert c == 0.9


def test_already_low_confidence_not_raised() -> None:
    # The rule only WITHHOLDS trust, never raises it.
    c = resolve_write_confidence(
        "The cache holds 4096 entries.", [],
        requested_confidence=0.3, enabled=True,
    )
    assert c == 0.3


def test_disabled_is_passthrough() -> None:
    c = resolve_write_confidence(
        "The cache holds 4096 entries.", [],
        requested_confidence=0.9, enabled=False,
    )
    assert c == 0.9


# ---------- env flag (default OFF) --------------------------------------


def test_enabled_flag_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENGRAM_EVIDENCE_REQUIREMENT", raising=False)
    assert evidence_requirement_enabled() is False
    monkeypatch.setenv("ENGRAM_EVIDENCE_REQUIREMENT", "1")
    assert evidence_requirement_enabled() is True
    monkeypatch.setenv("ENGRAM_EVIDENCE_REQUIREMENT", "off")
    assert evidence_requirement_enabled() is False


# ---------- end-to-end wire through the hippo_remember handler ----------


@pytest.fixture
def _sm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SemanticMemory:
    sm = SemanticMemory(db_path=tmp_path / "s.db")

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = sm

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    monkeypatch.delenv("ENGRAM_VALIDATE_DEFAULT", raising=False)
    return sm


async def _invoke(name: str, arguments: dict) -> dict:
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    text = next(c.text for c in payload.content if hasattr(c, "text"))
    return json.loads(text)


@pytest.mark.asyncio
async def test_e2e_specific_unsourced_capped_when_enabled(
    _sm: SemanticMemory, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENGRAM_EVIDENCE_REQUIREMENT", "1")
    out = await _invoke("hippo_remember", {
        "proposition": "The widget cache holds 4096 entries.",
        "topic": "t/test",
        "confidence": 0.9,
        "verified_by": [],  # specific + unsourced + not hype + not contradicted
    })
    assert out.get("ok") is True
    f = _sm.get(out["id"])
    assert f is not None
    assert f.confidence <= UNSOURCED_SPECIFIC_CEILING, (
        f"specific unsourced claim must be confidence-capped, got {f.confidence}"
    )
    # NOT quarantined — still recallable, just low-trust.
    assert f.status == "model_claim"


@pytest.mark.asyncio
async def test_e2e_sourced_specific_keeps_confidence(
    _sm: SemanticMemory, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENGRAM_EVIDENCE_REQUIREMENT", "1")
    out = await _invoke("hippo_remember", {
        "proposition": "The widget cache holds 4096 entries.",
        "topic": "t/test",
        "confidence": 0.9,
        "verified_by": ["file:engram/cache.py:88"],
    })
    f = _sm.get(out["id"])
    assert f is not None and f.confidence == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_e2e_disabled_preserves_confidence(
    _sm: SemanticMemory, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENGRAM_EVIDENCE_REQUIREMENT", raising=False)
    out = await _invoke("hippo_remember", {
        "proposition": "The widget cache holds 4096 entries.",
        "topic": "t/test",
        "confidence": 0.9,
        "verified_by": [],
    })
    f = _sm.get(out["id"])
    assert f is not None and f.confidence == pytest.approx(0.9)
