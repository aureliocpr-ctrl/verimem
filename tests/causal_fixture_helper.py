"""Shared fixture helper: wire fact<->fact causal links in the REAL format.

Scan #316 realignment (2026-06-10). The legacy fixtures created a
`causal_edges(src,dst)` table ON semantic.db — a schema/location that
exists NOWHERE in production (verified live: semantic.db has no causal
table at all; episodes.db holds the 442 real edges keyed by
src_episode_id/dst_episode_id). Those fixtures only worked because the
pre-fix community detector read exactly that broken shape.

Real wiring reproduced here: each fact gets a synthetic source episode
`ep_<fact_id>` in facts.source_episodes (comma-separated TEXT, the way
semantic.py stores it) and the episode<->episode edges live in the
SIBLING episodes.db — the path `community_detector._sibling_episodes_db`
derives, so the semantic db MUST live under a `semantic/` directory.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def add_causal_clique_edges(
    semantic_db: Path, edges: list[tuple[str, str]],
) -> None:
    ensure_source_episodes_column(Path(semantic_db))
    conn = sqlite3.connect(str(semantic_db))
    try:
        for fid in {x for pair in edges for x in pair}:
            conn.execute(
                "UPDATE facts SET source_episodes=? WHERE id=?",
                (f"ep_{fid}", fid),
            )
        conn.commit()
    finally:
        conn.close()
    ep_db = Path(semantic_db).parent.parent / "episodes" / "episodes.db"
    ep_db.parent.mkdir(parents=True, exist_ok=True)
    ep_conn = sqlite3.connect(str(ep_db))
    try:
        ep_conn.execute(
            "CREATE TABLE IF NOT EXISTS causal_edges ("
            "src_episode_id TEXT NOT NULL, dst_episode_id TEXT NOT NULL, "
            "via_skill_id TEXT NOT NULL, weight REAL NOT NULL, "
            "PRIMARY KEY (src_episode_id, dst_episode_id, via_skill_id))"
        )
        ep_conn.executemany(
            "INSERT OR IGNORE INTO causal_edges VALUES (?,?,?,?)",
            [(f"ep_{s}", f"ep_{d}", "s1", 1.0) for s, d in edges],
        )
        ep_conn.commit()
    finally:
        ep_conn.close()


def ensure_source_episodes_column(semantic_db: Path) -> None:
    """Add facts.source_episodes to a legacy minimal fixture schema."""
    conn = sqlite3.connect(str(semantic_db))
    try:
        cols = [c[1] for c in conn.execute("PRAGMA table_info(facts)")]
        if "source_episodes" not in cols:
            conn.execute("ALTER TABLE facts ADD COLUMN source_episodes TEXT")
            conn.commit()
    finally:
        conn.close()
