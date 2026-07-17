"""Cycle 242 — quick deep-dive into a named emerging skill cluster.

Usage::

    python -m scripts.inspect_emerging_cluster antigravity
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from verimem.skill_emergence_detector import detect_emerging_skills


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    needle = args[0] if args else "master"
    db = Path.home() / ".engram" / "semantic" / "semantic.db"
    candidates = detect_emerging_skills(
        db, min_community_size=4, min_topic_purity=0.1,
        min_cohesion=0.05, max_n=10,
    )
    matches = [
        c for c in candidates
        if needle in str(c.get("suggested_skill_name", ""))
    ]
    if not matches:
        print(f"no cluster matching {needle!r}")
        return 1
    c = matches[0]
    print(f"Cluster: {c['suggested_skill_name']}")
    print(
        f"  community_id={c['community_id']} size={c['size']} "
        f"purity={c['topic_purity']:.2f} cohesion={c['cohesion']:.2f}",
    )
    print(f"  dominant_topic={c['dominant_topic']}")
    conn = sqlite3.connect(str(db))
    try:
        for fid in c["fact_ids"][:8]:
            row = conn.execute(
                "SELECT topic, substr(proposition, 1, 220) "
                "FROM facts WHERE id = ?",
                (fid,),
            ).fetchone()
            if row:
                print(f"\n  [{fid[:8]}] topic={row[0]}")
                print(f"    {row[1]}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
