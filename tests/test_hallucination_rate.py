"""hallucination-rate@k — la metrica del fossato anti-confabulazione (MOSSA 2,
2026-06-15).

Mem0/Zep recuperano fatti senza alcun segnale di affidabilita': ogni hit e' "da
verificare" by construction, quindi la loro hallucination-rate@k e' ~1.0. Engram
attacca a ogni hit un trust_signal (trusted/stale/contested/obsolete/unverified):
questa metrica quantifica la frazione dei top-k recuperati che NON sono fidati =
il rischio-allucinazione che il recall espone al chiamante. E' il numero che mem0
non puo' nemmeno misurare (non ha status/supersession/contradiction).
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from engram.hallucination_rate import (
    _RISKY_VERDICTS,
    hallucination_rate_at_k,
    rate_from_verdicts,
)
from engram.semantic import Fact, SemanticMemory

# ---- core puro: aggregazione deterministica dai verdetti --------------------

def test_rate_from_verdicts_all_trusted_is_zero():
    risky, stale = rate_from_verdicts(["trusted", "trusted", "trusted"])
    assert risky == 0.0 and stale == 0.0


def test_rate_from_verdicts_counts_risky_not_stale():
    # 2 risky (obsolete, unverified) + 1 stale + 1 trusted su 4 -> risky 0.5, stale 0.25
    risky, stale = rate_from_verdicts(["obsolete", "unverified", "stale", "trusted"])
    assert risky == pytest.approx(0.5)
    assert stale == pytest.approx(0.25)


def test_rate_from_verdicts_empty_is_zero():
    assert rate_from_verdicts([]) == (0.0, 0.0)


def test_risky_set_is_the_three_unreliable_verdicts():
    # contract-lock: obsolete/contested/unverified sono "rischio"; trusted/stale no.
    assert _RISKY_VERDICTS == frozenset({"obsolete", "contested", "unverified"})


# ---- integrazione end-to-end attraverso recall(trust_signals=True) ----------

def test_hallucination_rate_zero_on_all_verified_corpus(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "0")  # isola la metrica dal fusion
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    for i in range(3):
        sm.store(Fact(proposition=f"the deploy region is eu-west-{i}", topic="t",
                      status="verified", confidence=0.95, source_episodes=["e"]),
                 embed="sync")
    out = hallucination_rate_at_k(sm, ["deploy region"], k=3)
    assert out["hallucination_rate_at_k"] == 0.0, out
    assert out["verdict_breakdown"]["trusted"] >= 1, out


def test_hallucination_rate_flags_unverified_fact(tmp_path, monkeypatch):
    """Il recall di default GIA' filtra obsolete/orphaned/quarantined/legacy (il
    bene di Engram, verificato altrove): non sono il rischio che la metrica
    misura. Il rischio che il recall ESPONE e' un model_claim a bassa confidence
    -> trust_signal lo marca 'unverified' -> conta nella hallucination-rate.
    E' il rischio residuo post-filtri; mem0 lo esporrebbe per OGNI fatto."""
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "0")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="the api key rotation interval is 30 days", topic="t",
                  status="model_claim", confidence=0.3, source_episodes=["e"]),
             embed="sync")
    out = hallucination_rate_at_k(sm, ["api key rotation interval"], k=5)
    assert out["hallucination_rate_at_k"] > 0.0, out
    assert out["verdict_breakdown"]["unverified"] >= 1, out


def test_hallucination_rate_skips_queries_without_hits(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "0")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="kubernetes ingress uses nginx", topic="t",
                  status="verified", confidence=0.9, source_episodes=["e"]),
             embed="sync")
    # una query con hit + una senza (whitespace) -> n_queries_with_hits conta solo la prima.
    out = hallucination_rate_at_k(sm, ["kubernetes ingress", "   "], k=5)
    assert out["n_queries_with_hits"] == 1, out


def test_hallucination_rate_empty_queries_is_safe(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    out = hallucination_rate_at_k(sm, [], k=5)
    assert out["hallucination_rate_at_k"] == 0.0
    assert out["n_queries_with_hits"] == 0


@pytest.mark.asyncio
async def test_hallucination_rate_mcp_tool(tmp_path, monkeypatch):
    """Raggiungibilita' di produzione (chiude il caller-verification FAIL del
    critic 1dd646b1): la metrica e' esposta come MCP tool
    hippo_hallucination_rate, non e' piu' dead code."""
    from engram import mcp_server
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "0")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="the deploy region is eu-west-1", topic="t",
                  status="verified", confidence=0.95, source_episodes=["e"]),
             embed="sync")
    agent = MagicMock()
    agent.semantic = sm
    monkeypatch.setattr(mcp_server, "_ag", lambda: agent)

    res = await mcp_server.call_tool(
        "hippo_hallucination_rate", {"queries": ["deploy region"], "k": 5})
    out = json.loads(res[0].text)
    assert "hallucination_rate_at_k" in out, out
    assert out["k"] == 5 and out["n_queries_with_hits"] == 1, out


def test_hallucination_rate_blackout_is_not_reported_as_perfect(tmp_path, monkeypatch):
    """Audit 3-round R3 (fix-order-meta #0): un recall BLACKOUT — query reali ma
    ZERO hit (qui: corpus vuoto) — NON deve riportare 0.0 (perfetto). La metrica
    anti-confab mentirebbe esattamente quando il recall e' rotto. Deve segnalare
    degraded=True + hallucination_rate_at_k=None + coverage=0.0."""
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "0")
    sm = SemanticMemory(db_path=tmp_path / "s.db")  # corpus VUOTO -> recall=[]
    out = hallucination_rate_at_k(sm, ["any real query"], k=5)
    assert out["n_queries"] == 1 and out["n_queries_with_hits"] == 0, out
    assert out["hallucination_rate_at_k"] is None, out
    assert out["degraded"] is True, out
    assert out["coverage"] == 0.0, out


def test_hallucination_rate_empty_queries_is_not_degraded(tmp_path):
    """Distinzione: ZERO query (niente da misurare) != blackout (query senza hit).
    Nessuna query -> degraded resta False (non e' un recall rotto)."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    out = hallucination_rate_at_k(sm, [], k=5)
    assert out["degraded"] is False, out
