"""BM25 lexical ranking over fact propositions via SQLite FTS5 (competitor-gap
step 3a, 2026-06-14).

Closes Zep's first-class-BM25 gap and fixes EXACT-TOKEN recall: a commit SHA, a
file path, an error string or an API name is a single rare token the bi-encoder
smears into a dense neighborhood, so pure-cosine ranks it poorly — BM25 ranks it
first. This is the third RRF signal (alongside dense-cosine and entity-PPR); the
wiring into recall's fusion is step 3b.

Leaf module, no SemanticMemory dependency. Maintains a standalone FTS5 index
(``facts_fts(fact_id UNINDEXED, proposition)``) synced to the curated facts by row
count — a cheap heuristic sufficient for this building block; step 3b replaces it
with triggers / incremental sync. Fail-soft: returns [] on any error.
"""
from __future__ import annotations

import re
import sqlite3

#: curated view = same default filter recall uses (no superseded / hidden rows).
_CURATED = "superseded_by IS NULL AND status NOT IN ('orphaned', 'quarantined')"


def _to_fts_query(query: str) -> str:
    """Turn free text into a safe FTS5 MATCH expr: OR of double-quoted tokens
    (quoting each token neutralizes FTS5 operators, so arbitrary input never
    raises a syntax error; OR maximizes recall, the rank does the ordering)."""
    toks = [t for t in re.findall(r"\w+", query.lower()) if len(t) >= 2]
    return " OR ".join(f'"{t}"' for t in toks)


def _ensure_fts(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts "
        "USING fts5(fact_id UNINDEXED, proposition)"
    )
    # Incremental sync via triggers (no O(N) rebuild): the FTS index mirrors EVERY
    # facts row 1:1; the curated/status filter is applied at QUERY time (status can
    # change after insert, so it can't live in the trigger). O(1) per write.
    conn.execute(
        "CREATE TRIGGER IF NOT EXISTS facts_fts_ai AFTER INSERT ON facts BEGIN "
        "INSERT INTO facts_fts(fact_id, proposition) "
        "VALUES (new.id, new.proposition); END"
    )
    conn.execute(
        "CREATE TRIGGER IF NOT EXISTS facts_fts_ad AFTER DELETE ON facts BEGIN "
        "DELETE FROM facts_fts WHERE fact_id = old.id; END"
    )
    conn.execute(
        "CREATE TRIGGER IF NOT EXISTS facts_fts_au AFTER UPDATE ON facts BEGIN "
        "DELETE FROM facts_fts WHERE fact_id = old.id; "
        "INSERT INTO facts_fts(fact_id, proposition) "
        "VALUES (new.id, new.proposition); END"
    )
    # One-time backfill for rows that predate the FTS table/triggers.
    n_fts = conn.execute("SELECT count(*) FROM facts_fts").fetchone()[0]
    if n_fts == 0:
        n_all = conn.execute("SELECT count(*) FROM facts").fetchone()[0]
        if n_all > 0:
            conn.execute(
                "INSERT INTO facts_fts(fact_id, proposition) "
                "SELECT id, proposition FROM facts"
            )
    conn.commit()


def bm25_fact_ids(query: str | None, db_path, *, limit: int = 20) -> list[str]:
    """Return fact ids ranked by BM25 over their proposition, best first.

    Fail-soft: ``[]`` on empty query / no tokens / any sqlite or FTS error.
    """
    if not query:
        return []
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        try:
            _ensure_fts(conn)
            expr = _to_fts_query(query)
            if not expr:
                return []
            rows = conn.execute(
                "SELECT facts_fts.fact_id FROM facts_fts "
                "JOIN facts ON facts.id = facts_fts.fact_id "
                f"WHERE facts_fts MATCH ? AND facts.{_CURATED} "
                "ORDER BY bm25(facts_fts) LIMIT ?",
                (expr, int(max(1, limit))),
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 — fail-soft; the fusion degrades without BM25
        return []


__all__ = ["bm25_fact_ids"]
