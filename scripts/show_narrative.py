"""Cycle 201 (2026-05-23) — ASCII narrative visualiser.

Standalone script that calls ``verimem.temporal_narrative.reconstruct_narrative``
(cycle 193) and prints the result as an ASCII timeline.

Run:
    python scripts/show_narrative.py <fact_id_prefix> [window_days]

Example:
    python scripts/show_narrative.py 9ca3d42a 30

NO touch to mcp_server.py / cli.py — purely user-facing standalone
operator tool that exercises cycles 193's pure function on the live
~/.engram/semantic.db corpus.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

_ROLE_GLYPHS: dict[str, str] = {
    "root":       "█",  # the seed
    "antecedent": "←",
    "descendant": "→",
    "revision":   "↻",
    "context":    "·",
}


def _resolve_id_prefix(db_path: Path, prefix: str) -> str | None:
    """Match a fact id by prefix (>=6 chars); return None if ambiguous
    or missing."""
    if len(prefix) < 6:
        return None
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute(
                "SELECT id FROM facts WHERE id LIKE ? || '%' LIMIT 2",
                (prefix,),
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    if len(rows) != 1:
        return None
    return str(rows[0][0])


def _format_ts(ts: float) -> str:
    try:
        return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        return "?"


def _format_prop(db_path: Path, fact_id: str, max_chars: int = 80) -> str:
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT proposition FROM facts WHERE id = ?",
                (fact_id,),
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return "<err>"
    if row is None:
        return "<missing>"
    prop = str(row[0] or "")
    if len(prop) > max_chars:
        return prop[: max_chars - 1].replace("\n", " ") + "…"
    return prop.replace("\n", " ")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        sys.stderr.write(
            "usage: show_narrative.py <fact_id_prefix> [window_days]\n"
        )
        return 2

    prefix = argv[0]
    window_days = float(argv[1]) if len(argv) >= 2 else 30.0

    db = Path.home() / ".engram" / "semantic" / "semantic.db"
    if not db.exists():
        sys.stderr.write(f"semantic.db not found at {db}\n")
        return 1

    full_id = _resolve_id_prefix(db, prefix)
    if full_id is None:
        sys.stderr.write(
            f"fact id prefix {prefix!r} did not resolve to exactly 1 row\n"
        )
        return 3

    from verimem.temporal_narrative import reconstruct_narrative
    entries = reconstruct_narrative(
        db, seed_fact_id=full_id, window_days=window_days,
    )
    if not entries:
        sys.stderr.write(f"no narrative for fact {full_id}\n")
        return 4

    print(
        f"=== Narrative for {full_id} (window={window_days}d, "
        f"{len(entries)} entries) ===",
    )
    print()
    for e in entries:
        glyph = _ROLE_GLYPHS.get(e["role"], "?")
        ts_str = _format_ts(e["ts"])
        role = e["role"].ljust(11)
        prop = _format_prop(db, e["fact_id"], max_chars=70)
        print(f"  {glyph} {ts_str}  {role}  {e['fact_id'][:12]}  {prop}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
