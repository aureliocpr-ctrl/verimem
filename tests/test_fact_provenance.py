"""Cycle #109 — Fact provenance schema v3.

Aurelio sfida 2026-05-16: la memoria con embedding-only similarity senza
provenance checks amplifica hallucinazione (MemoryGraft 2512.16962
documenta 47.9% poisoning rate persistent). Soluzione (ProvSEEK pattern
2508.21323): ogni fact deve avere campi provenance verificabili.

Schema v2 (questo branch, da main v1):
- verified_by: TEXT  (JSON list di tool_call refs; NULL = no verification)
- status: TEXT NOT NULL DEFAULT 'model_claim'
   ('verified' | 'model_claim' | 'provisional' | 'legacy_unverified')
- source_signature: TEXT (hash of source content; NULL = no signature)

Legacy facts (pre-cycle-109) sono marcati 'legacy_unverified' dalla
migration così rimangono distinguibili da fact post-fix.

NB: Aspetto integrazione con PR #43 (cycle 78 supersession layer):
quando #43 mergia, schema diventerà v3 (questo) + supersession (#43)
in un cycle110 di reconciliation.
"""
from __future__ import annotations

import json

import pytest

from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def sm(tmp_path):
    return SemanticMemory(db_path=tmp_path / "sm.db")


class TestFactDataclassV3:
    """Fact dataclass deve esporre i 3 campi provenance."""

    def test_fact_has_verified_by_field_default_empty_list(self):
        f = Fact(proposition="x")
        assert hasattr(f, "verified_by"), "Fact missing verified_by"
        assert f.verified_by == []

    def test_fact_has_status_field_default_model_claim(self):
        f = Fact(proposition="x")
        assert hasattr(f, "status"), "Fact missing status"
        assert f.status == "model_claim"

    def test_fact_has_source_signature_field_default_none(self):
        f = Fact(proposition="x")
        assert hasattr(f, "source_signature"), "Fact missing source_signature"
        assert f.source_signature is None

    def test_fact_verified_by_accepts_tool_call_refs(self):
        f = Fact(
            proposition="NEXUS has 17280 tests",
            verified_by=["bash:pytest_collect:exit0", "file:tests/:1708"],
            status="verified",
            source_signature="sha256:abc123",
        )
        assert f.verified_by == [
            "bash:pytest_collect:exit0", "file:tests/:1708",
        ]
        assert f.status == "verified"
        assert f.source_signature == "sha256:abc123"


class TestSchemaMigrationV1ToV2:
    """Migration ladder v1→v2 aggiunge le 3 colonne idempotente."""

    def test_fresh_db_has_provenance_columns(self, sm):
        with sm._connect() as conn:
            cols = {
                row[1] for row in conn.execute("PRAGMA table_info(facts)")
            }
        assert "verified_by" in cols
        assert "status" in cols
        assert "source_signature" in cols

    def test_schema_version_is_3_after_init(self, sm):
        """Post-rebase on main: cycle #78 (v2 supersession), cycle #109
        (v3 provenance), cycle 157 (v4 partial UNIQUE INDEX). The target
        version is read dynamically from the module so this test
        auto-adapts as new migrations land (cycle 160 v5 pattern card
        schema queued behind PR #103).
        """
        from verimem.semantic import _SEMANTIC_TARGET_VERSION
        with sm._connect() as conn:
            row = conn.execute(
                "SELECT version FROM _schema_version WHERE db_id = 'semantic'"
            ).fetchone()
        assert row is not None
        assert int(row[0]) == _SEMANTIC_TARGET_VERSION

    def test_migration_is_idempotent(self, sm):
        # Re-init same DB path — should not raise
        from verimem.semantic import _SEMANTIC_TARGET_VERSION
        sm2 = SemanticMemory(db_path=sm.db_path)
        with sm2._connect() as conn:
            row = conn.execute(
                "SELECT version FROM _schema_version WHERE db_id = 'semantic'"
            ).fetchone()
        assert int(row[0]) == _SEMANTIC_TARGET_VERSION


class TestStorePersistsProvenance:
    """SemanticMemory.store deve persistere e re-leggere campi provenance."""

    def test_store_default_fact_gets_model_claim_status(self, sm):
        sm.store(Fact(id="a", proposition="claim", topic="t", confidence=0.9))
        got = sm.get("a")
        assert got is not None
        assert got.status == "model_claim"
        assert got.verified_by == []
        assert got.source_signature is None

    def test_store_verified_fact_round_trip(self, sm):
        # Cycle #111 v2 (2026-05-17): the hard-gate demands I/O verify
        # for status='verified'. The cycle-109 tool-call refs below are
        # NOT verifiable in this test's tmp_path SemanticMemory (no
        # repo_root configured), so the fact is correctly demoted to
        # 'model_claim'. verified_by payload is preserved verbatim —
        # only the trust label changes. See test_verified_by_validation
        # for the verified-tier path using a real git repo fixture.
        sm.store(Fact(
            id="b", proposition="NEXUS has 17280 tests",
            topic="project/nexus/test-count", confidence=0.95,
            verified_by=["bash:pytest_collect", "file:tests/:count=1708"],
            status="verified",
            source_signature="sha256:deadbeef",
        ))
        got = sm.get("b")
        assert got.status == "model_claim"
        assert got.verified_by == [
            "bash:pytest_collect", "file:tests/:count=1708",
        ]
        assert got.source_signature == "sha256:deadbeef"

    def test_provisional_status_persisted(self, sm):
        sm.store(Fact(
            id="c", proposition="research finding from arxiv X",
            topic="research/x", confidence=0.85,
            verified_by=["url:arxiv.org/abs/2310.11511:sec_3.1"],
            status="provisional",
        ))
        assert sm.get("c").status == "provisional"


class TestStatusValidation:
    """Status invalido viene rifiutato per evitare typo."""

    def test_invalid_status_raises_value_error(self, sm):
        with pytest.raises(ValueError, match="status"):
            sm.store(Fact(
                id="x", proposition="p", status="totally_bogus_value",
            ))

    def test_valid_statuses_accepted(self, sm):
        for status in (
            "verified", "model_claim", "provisional", "legacy_unverified",
        ):
            sm.store(Fact(
                id=f"v_{status}", proposition="p", status=status,
            ))
        # All 4 stored
        rows = [sm.get(f"v_{s}") for s in (
            "verified", "model_claim", "provisional", "legacy_unverified",
        )]
        assert all(r is not None for r in rows)


class TestVerifiedByJsonSerialization:
    """verified_by è list[str] in memory, JSON in SQL — round trip preserved."""

    def test_empty_list_round_trip(self, sm):
        sm.store(Fact(id="e", proposition="p", verified_by=[]))
        assert sm.get("e").verified_by == []

    def test_multi_entry_list_round_trip(self, sm):
        sm.store(Fact(
            id="m", proposition="p",
            verified_by=["bash:cmd1", "file:p:42", "pytest:test_x"],
        ))
        assert sm.get("m").verified_by == [
            "bash:cmd1", "file:p:42", "pytest:test_x",
        ]


class TestRecallReturnsProvenance:
    """recall() deve restituire i campi provenance, non solo proposition."""

    def test_recall_returns_status(self, sm):
        # Cycle #111 v2: 'bash:cmd' is not I/O-verifiable so the
        # store-time gate demotes to 'model_claim'. The test still
        # asserts recall() returns the (demoted) status + the original
        # verified_by payload — i.e. provenance fields ARE plumbed
        # through recall(), regardless of trust label.
        sm.store(Fact(
            id="r", proposition="verified claim about X",
            topic="t", verified_by=["bash:cmd"], status="verified",
        ))
        hits = sm.recall("verified claim X", k=1)
        assert len(hits) == 1
        fact, sim = hits[0]
        assert fact.status == "model_claim"
        assert fact.verified_by == ["bash:cmd"]


class TestLegacyFactsMarkedLegacyUnverified:
    """Migrazione di un DB con dati pre-v2 deve marcare gli esistenti
    come 'legacy_unverified' (non 'model_claim') per distinguerli da
    fact creati post-fix con status implicito."""

    def test_legacy_rows_get_legacy_unverified_status(self, tmp_path):
        # Simula DB v1: crea fact direttamente con schema v1 (no provenance)
        import sqlite3
        db_path = tmp_path / "legacy.db"
        # Crea schema v1 manuale
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE facts (
                    id TEXT PRIMARY KEY,
                    proposition TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source_episodes TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    embedding BLOB NOT NULL
                )
            """)
            # Mark schema v1
            conn.execute("""
                CREATE TABLE _schema_version (
                    db_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    upgraded_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute(
                "INSERT INTO _schema_version (db_id, version) VALUES (?, 1)",
                ("semantic",),
            )
            # Insert one v1 fact with embedding placeholder
            import numpy as np

            from verimem import embedding as emb_mod
            fake_emb = emb_mod.encode("legacy claim")
            conn.execute("""
                INSERT INTO facts
                (id, proposition, topic, confidence, source_episodes,
                 created_at, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "legacy_id", "legacy claim", "legacy/topic", 0.9,
                "", 1700000000.0, emb_mod.serialize(fake_emb),
            ))

        # Now open with new SemanticMemory — migration should run
        sm = SemanticMemory(db_path=db_path)
        got = sm.get("legacy_id")
        assert got is not None
        assert got.status == "legacy_unverified"
        assert got.verified_by == []
