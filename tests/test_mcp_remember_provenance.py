"""Cycle #109 S2 — MCP hippo_remember accepts provenance fields.

Pattern ProvSEEK 2508.21323: ogni claim LLM deve mappare a row_id
verificable. Estendiamo hippo_remember MCP tool per accettare
``verified_by``, ``status``, ``source_signature`` come parametri
opzionali. Default ``status='model_claim'`` per backward compat.
"""
from __future__ import annotations

import pytest

# We test the dispatch handler indirectly by importing the helper
# _build_fact and exercising semantic.SemanticMemory.store contract.
from engram.semantic import Fact, SemanticMemory


@pytest.fixture
def sm(tmp_path):
    return SemanticMemory(db_path=tmp_path / "sm.db")


class TestBuildFactSupportsProvenance:
    """The _build_fact helper must propagate provenance fields."""

    def test_build_fact_accepts_verified_by(self):
        from engram.mcp_server import _build_fact
        f = _build_fact(
            "test proposition", topic="t", confidence=0.9,
            verified_by=["bash:cmd", "file:x:1"],
        )
        assert f.verified_by == ["bash:cmd", "file:x:1"]

    def test_build_fact_accepts_status(self):
        from engram.mcp_server import _build_fact
        f = _build_fact(
            "test", topic="t", confidence=0.9,
            status="verified",
        )
        assert f.status == "verified"

    def test_build_fact_accepts_source_signature(self):
        from engram.mcp_server import _build_fact
        f = _build_fact(
            "test", topic="t", confidence=0.9,
            source_signature="sha256:abc",
        )
        assert f.source_signature == "sha256:abc"

    def test_build_fact_default_status_is_model_claim(self):
        from engram.mcp_server import _build_fact
        f = _build_fact("test", topic="t", confidence=0.9)
        assert f.status == "model_claim"
        assert f.verified_by == []
        assert f.source_signature is None


class TestRememberDispatchProvenance:
    """The dispatch path through SemanticMemory persists provenance."""

    def test_dispatch_persists_verified_status(self, sm):
        # Cycle #111 v2: 'bash:pytest_collect:exit0:17280' is a
        # historical tool-call trace, not I/O-verifiable, so the
        # status='verified' write is demoted to 'model_claim'. The
        # dispatch still persists the verified_by payload and the
        # source_signature; only the trust label is downgraded.
        from engram.mcp_server import _build_fact
        fact = _build_fact(
            "NEXUS has 17280 tests",
            topic="project/nexus/test-count",
            confidence=0.95,
            verified_by=["bash:pytest_collect:exit0:17280"],
            status="verified",
            source_signature="cycle109-2026-05-16",
        )
        sm.store(fact)
        got = sm.get(fact.id)
        assert got.status == "model_claim"
        assert got.verified_by == ["bash:pytest_collect:exit0:17280"]
        assert got.source_signature == "cycle109-2026-05-16"

    def test_dispatch_rejects_invalid_status(self, sm):
        from engram.mcp_server import _build_fact
        with pytest.raises(ValueError, match="status"):
            sm.store(_build_fact(
                "p", topic="t", status="totally_bogus",
            ))


class TestRememberAutoClassification:
    """Without explicit verified_by, fact gets default status=model_claim.

    This is the empirical-gate "soft" behavior: we don't BLOCK calls
    without verified_by, but we MARK them so retrieval can distinguish.
    """

    def test_no_verified_by_marks_model_claim(self, sm):
        from engram.mcp_server import _build_fact
        fact = _build_fact("opinion claim", topic="t", confidence=0.5)
        sm.store(fact)
        got = sm.get(fact.id)
        assert got.status == "model_claim"
        assert got.verified_by == []

    def test_verified_by_with_status_verified_combo(self, sm):
        # Cycle #111 v2: neither 'bash:date' nor 'sql:count=42' is
        # I/O-verifiable (no filesystem or git target). Hard-gate
        # demotes to 'model_claim'. Payload still round-trips.
        from engram.mcp_server import _build_fact
        fact = _build_fact(
            "real verified fact", topic="t", confidence=0.95,
            verified_by=["bash:date", "sql:count=42"],
            status="verified",
        )
        sm.store(fact)
        got = sm.get(fact.id)
        assert got.status == "model_claim"
        assert len(got.verified_by) == 2


class TestProvisionalForResearch:
    """Research findings should be marked 'provisional' (no row_id but
    has paper source URL)."""

    def test_provisional_with_url_provenance(self, sm):
        from engram.mcp_server import _build_fact
        fact = _build_fact(
            "Self-RAG outperforms ChatGPT on PopQA 55.8 vs 29.3",
            topic="research/self-rag-2023",
            confidence=0.85,
            verified_by=["url:arxiv.org/abs/2310.11511:tab2"],
            status="provisional",
        )
        sm.store(fact)
        got = sm.get(fact.id)
        assert got.status == "provisional"
        assert got.verified_by[0].startswith("url:arxiv")
