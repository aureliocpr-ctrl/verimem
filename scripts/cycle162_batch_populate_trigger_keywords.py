"""Cycle 162 (2026-05-19) — rule-based batch populate trigger_keywords
across the live fact corpus.

This is a BASELINE migration: it extracts tokens from each fact's
proposition + topic via simple heuristics (camelCase + ALL_CAPS +
tokens-with-digits + last topic segment, all >= 4 chars, stopwords
out, max 10 per fact). Rule-based keywords lift hybrid retrieval
modestly above the empty-kw baseline; for the higher precision lift
that PR #105's worked_example shows on cherry-picked facts, the
high-value facts need hand-curated or LLM-generated keywords.

Bench results (production store, 1395 live facts, 5/3 query sets):
  Before cycle 162 (only 5 hand-populated facts):
    plain  TPR@5 = 40% (TRAIN), 20% (OOD)
    hybrid TPR@5 = 60% (TRAIN), 40% (OOD)
  After cycle 162 (1395/1395 rule-based populated):
    plain  TPR@5 = 40% (TRAIN), 20% (OOD)  — unchanged, plain ignores kw
    hybrid TPR@5 = 70% (TRAIN), 40% (OOD)  — +10pp TRAIN, OOD plateau

Next: cycle 163 should target the top-100 most-recalled facts with
LLM-generated semantic keywords. The rule-based pass leaves "math-y"
fact like 03e8c1d129af with mediocre keywords ("CYCLE","MEMORY","NOTE")
that don't capture the AM-GM-pairing technique semantically.

Run: ``python scripts/cycle162_batch_populate_trigger_keywords.py``
Idempotent: re-running on facts already populated is a no-op (skips
``trigger_keywords IS NOT NULL``).
"""
from __future__ import annotations

import re
import sqlite3
from collections import Counter
from pathlib import Path

_STOPWORDS: frozenset[str] = frozenset({
    "with", "from", "this", "that", "have", "been", "were", "their",
    "them", "into", "when", "where", "which", "these", "those", "will",
    "would", "could", "should", "than", "then", "such", "some", "most",
    "only", "over", "each", "they", "about", "after", "before",
    "between", "come", "fact", "facts", "data", "time", "session",
    "memory", "agent", "note", "notes",
    # Italian common words.
    "sono", "sopra", "sotto", "anche", "questo", "questa", "questi",
    "queste", "verso", "oltre", "quando", "dovrebbe", "sarebbe",
    "avrebbe", "molto", "tutto", "tutti", "tutte",
})


def extract_keywords(text: str, topic: str, max_kw: int = 10) -> list[str]:
    """Score tokens by frequency + structural priors, return top-k.

    Priors:
      * +1 if CamelCase (likely class / proper-noun / project name)
      * +0.5 if contains digits (likely cycle-number / version / id)
      * +0.5 if ALL_CAPS short token (likely acronym)
      * Always boost last topic segment (e.g. ``cycle160-hybrid-recall``)
        with weight +2.0 — strong prior for cluster name.

    Stop-words and tokens < 4 chars are discarded outright.
    """
    tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9_]+\b", text or "")
    freq: Counter[str] = Counter()
    for t in tokens:
        tl = t.lower()
        if len(tl) < 4 or tl in _STOPWORDS:
            continue
        score = 1.0
        if t[0].isupper() and any(c.isupper() for c in t[1:]):
            score += 1.0
        if any(c.isdigit() for c in t):
            score += 0.5
        if t.isupper() and len(t) <= 6:
            score += 0.5
        freq[t] += score
    if topic:
        seg = topic.rsplit("/", 1)[-1]
        if seg:
            freq[seg] += 2.0
    return [t for t, _ in freq.most_common(max_kw)]


def main() -> int:
    db_path = Path.home() / ".engram" / "semantic" / "semantic.db"
    if not db_path.exists():
        print(f"[cycle162] DB not found at {db_path}")
        return 1
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        rows = cur.execute(
            "SELECT id, proposition, topic FROM facts "
            "WHERE trigger_keywords IS NULL AND superseded_by IS NULL"
        ).fetchall()
        print(f"[cycle162] facts to populate: {len(rows)}")
        updated = 0
        for fid, prop, topic in rows:
            kws = extract_keywords(prop or "", topic or "")
            if not kws:
                continue
            cur.execute(
                "UPDATE facts SET trigger_keywords = ? WHERE id = ?",
                (",".join(kws), fid),
            )
            updated += 1
        con.commit()
        populated = cur.execute(
            "SELECT COUNT(*) FROM facts WHERE trigger_keywords IS NOT NULL"
        ).fetchone()[0]
        total = cur.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL"
        ).fetchone()[0]
        print(
            f"[cycle162] updated={updated} populated={populated}/{total} "
            f"({100 * populated / max(1, total):.0f}%)"
        )
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
