"""Cycle 160 (2026-05-19) — pattern card schema v5 tests.

Empirical motivation: cycle 160 bench on production store (1391 facts)
measured TPR@20 = 70% for semantic-only retrieval; the residual 30%
miss is the wording-mismatch class where the right fact exists but
embedding cosine fails to land it in the top-k. The pattern-card
schema extension adds explicit metadata that the host can index on:

  trigger_keywords  — short keywords beyond the proposition body
  applicable_when   — natural-language condition (when the fact
                      applies)
  worked_example    — short example carried with the fact
  lineage_to        — fact ids this fact supersedes / extends

All four are nullable / empty by default — pre-cycle-160 callers see
zero behaviour change. Master fact: bench retrieval id 9379c8141a3e
(2026-05-19 cycle 160 retrieval-quality fact).

These tests pin:
  R1 — fresh-DB schema includes the four new columns at v5
  R2 — Fact dataclass accepts the four new fields with safe defaults
  R3 — round-trip store/load preserves all four
  R4 — backward-compat: a Fact stored without the new fields loads
       with the documented defaults (empty list / None) — no crash
  R5 — migration v4→v5 on an existing DB adds the columns without
       touching old rows
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

# -----------------------------------------------------------------------
# R1: fresh DB has the new columns
# -----------------------------------------------------------------------


def test_fresh_db_has_pattern_card_columns(tmp_path: Path) -> None:
    from verimem.semantic import SemanticMemory

    sm = SemanticMemory(db_path=tmp_path / "semantic.db")
    with sm._connect() as conn:  # noqa: SLF001
        cols = {r[1] for r in conn.execute("PRAGMA table_info(facts)").fetchall()}
    for required in {
        "trigger_keywords",
        "applicable_when",
        "worked_example",
        "lineage_to",
    }:
        assert required in cols, f"v5 column missing: {required} (got {cols})"


# -----------------------------------------------------------------------
# R2 + R3: Fact dataclass accepts new fields + round-trip
# -----------------------------------------------------------------------


def test_fact_dataclass_accepts_pattern_card_fields() -> None:
    from verimem.semantic import Fact

    f = Fact(
        proposition="AM-GM pairing trick on (2p-1)!",
        topic="math/imo/2022-p5",
        trigger_keywords=["AM-GM", "pairing", "factorial bound"],
        applicable_when="bounding factorial vs prime power",
        worked_example="(2p-1)! = p · prod k(2p-k) ≤ p^(2p-1)",
        lineage_to=["abc123def456"],
    )
    assert f.trigger_keywords == ["AM-GM", "pairing", "factorial bound"]
    assert f.applicable_when == "bounding factorial vs prime power"
    assert "(2p-1)!" in f.worked_example
    assert f.lineage_to == ["abc123def456"]


def test_store_and_load_round_trips_pattern_card(tmp_path: Path) -> None:
    from verimem.semantic import Fact, SemanticMemory

    sm = SemanticMemory(db_path=tmp_path / "semantic.db")
    f = Fact(
        proposition="AM-GM pairing trick",
        topic="math/imo-2022-p5",
        trigger_keywords=["AM-GM", "factorial"],
        applicable_when="bounding factorial vs prime power",
        worked_example="(2p-1)! ≤ p^(2p-1)",
        lineage_to=["parent-fact-id"],
    )
    sm.store(f)

    got = sm.get(f.id)
    assert got is not None
    assert got.trigger_keywords == ["AM-GM", "factorial"]
    assert got.applicable_when == "bounding factorial vs prime power"
    assert got.worked_example == "(2p-1)! ≤ p^(2p-1)"
    assert got.lineage_to == ["parent-fact-id"]


# -----------------------------------------------------------------------
# R4: backward compat — Fact created without new fields
# -----------------------------------------------------------------------


def test_fact_default_pattern_card_fields_empty() -> None:
    from verimem.semantic import Fact

    f = Fact(proposition="legacy fact", topic="legacy")
    assert f.trigger_keywords == []
    assert f.applicable_when is None
    assert f.worked_example is None
    assert f.lineage_to == []


def test_legacy_fact_loads_with_default_pattern_card(tmp_path: Path) -> None:
    from verimem.semantic import Fact, SemanticMemory

    sm = SemanticMemory(db_path=tmp_path / "semantic.db")
    f = Fact(proposition="no pattern card", topic="x")
    sm.store(f)

    got = sm.get(f.id)
    assert got is not None
    assert got.trigger_keywords == []
    assert got.applicable_when is None
    assert got.worked_example is None
    assert got.lineage_to == []


# -----------------------------------------------------------------------
# R5: migration v4→v5 on existing DB adds columns
# -----------------------------------------------------------------------


def test_migration_v4_to_v5_adds_columns(tmp_path: Path) -> None:
    """Simulate a pre-v5 DB created at schema v4: missing the 4
    pattern-card columns. The migration must add them on first open.
    """
    db_path = tmp_path / "semantic.db"
    # Hand-craft a v4-shaped DB (no pattern card columns).
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE facts (
            id TEXT PRIMARY KEY,
            proposition TEXT NOT NULL,
            topic TEXT NOT NULL,
            confidence REAL NOT NULL,
            source_episodes TEXT NOT NULL,
            created_at REAL NOT NULL,
            embedding BLOB NOT NULL,
            superseded_by TEXT,
            superseded_at REAL,
            superseded_reason TEXT,
            verified_by TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'model_claim',
            source_signature TEXT
        );
        CREATE TABLE _schema_version (
            db_id TEXT PRIMARY KEY,
            version INTEGER NOT NULL,
            upgraded_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO _schema_version (db_id, version) VALUES ('semantic', 4);
    """)
    # Insert a single legacy row.
    import numpy as np

    fake_emb = np.zeros(384, dtype=np.float32).tobytes()
    conn.execute(
        "INSERT INTO facts (id, proposition, topic, confidence, source_episodes, "
        "created_at, embedding) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("legacy1", "old fact", "old", 0.5, "", 1700000000.0, fake_emb),
    )
    conn.commit()
    conn.close()

    # Re-open via SemanticMemory — the migration ladder should run v4→v5.
    from verimem.semantic import SemanticMemory

    sm = SemanticMemory(db_path=db_path)

    # Columns now present.
    with sm._connect() as conn:  # noqa: SLF001
        cols = {r[1] for r in conn.execute("PRAGMA table_info(facts)").fetchall()}
    assert "trigger_keywords" in cols
    assert "applicable_when" in cols
    assert "worked_example" in cols
    assert "lineage_to" in cols

    # Old row still loads with defaults.
    got = sm.get("legacy1")
    assert got is not None
    assert got.trigger_keywords == []
    assert got.applicable_when is None
    assert got.worked_example is None
    assert got.lineage_to == []
