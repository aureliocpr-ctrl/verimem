"""Cycle 229 (2026-05-23) — emerging skill → persistent fact registration.

RED marker: ``from verimem.emerging_skill_register import register_emerging_drafts_as_facts``
must fail on master.

Closes the discovery → persistence loop. After cycle 213 detects and
cycle 217 drafts the skill, cycle 229 registers each draft as a
``emerging_skill/<name>`` fact in the live ``semantic.db`` with:

  - proposition = "{skill_name}\\n{evidence}\\n{draft_text_preview}"
  - topic = "emerging_skill/auto-discovered/<skill_name>"
  - status = "model_claim" (NOT promoted, so the cycle-184 anti-confab
    gate doesn't pick it up as a verified claim)
  - confidence calibrated to evidence (purity × cohesion)

Idempotent: if a fact with the same auto-generated id already exists,
it is updated (not duplicated) — content-hash id derived from skill
name + dominant_topic.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

# RED MARKER
from verimem.emerging_skill_register import (
    register_emerging_drafts_as_facts,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT,
    topic TEXT,
    embedding BLOB,
    lineage_to TEXT,
    superseded_by TEXT,
    status TEXT DEFAULT 'model_claim',
    confidence REAL DEFAULT 0.5,
    created_at REAL DEFAULT 0.0
);
"""


def _make_draft(name: str, *, cid: str = "c-0", purity: float = 0.6,
                cohesion: float = 0.8, size: int = 5) -> dict:
    return {
        "skill_name": name,
        "draft_text": (
            f"# {name} (DRAFT)\n\n## Evidence\n- size={size}\n\n"
            "Status: DRAFT (pending review)."
        ),
        "trigger_keywords": ["foo", "bar", "baz"],
        "fact_ids": ["f1", "f2", "f3"],
        "evidence": {
            "community_id": cid,
            "size": size,
            "dominant_topic": "lang/python",
            "topic_purity": purity,
            "cohesion": cohesion,
            "emergence_score": purity * cohesion * size,
        },
    }


def _build_db(tmp_path: Path) -> Path:
    db = tmp_path / "s.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()
    return db


class TestRegisterEmergingDrafts:
    def test_empty_list_writes_nothing(self, tmp_path: Path) -> None:
        db = _build_db(tmp_path)
        out = register_emerging_drafts_as_facts(db, [])
        assert out["n_inserted"] == 0
        assert out["n_updated"] == 0

    def test_writes_one_fact_per_draft(self, tmp_path: Path) -> None:
        db = _build_db(tmp_path)
        drafts = [
            _make_draft("emerging_skill_python"),
            _make_draft("emerging_skill_rust", cid="c-1"),
        ]
        out = register_emerging_drafts_as_facts(db, drafts)
        assert out["n_inserted"] == 2
        # Verify DB
        conn = sqlite3.connect(str(db))
        rows = conn.execute(
            "SELECT topic, status FROM facts ORDER BY topic",
        ).fetchall()
        conn.close()
        topics = [r[0] for r in rows]
        statuses = [r[1] for r in rows]
        assert all(t.startswith("emerging_skill/auto-discovered/") for t in topics)
        assert all(s == "model_claim" for s in statuses)

    def test_idempotent_second_call_updates_not_inserts(
        self, tmp_path: Path,
    ) -> None:
        """Re-running with the same drafts updates, doesn't duplicate."""
        db = _build_db(tmp_path)
        drafts = [_make_draft("emerging_skill_python")]
        first = register_emerging_drafts_as_facts(db, drafts)
        second = register_emerging_drafts_as_facts(db, drafts)
        assert first["n_inserted"] == 1
        assert first["n_updated"] == 0
        assert second["n_inserted"] == 0
        assert second["n_updated"] == 1
        # Total row count: exactly 1.
        conn = sqlite3.connect(str(db))
        n = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        conn.close()
        assert n == 1

    def test_confidence_reflects_purity_times_cohesion(
        self, tmp_path: Path,
    ) -> None:
        """High-evidence drafts get higher confidence."""
        db = _build_db(tmp_path)
        weak = _make_draft("weak_skill", purity=0.5, cohesion=0.3)
        strong = _make_draft("strong_skill", cid="c-1", purity=0.9, cohesion=0.95)
        register_emerging_drafts_as_facts(db, [weak, strong])
        conn = sqlite3.connect(str(db))
        rows = conn.execute(
            "SELECT topic, confidence FROM facts ORDER BY confidence",
        ).fetchall()
        conn.close()
        assert len(rows) == 2
        # Strong > weak.
        assert rows[1][1] > rows[0][1]
        # Both bounded in [0,1].
        for _, conf in rows:
            assert 0.0 <= conf <= 1.0

    def test_empty_skill_name_skipped(self, tmp_path: Path) -> None:
        db = _build_db(tmp_path)
        out = register_emerging_drafts_as_facts(
            db, [_make_draft("")],
        )
        assert out["n_inserted"] == 0
        assert out["n_skipped"] == 1

    def test_proposition_contains_evidence(self, tmp_path: Path) -> None:
        db = _build_db(tmp_path)
        register_emerging_drafts_as_facts(
            db, [_make_draft("emerging_skill_demo", purity=0.6,
                              cohesion=0.8, size=7)],
        )
        conn = sqlite3.connect(str(db))
        prop = conn.execute(
            "SELECT proposition FROM facts LIMIT 1",
        ).fetchone()[0]
        conn.close()
        assert "emerging_skill_demo" in prop
        # At least one piece of evidence surfaced (size=7).
        assert "7" in prop

    def test_missing_db_returns_zero(self, tmp_path: Path) -> None:
        out = register_emerging_drafts_as_facts(
            tmp_path / "missing.db",
            [_make_draft("x")],
        )
        assert out["n_inserted"] == 0

    def test_lineage_to_anchors_to_first_fact(
        self, tmp_path: Path,
    ) -> None:
        """Cycle 237: lineage_to of the emerging-skill fact must point
        at the FIRST member fact_id (so `clp chain show` walks back
        to the source cluster)."""
        db = tmp_path / "lineage.db"
        # Use the richer schema that includes lineage_to.
        import sqlite3 as _sql
        conn = _sql.connect(str(db))
        conn.executescript(
            "CREATE TABLE facts ("
            "id TEXT PRIMARY KEY, "
            "proposition TEXT, "
            "topic TEXT, "
            "embedding BLOB, "
            "lineage_to TEXT, "
            "superseded_by TEXT, "
            "status TEXT DEFAULT 'model_claim', "
            "confidence REAL DEFAULT 0.5, "
            "created_at REAL DEFAULT 0.0);",
        )
        conn.commit()
        conn.close()
        draft = _make_draft("emerging_skill_lineage_demo")
        # Override fact_ids order so the assertion is deterministic.
        draft["fact_ids"] = ["src_anchor", "src_b", "src_c"]
        out = register_emerging_drafts_as_facts(db, [draft])
        assert out["n_inserted"] == 1
        # The new fact must carry lineage_to = "src_anchor".
        conn = _sql.connect(str(db))
        row = conn.execute(
            "SELECT lineage_to FROM facts WHERE topic LIKE 'emerging_skill/%'",
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "src_anchor"

    def test_lineage_to_idempotent_update(
        self, tmp_path: Path,
    ) -> None:
        """Re-registering with the same source cluster keeps the
        lineage_to anchor stable (idempotent UPDATE)."""
        db = tmp_path / "lineage_idem.db"
        import sqlite3 as _sql
        conn = _sql.connect(str(db))
        conn.executescript(
            "CREATE TABLE facts ("
            "id TEXT PRIMARY KEY, "
            "proposition TEXT, "
            "topic TEXT, "
            "embedding BLOB, "
            "lineage_to TEXT, "
            "superseded_by TEXT, "
            "status TEXT DEFAULT 'model_claim', "
            "confidence REAL DEFAULT 0.5, "
            "created_at REAL DEFAULT 0.0);",
        )
        conn.commit()
        conn.close()
        draft = _make_draft("emerging_skill_idem")
        draft["fact_ids"] = ["stable_anchor", "f2"]
        first = register_emerging_drafts_as_facts(db, [draft])
        second = register_emerging_drafts_as_facts(db, [draft])
        assert first["n_inserted"] == 1
        assert second["n_updated"] == 1
        conn = _sql.connect(str(db))
        row = conn.execute(
            "SELECT lineage_to FROM facts WHERE topic LIKE 'emerging_skill/%'",
        ).fetchone()
        conn.close()
        assert row[0] == "stable_anchor"
