"""Cycle 165 (2026-05-19) — rule-based batch populate ``applicable_when``.

Companion to cycle 162 (trigger_keywords). Builds a 1-sentence
condition for each fact by combining:

  (a) Topic taxonomy (skip date-shaped segments), capped at 3 segments,
      formatted as ``"task touches X / Y / Z"``.
  (b) First sentence of proposition (split on .!?), trimmed to ≤200
      chars, lowercased.

Joined with "; " and capped at 300 chars total. Idempotent: skips
facts whose ``applicable_when`` is already non-NULL (preserves cycle
160 hand-curated values on the cherry-picked top-5).

Bench post-cycle165 (production, 1397 live facts, 99% coverage on
applicable_when):
  TRAIN bench (keyword-match queries)
    plain  TPR@5 = 40%
    hybrid TPR@5 = 80%   (+10pp from cycle 162 hybrid 70%, +40pp
                          absolute vs plain)
  OOD bench (paraphrased queries)
    plain  TPR@5 = 20%
    hybrid TPR@5 = 40%   (unchanged — rule-based applicable_when from
                          topic + first sentence doesn't generate
                          sufficient lexical overlap with strong
                          paraphrases; cycle 166 needs LLM-generated
                          semantic conditions)

Run: ``python scripts/cycle165_batch_populate_applicable_when.py``
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SENT_SPLIT = re.compile(r"[.!?]")


def derive_applicable_when(proposition: str, topic: str) -> str:
    parts: list[str] = []
    if topic:
        segs = [s for s in topic.split("/") if s and not _DATE_RE.match(s)]
        if segs:
            parts.append("task touches " + " / ".join(segs[:3]))
    if proposition:
        first = _SENT_SPLIT.split(proposition, maxsplit=1)[0].strip()
        if 5 < len(first) <= 200:
            parts.append(first.lower())
    return "; ".join(parts)[:300]


def main() -> int:
    db_path = Path.home() / ".engram" / "semantic" / "semantic.db"
    if not db_path.exists():
        print(f"[cycle165] DB not found at {db_path}")
        return 1
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        rows = cur.execute(
            "SELECT id, proposition, topic FROM facts "
            "WHERE applicable_when IS NULL AND superseded_by IS NULL"
        ).fetchall()
        print(f"[cycle165] facts to populate: {len(rows)}")
        updated = 0
        for fid, prop, topic in rows:
            aw = derive_applicable_when(prop or "", topic or "")
            if not aw:
                continue
            cur.execute(
                "UPDATE facts SET applicable_when = ? WHERE id = ?",
                (aw, fid),
            )
            updated += 1
        con.commit()
        populated = cur.execute(
            "SELECT COUNT(*) FROM facts WHERE applicable_when IS NOT NULL"
        ).fetchone()[0]
        total = cur.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL"
        ).fetchone()[0]
        print(
            f"[cycle165] updated={updated} populated={populated}/{total} "
            f"({100 * populated / max(1, total):.0f}%)"
        )
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
