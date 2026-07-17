"""Cycle 193 (2026-05-23) — temporal narrative reconstruction tests.

Acceptance §5.1 of docs/sota/temporal-evolution-narrative.md:
  * Synthetic 5-fact chain (root + antecedent + descendant +
    revision + same-topic-context) → all 5 roles labelled.
  * Empty / missing DB → [] defensive.

RED marker: ``from verimem.temporal_narrative import
reconstruct_narrative`` must fail on master.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

# RED MARKER
from verimem.temporal_narrative import reconstruct_narrative

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT,
    topic TEXT,
    lineage_to TEXT,
    superseded_by TEXT,
    status TEXT DEFAULT 'model_claim',
    created_at REAL
);
"""


@pytest.fixture
def chain_db(tmp_path: Path) -> Path:
    """Five facts on topic 'cycle/175':

      root_ant (ts=1000)  ← root's antecedent (root.lineage_to=root_ant)
      root     (ts=2000)
      root_rev (ts=2500)  ← supersedes root (root.superseded_by=root_rev)
      root_desc(ts=3000)  ← child (lineage_to=root)
      same_ctx (ts=2200)  ← same topic, not linked

    All 5 roles must surface for seed='root'.
    """
    db_path = tmp_path / "semantic.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    rows = [
        ("root_ant", "p", "cycle/175", None, None, "model_claim", 1000.0),
        ("root", "p", "cycle/175", "root_ant", "root_rev", "model_claim", 2000.0),
        ("same_ctx", "p", "cycle/175", None, None, "model_claim", 2200.0),
        ("root_rev", "p", "cycle/175", None, None, "model_claim", 2500.0),
        ("root_desc", "p", "cycle/175", "root", None, "model_claim", 3000.0),
    ]
    conn.executemany(
        "INSERT INTO facts (id, proposition, topic, lineage_to, "
        "superseded_by, status, created_at) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


class TestReconstructNarrative:
    def test_missing_db_returns_empty(self, tmp_path: Path) -> None:
        out = reconstruct_narrative(
            tmp_path / "nope.db", seed_fact_id="anything",
        )
        assert out == []

    def test_unknown_seed_returns_empty(self, chain_db: Path) -> None:
        out = reconstruct_narrative(
            chain_db, seed_fact_id="ghost-id",
        )
        assert out == []

    def test_root_role_present(self, chain_db: Path) -> None:
        out = reconstruct_narrative(
            chain_db, seed_fact_id="root", now=4000.0,
        )
        roles = {(e["fact_id"], e["role"]) for e in out}
        assert ("root", "root") in roles

    def test_antecedent_role_via_lineage(self, chain_db: Path) -> None:
        out = reconstruct_narrative(
            chain_db, seed_fact_id="root", now=4000.0,
        )
        roles = {(e["fact_id"], e["role"]) for e in out}
        assert ("root_ant", "antecedent") in roles

    def test_descendant_role_via_reverse_lineage(
        self, chain_db: Path,
    ) -> None:
        out = reconstruct_narrative(
            chain_db, seed_fact_id="root", now=4000.0,
        )
        roles = {(e["fact_id"], e["role"]) for e in out}
        assert ("root_desc", "descendant") in roles

    def test_revision_role_via_superseded_by(self, chain_db: Path) -> None:
        out = reconstruct_narrative(
            chain_db, seed_fact_id="root", now=4000.0,
        )
        roles = {(e["fact_id"], e["role"]) for e in out}
        assert ("root_rev", "revision") in roles

    def test_context_role_via_same_topic(self, chain_db: Path) -> None:
        out = reconstruct_narrative(
            chain_db, seed_fact_id="root", now=4000.0,
            window_days=1.0,  # 1d window
        )
        roles = {(e["fact_id"], e["role"]) for e in out}
        # same_ctx ts=2200, root ts=2000 → 200s diff ~= 0.002 days,
        # well inside window_days=1.
        assert ("same_ctx", "context") in roles

    def test_chronological_order(self, chain_db: Path) -> None:
        out = reconstruct_narrative(
            chain_db, seed_fact_id="root", now=4000.0,
        )
        timestamps = [e["ts"] for e in out]
        assert timestamps == sorted(timestamps)

    def test_age_days_computed_from_now(self, chain_db: Path) -> None:
        out = reconstruct_narrative(
            chain_db, seed_fact_id="root", now=4000.0 + 86400.0,
        )
        root = next(e for e in out if e["fact_id"] == "root")
        # root.ts = 2000.0, now = 88400 → age = 86400 sec = 1 day
        assert abs(root["age_days"] - (1.0 + 2000.0 / 86400.0)) < 0.01

    def test_max_entries_caps_result(self, chain_db: Path) -> None:
        out = reconstruct_narrative(
            chain_db, seed_fact_id="root", now=4000.0, max_entries=2,
        )
        assert len(out) <= 2

    def test_all_five_roles_appear_in_full_chain(
        self, chain_db: Path,
    ) -> None:
        """Acceptance §5.1: synthetic chain must surface all 5 roles."""
        out = reconstruct_narrative(
            chain_db, seed_fact_id="root", now=4000.0,
        )
        roles = {e["role"] for e in out}
        for r in ("root", "antecedent", "descendant", "revision", "context"):
            assert r in roles, f"missing role {r!r}: {roles}"

    def test_edge_to_seed_field_present(self, chain_db: Path) -> None:
        out = reconstruct_narrative(
            chain_db, seed_fact_id="root", now=4000.0,
        )
        for e in out:
            assert "edge_to_seed" in e
