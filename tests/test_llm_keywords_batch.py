"""Cycle 168.1 (2026-05-22) — batch caller that walks semantic.db facts
with missing / shallow ``trigger_keywords`` and persists LLM-augmented
output via SQLite UPDATE.

Composes over the cycle-168 pure function
``engram.llm_keywords_augment.extract_keywords``. Pure dispatch +
persistence wrapper; the LLM call itself is still injection-only
(subscription-only per CLAUDE.md O4).

Empirical scope reference (corpus audit fact b0ac1291108f):
  * 1665 facts total in ~/.engram/semantic/semantic.db
  * 1388 (83.4%) have trigger_keywords populated (cycle-162 rule-based,
    shallow output)
  * 277 (16.6%) have trigger_keywords NULL -- primary target

Contract
--------
``augment_keywords_batch(db_path, *, llm_callable, limit, min_length,
n_min, n_max) -> dict``

Returns a summary dict:
  * ``selected``: rows that matched the WHERE clause
  * ``augmented``: rows where extract_keywords returned >= 1 keyword AND
    we successfully UPDATE'd the row
  * ``skipped_empty_llm``: rows where extract_keywords returned []
    (LLM failure / invalid JSON / empty text) -- NOT updated
  * ``errors``: rows where the SQLite UPDATE itself raised

Defensive: any single-row failure NEVER aborts the loop. Errors are
counted but the next row keeps going.

RED marker: ``from engram.llm_keywords_batch import
augment_keywords_batch`` must fail on master.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# RED MARKER
from engram.llm_keywords_batch import augment_keywords_batch

# ---------------------------------------------------------------------------
# Fixture: a tiny semantic.db mimicking real-corpus shape (cycle 175 audit)
# ---------------------------------------------------------------------------


_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT,
    trigger_keywords TEXT,
    superseded_by TEXT,
    status TEXT DEFAULT 'model_claim',
    created_at REAL
);
"""


@pytest.fixture
def tiny_db(tmp_path: Path) -> Path:
    """Seed 5 facts mimicking the real-corpus distribution.

    Shape:
      * 2 with trigger_keywords NULL (target)
      * 1 with shallow rule-based keywords (target if min_length>14)
      * 1 with rich keywords (NOT target -- already good)
      * 1 superseded (NOT target -- excluded by WHERE)
    """
    db_path = tmp_path / "semantic.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    rows = [
        ("f-null-1", "User email is user@example.com", None, None, 1.0),
        ("f-null-2", "API endpoint is https://api/v1", None, None, 2.0),
        ("f-short", "stress test fact", "test,stress", None, 3.0),
        ("f-rich", "rich semantic fact",
         "concept-tag,another-tag,third-tag,fourth-tag,fifth-tag", None, 4.0),
        ("f-superseded", "obsolete fact", None, "f-rich", 5.0),
    ]
    conn.executemany(
        "INSERT INTO facts (id, proposition, trigger_keywords, "
        "superseded_by, created_at) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


def _make_llm(keywords: list[str]) -> MagicMock:
    """Mock llm_callable that always returns the same keywords."""
    mock = MagicMock()
    mock.return_value = json.dumps({"keywords": keywords})
    return mock


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


class TestAugmentKeywordsBatch:
    def test_returns_summary_dict_with_required_keys(
        self, tiny_db: Path,
    ) -> None:
        llm = _make_llm(["a", "b", "c", "d", "e"])
        out = augment_keywords_batch(
            tiny_db, llm_callable=llm, limit=5, min_length=20,
        )
        assert isinstance(out, dict)
        for k in ("selected", "augmented", "skipped_empty_llm", "errors"):
            assert k in out, f"missing key {k!r} in summary: {out}"

    def test_selects_null_trigger_keywords(self, tiny_db: Path) -> None:
        """Rows with NULL trigger_keywords MUST be selected
        (excluding superseded)."""
        llm = _make_llm(["alpha", "beta", "gamma", "delta", "epsilon"])
        out = augment_keywords_batch(
            tiny_db, llm_callable=llm, limit=10, min_length=20,
        )
        # f-null-1, f-null-2 (NULL) plus f-short (len=11 < 20) = 3 selected.
        # f-rich has len 56 > 20 → skipped. f-superseded excluded.
        assert out["selected"] == 3, (
            f"expected 3 selected (2 NULL + 1 short), got {out['selected']}: "
            f"{out}"
        )

    def test_persists_augmented_keywords_via_update(
        self, tiny_db: Path,
    ) -> None:
        """Successful LLM call must UPDATE the row's trigger_keywords."""
        llm = _make_llm(["alpha-tag", "beta-tag", "gamma-tag",
                          "delta-tag", "epsilon-tag"])
        augment_keywords_batch(
            tiny_db, llm_callable=llm, limit=10, min_length=20,
        )
        conn = sqlite3.connect(str(tiny_db))
        row = conn.execute(
            "SELECT trigger_keywords FROM facts WHERE id = ?",
            ("f-null-1",),
        ).fetchone()
        conn.close()
        assert row is not None
        # Persisted as comma-joined string (cycle-162 convention).
        persisted = row[0]
        assert persisted is not None and persisted != ""
        for tag in ("alpha-tag", "beta-tag", "gamma-tag"):
            assert tag in persisted, (
                f"expected {tag!r} in persisted {persisted!r}"
            )

    def test_respects_limit_cap(self, tiny_db: Path) -> None:
        """``limit`` bounds the rows processed."""
        llm = _make_llm(["a", "b", "c", "d", "e"])
        out = augment_keywords_batch(
            tiny_db, llm_callable=llm, limit=1, min_length=20,
        )
        assert out["selected"] <= 1

    def test_excludes_superseded_rows(self, tiny_db: Path) -> None:
        """Superseded rows MUST NOT be in the batch."""
        llm = _make_llm(["x", "y", "z", "w", "v"])
        augment_keywords_batch(
            tiny_db, llm_callable=llm, limit=10, min_length=20,
        )
        conn = sqlite3.connect(str(tiny_db))
        row = conn.execute(
            "SELECT trigger_keywords FROM facts WHERE id = ?",
            ("f-superseded",),
        ).fetchone()
        conn.close()
        # f-superseded was NULL before; if it was processed it would have
        # been updated with our mock keywords.
        assert row is not None
        assert row[0] is None, (
            f"superseded row was unexpectedly updated: {row[0]!r}"
        )

    def test_excludes_already_rich_rows(self, tiny_db: Path) -> None:
        """Rows whose trigger_keywords length > min_length MUST be
        skipped (resume semantics)."""
        # f-rich has trigger_keywords of length ~56 → above min_length=20.
        llm = _make_llm(["should", "not", "be", "used", "here"])
        augment_keywords_batch(
            tiny_db, llm_callable=llm, limit=10, min_length=20,
        )
        conn = sqlite3.connect(str(tiny_db))
        row = conn.execute(
            "SELECT trigger_keywords FROM facts WHERE id = ?",
            ("f-rich",),
        ).fetchone()
        conn.close()
        assert row is not None
        # Original keywords preserved.
        assert "concept-tag" in row[0]
        assert "should" not in row[0]

    def test_skipped_empty_llm_counted_separately(
        self, tiny_db: Path,
    ) -> None:
        """When extract_keywords returns [] (LLM failure / empty),
        the row is NOT updated and counted in skipped_empty_llm."""
        bad_llm = MagicMock()
        bad_llm.side_effect = RuntimeError("network down")
        out = augment_keywords_batch(
            tiny_db, llm_callable=bad_llm, limit=10, min_length=20,
        )
        # All selected rows return [] → all skipped.
        assert out["augmented"] == 0
        assert out["skipped_empty_llm"] == out["selected"]

    def test_one_bad_row_does_not_abort_loop(
        self, tiny_db: Path,
    ) -> None:
        """If extract_keywords raises on row N, the loop MUST continue
        to row N+1. Counted, not crashed."""
        call_count = [0]

        def flaky(prompt: str) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("transient network blip")
            return json.dumps({"keywords": ["ok", "still", "running",
                                              "after", "fail"]})

        out = augment_keywords_batch(
            tiny_db, llm_callable=flaky, limit=10, min_length=20,
        )
        # First row failed, but the others succeeded.
        assert out["augmented"] >= 1, (
            f"loop aborted after first error: {out}"
        )

    def test_handles_missing_db_defensive(self, tmp_path: Path) -> None:
        """Missing DB → ``selected=0``, NEVER raises."""
        llm = MagicMock()
        out = augment_keywords_batch(
            tmp_path / "nope.db",
            llm_callable=llm, limit=10, min_length=20,
        )
        assert out == {
            "selected": 0, "augmented": 0,
            "skipped_empty_llm": 0, "errors": 0,
        }
        assert llm.call_count == 0
