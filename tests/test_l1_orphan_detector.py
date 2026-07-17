"""Cycle 181 (2026-05-23) — L2 reconciler stub: detect_l1_orphan_candidates.

Read-only detector that returns fact_ids which are L1-orphan candidates:
  * status IN ('provisional', 'model_claim')
  * proposition contains an L1 SHIPPED-family keyword (SHIPPED, MERGED,
    WIRED, DEPLOYED)
  * verified_by has NO commit-tracking ref (commit:/pr:/file:/git:)
  * older than ``min_age_days`` (default 7)
  * NOT superseded

Closes gap §5 of ``docs/sota/L0-L3-anti-confab-layers.md`` (cycle 180).
The full L2 reconciler (write-mode flip to ``status='orphaned'``) is a
follow-up cycle; this commit ships ONLY the read-side detector so a
human or external tool can review candidates before the flip.

RED marker: import must fail on master.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

# RED MARKER
from verimem.l1_orphan_detector import detect_l1_orphan_candidates

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT,
    verified_by TEXT,
    superseded_by TEXT,
    status TEXT DEFAULT 'model_claim',
    created_at REAL,
    trigger_keywords TEXT,
    applicable_when TEXT
);
"""


@pytest.fixture
def tiny_db(tmp_path: Path) -> Path:
    """Seed semantic.db with rows covering all detector branches.

    NOW=1_000_000 (arbitrary). Ages chosen so the default 7-day cutoff
    selects only the intended rows.
    """
    db_path = tmp_path / "semantic.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    eight_days = 8 * 86400
    one_day = 86400
    now = 1_000_000.0
    rows = [
        # f-orphan-1: classic candidate (SHIPPED, no commit, 8d old)
        ("f-orphan-1", "Cycle 99 SHIPPED PR #999 commit abc123",
         '["bash:pytest_pass", "file:foo.py"]',  # has file: prefix
         None, "model_claim", now - eight_days),
        # f-orphan-2: clean candidate (SHIPPED, NO commit ref, 8d old)
        ("f-orphan-2", "Cycle 100 MERGED on main branch",
         '["bash:some_tool_call"]',  # no commit/pr/file/git
         None, "model_claim", now - eight_days),
        # f-orphan-3: provisional + WIRED + no ref + 8d
        ("f-orphan-3", "Hook WIRED into MCP server",
         '["pytest:test_x_passed"]',
         None, "provisional", now - eight_days),
        # f-recent: too young (1d), excluded
        ("f-recent", "Cycle 101 DEPLOYED to production",
         '[]', None, "model_claim", now - one_day),
        # f-verified: status=verified, excluded
        ("f-verified", "Cycle 102 SHIPPED with full audit",
         '[]', None, "verified", now - eight_days),
        # f-with-commit: has commit ref, excluded
        ("f-with-commit", "Cycle 103 MERGED in main",
         '["commit:abc123def456", "file:engram/x.py"]',
         None, "model_claim", now - eight_days),
        # f-superseded: superseded, excluded
        ("f-superseded", "Cycle 104 SHIPPED but obsolete",
         '[]', "f-orphan-1", "model_claim", now - eight_days),
        # f-no-keyword: no L1 keyword, excluded
        ("f-no-keyword", "Just a generic fact about the corpus",
         '[]', None, "model_claim", now - eight_days),
    ]
    conn.executemany(
        "INSERT INTO facts (id, proposition, verified_by, superseded_by, "
        "status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


class TestDetectL1OrphanCandidates:
    def test_returns_list_of_str(self, tiny_db: Path) -> None:
        out = detect_l1_orphan_candidates(
            tiny_db, min_age_days=7, max_n=50, now=1_000_000.0,
        )
        assert isinstance(out, list)
        assert all(isinstance(x, str) for x in out)

    def test_detects_shipped_without_commit_ref(self, tiny_db: Path) -> None:
        """f-orphan-2 has MERGED + only bash: ref (no commit/pr/file/git)."""
        out = detect_l1_orphan_candidates(
            tiny_db, min_age_days=7, max_n=50, now=1_000_000.0,
        )
        assert "f-orphan-2" in out, f"missing f-orphan-2: {out}"

    def test_detects_provisional_status(self, tiny_db: Path) -> None:
        """status='provisional' AND L1 keyword AND no commit ref → candidate."""
        out = detect_l1_orphan_candidates(
            tiny_db, min_age_days=7, max_n=50, now=1_000_000.0,
        )
        assert "f-orphan-3" in out

    def test_excludes_recent_facts(self, tiny_db: Path) -> None:
        """Age < min_age_days cutoff → excluded."""
        out = detect_l1_orphan_candidates(
            tiny_db, min_age_days=7, max_n=50, now=1_000_000.0,
        )
        assert "f-recent" not in out

    def test_excludes_verified_status(self, tiny_db: Path) -> None:
        """status='verified' → excluded (already trusted)."""
        out = detect_l1_orphan_candidates(
            tiny_db, min_age_days=7, max_n=50, now=1_000_000.0,
        )
        assert "f-verified" not in out

    def test_excludes_facts_with_commit_ref(self, tiny_db: Path) -> None:
        """verified_by containing commit:/pr:/file:/git: → excluded.

        f-orphan-1 has 'file:foo.py' in verified_by → excluded.
        f-with-commit has 'commit:abc' → excluded.
        """
        out = detect_l1_orphan_candidates(
            tiny_db, min_age_days=7, max_n=50, now=1_000_000.0,
        )
        assert "f-orphan-1" not in out, (
            f"f-orphan-1 leaked despite file: ref: {out}"
        )
        assert "f-with-commit" not in out

    def test_excludes_superseded_rows(self, tiny_db: Path) -> None:
        out = detect_l1_orphan_candidates(
            tiny_db, min_age_days=7, max_n=50, now=1_000_000.0,
        )
        assert "f-superseded" not in out

    def test_excludes_facts_without_l1_keyword(self, tiny_db: Path) -> None:
        out = detect_l1_orphan_candidates(
            tiny_db, min_age_days=7, max_n=50, now=1_000_000.0,
        )
        assert "f-no-keyword" not in out

    def test_respects_max_n_cap(self, tiny_db: Path) -> None:
        out = detect_l1_orphan_candidates(
            tiny_db, min_age_days=7, max_n=1, now=1_000_000.0,
        )
        assert len(out) <= 1

    def test_handles_missing_db_defensive(self, tmp_path: Path) -> None:
        """Missing DB path → empty list, no crash."""
        out = detect_l1_orphan_candidates(
            tmp_path / "nope.db", min_age_days=7, max_n=50,
        )
        assert out == []

    def test_uses_default_now_when_none(self, tiny_db: Path) -> None:
        """When ``now`` is None, uses ``time.time()`` (real clock).
        f-orphan-2 created at 1_000_000 will be ancient relative to real
        clock — so it SHOULD be selected."""
        out = detect_l1_orphan_candidates(
            tiny_db, min_age_days=7, max_n=50, now=None,
        )
        assert "f-orphan-2" in out
