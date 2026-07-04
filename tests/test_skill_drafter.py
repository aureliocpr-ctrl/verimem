"""Cycle 217 (2026-05-23) — skill_drafter tests.

RED marker: ``from engram.skill_drafter import draft_skill_from_community``
must fail on master.

Builds on cycle 213 (detect_emerging_skills) + cycle 214 (normalize_topic).
The drafter takes a community result + the corpus DB and produces a
TEXT DRAFT (deterministic, LLM-free) of a candidate skill body:

  - Title: ``emerging_skill_<topic_leaf>``
  - Header with empirical evidence (size, purity, cohesion, dominant_topic)
  - List of fact IDs + truncated propositions
  - Trigger keywords (frequency-ranked from propositions, stop-words filtered)
  - Status: DRAFT (auto-discovered, pending review)

This is the missing piece between cycle 213's algorithmic discovery and
the LLM-call body-writing step.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

# RED MARKER
from engram.skill_drafter import draft_skill_from_community

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT,
    topic TEXT,
    embedding BLOB,
    lineage_to TEXT,
    superseded_by TEXT,
    status TEXT DEFAULT 'model_claim',
    created_at REAL DEFAULT 0.0
);
"""


def _build_db(tmp_path: Path) -> Path:
    db = tmp_path / "semantic.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(_SCHEMA)
    rows = [
        ("p1", "Python is a high-level language with dynamic typing.",
         "lang/python"),
        ("p2", "Python lists are ordered mutable sequences.",
         "lang/python"),
        ("p3", "Python dicts use hash tables for O(1) lookup.",
         "lang/python"),
        ("p4", "Python supports list comprehensions for brevity.",
         "lang/python"),
        ("r1", "Rust uses ownership and borrow checking.",
         "lang/rust"),
    ]
    for fid, prop, topic in rows:
        conn.execute(
            "INSERT INTO facts (id, proposition, topic) VALUES (?,?,?)",
            (fid, prop, topic),
        )
    conn.commit()
    conn.close()
    return db


class TestDraftSkillFromCommunity:
    def test_returns_dict_with_required_keys(self, tmp_path: Path) -> None:
        db = _build_db(tmp_path)
        community = {
            "community_id": "c0",
            "size": 4,
            "fact_ids": ["p1", "p2", "p3", "p4"],
            "suggested_skill_name": "emerging_skill_python",
            "dominant_topic": "lang/python",
            "topic_purity": 1.0,
            "cohesion": 0.9,
            "emergence_score": 3.6,
        }
        out = draft_skill_from_community(db, community)
        for key in (
            "skill_name", "draft_text", "trigger_keywords",
            "fact_ids", "evidence",
        ):
            assert key in out

    def test_draft_text_contains_skill_name(self, tmp_path: Path) -> None:
        db = _build_db(tmp_path)
        community = {
            "community_id": "c0", "size": 4,
            "fact_ids": ["p1", "p2", "p3", "p4"],
            "suggested_skill_name": "emerging_skill_python",
            "dominant_topic": "lang/python",
            "topic_purity": 1.0, "cohesion": 0.9,
            "emergence_score": 3.6,
        }
        out = draft_skill_from_community(db, community)
        assert "emerging_skill_python" in out["draft_text"]

    def test_draft_text_contains_evidence_block(self, tmp_path: Path) -> None:
        """The draft must surface size, purity, cohesion, dominant_topic."""
        db = _build_db(tmp_path)
        community = {
            "community_id": "c0", "size": 4,
            "fact_ids": ["p1", "p2", "p3", "p4"],
            "suggested_skill_name": "emerging_skill_python",
            "dominant_topic": "lang/python",
            "topic_purity": 0.75, "cohesion": 0.88,
            "emergence_score": 2.64,
        }
        out = draft_skill_from_community(db, community)
        txt = out["draft_text"]
        assert "size=4" in txt or "size: 4" in txt or "size 4" in txt.lower()
        assert "0.75" in txt or "75%" in txt
        assert "0.88" in txt
        assert "lang/python" in txt

    def test_draft_text_lists_propositions(self, tmp_path: Path) -> None:
        db = _build_db(tmp_path)
        community = {
            "community_id": "c0", "size": 4,
            "fact_ids": ["p1", "p2", "p3", "p4"],
            "suggested_skill_name": "emerging_skill_python",
            "dominant_topic": "lang/python",
            "topic_purity": 1.0, "cohesion": 0.9,
            "emergence_score": 3.6,
        }
        out = draft_skill_from_community(db, community)
        txt = out["draft_text"]
        # at least one proposition must appear
        assert "Python is a high-level language" in txt or "Python lists" in txt

    def test_trigger_keywords_extracted(self, tmp_path: Path) -> None:
        """Trigger keywords list non-empty and contains 'python'."""
        db = _build_db(tmp_path)
        community = {
            "community_id": "c0", "size": 4,
            "fact_ids": ["p1", "p2", "p3", "p4"],
            "suggested_skill_name": "emerging_skill_python",
            "dominant_topic": "lang/python",
            "topic_purity": 1.0, "cohesion": 0.9,
            "emergence_score": 3.6,
        }
        out = draft_skill_from_community(db, community)
        kws = out["trigger_keywords"]
        assert isinstance(kws, list)
        assert len(kws) > 0
        assert "python" in [k.lower() for k in kws]

    def test_stopwords_filtered_from_keywords(self, tmp_path: Path) -> None:
        """Common stopwords like 'the', 'is', 'a' must NOT appear."""
        db = _build_db(tmp_path)
        community = {
            "community_id": "c0", "size": 4,
            "fact_ids": ["p1", "p2", "p3", "p4"],
            "suggested_skill_name": "emerging_skill_python",
            "dominant_topic": "lang/python",
            "topic_purity": 1.0, "cohesion": 0.9,
            "emergence_score": 3.6,
        }
        out = draft_skill_from_community(db, community)
        kws_lower = {k.lower() for k in out["trigger_keywords"]}
        for sw in ("the", "is", "a", "for", "and"):
            assert sw not in kws_lower

    def test_italian_stopwords_filtered(self, tmp_path: Path) -> None:
        """Cycle 220: Italian particles (non, con, del, della, ...)
        must NOT survive — HippoAgent's real corpus is Italian-heavy
        and cycle 217's first run surfaced 'non'/'con' as keywords."""
        db = tmp_path / "it.db"
        import sqlite3
        conn = sqlite3.connect(str(db))
        conn.executescript("""
            CREATE TABLE facts (
                id TEXT PRIMARY KEY, proposition TEXT, topic TEXT,
                embedding BLOB, lineage_to TEXT, superseded_by TEXT,
                status TEXT DEFAULT 'model_claim',
                created_at REAL DEFAULT 0.0
            );
        """)
        # 4 Italian propositions with common particles repeated.
        for i, p in enumerate([
            "Il sistema usa una memoria del tipo persistente con cache.",
            "Una memoria del tipo persistente con cache fa il lavoro.",
            "Per il sistema della memoria con il cache non basta.",
            "Della memoria nel sistema con cache una analisi tipo bench.",
        ]):
            conn.execute(
                "INSERT INTO facts (id, proposition, topic) VALUES (?,?,?)",
                (f"it{i}", p, "test/italian"),
            )
        conn.commit()
        conn.close()
        community = {
            "community_id": "it", "size": 4,
            "fact_ids": [f"it{i}" for i in range(4)],
            "suggested_skill_name": "emerging_skill_italian",
            "dominant_topic": "test/italian",
            "topic_purity": 1.0, "cohesion": 0.9,
            "emergence_score": 3.6,
        }
        out = draft_skill_from_community(db, community)
        kws_lower = {k.lower() for k in out["trigger_keywords"]}
        for sw in ("il", "la", "del", "della", "con", "non", "una",
                  "nel", "per", "che", "una"):
            assert sw not in kws_lower, f"IT stopword '{sw}' leaked"
        # Domain words SHOULD survive — 'memoria', 'sistema', 'cache'.
        assert "memoria" in kws_lower or "sistema" in kws_lower or \
            "cache" in kws_lower

    def test_status_marker_present(self, tmp_path: Path) -> None:
        """Draft must carry an unambiguous DRAFT/pending marker."""
        db = _build_db(tmp_path)
        community = {
            "community_id": "c0", "size": 4,
            "fact_ids": ["p1", "p2", "p3", "p4"],
            "suggested_skill_name": "emerging_skill_python",
            "dominant_topic": "lang/python",
            "topic_purity": 1.0, "cohesion": 0.9,
            "emergence_score": 3.6,
        }
        out = draft_skill_from_community(db, community)
        txt = out["draft_text"].lower()
        assert "draft" in txt or "pending" in txt

    def test_missing_facts_handled(self, tmp_path: Path) -> None:
        """Community references fact_ids not in DB → skip silently, no crash."""
        db = _build_db(tmp_path)
        community = {
            "community_id": "c0", "size": 2,
            "fact_ids": ["p1", "ghost1", "ghost2"],
            "suggested_skill_name": "emerging_skill_python",
            "dominant_topic": "lang/python",
            "topic_purity": 1.0, "cohesion": 0.9,
            "emergence_score": 1.8,
        }
        out = draft_skill_from_community(db, community)
        assert "draft_text" in out
        # Only p1 found → should still produce something
        assert len(out["fact_ids"]) >= 1

    def test_empty_community_returns_minimal_stub(self, tmp_path: Path) -> None:
        """Empty fact_ids → returns dict with empty draft text but no crash."""
        db = _build_db(tmp_path)
        community = {
            "community_id": "empty", "size": 0,
            "fact_ids": [],
            "suggested_skill_name": "",
            "dominant_topic": "",
            "topic_purity": 0.0, "cohesion": 0.0,
            "emergence_score": 0.0,
        }
        out = draft_skill_from_community(db, community)
        assert isinstance(out["draft_text"], str)
        assert out["trigger_keywords"] == []

    def test_missing_db_returns_stub(self, tmp_path: Path) -> None:
        """Defensive: DB doesn't exist → no crash."""
        community = {
            "community_id": "c0", "size": 1,
            "fact_ids": ["foo"],
            "suggested_skill_name": "x", "dominant_topic": "t",
            "topic_purity": 1.0, "cohesion": 0.5,
            "emergence_score": 0.5,
        }
        out = draft_skill_from_community(tmp_path / "nonexistent.db", community)
        assert "draft_text" in out
        assert out["fact_ids"] == []
