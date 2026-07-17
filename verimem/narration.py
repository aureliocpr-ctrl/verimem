"""Narration vs atomic knowledge (verimem.narration).

Empirical motivation (2026-06-13, measured on the live store): ~34% of the
curated ``facts`` are NARRATION — long, dated, first-person session summaries
("ENGRAM 2026-06-13 sera: PIVOT …", "HippoAgent roadmap 2026-05-11 P0 …"). They
are *time-bound stories presented as atemporal facts*: long + semantically rich,
they dominate recall, and a later instance reads them as CURRENT TRUTH and acts
on stale state — the A1 "confabulazione mascherata da continuità" anti-pattern
Aurelio flagged ("la narrazione ci faceva deragliare e hallucinare").

Decision (Aurelio, 2026-06-13): **extract the atomic verifiable claims, then
archive the prose** — turn narration into real knowledge instead of discarding
it. This module is the deterministic, no-LLM FOUNDATION:

  - ``is_session_narration``  — precise detector (dated/session prefix + length),
    tuned for PRECISION (never flags a short atomic fact).
  - ``extract_atomic_candidates`` — split the prose into short clauses that carry
    a VERIFIABLE anchor (commit SHA, PR#, file:line, a strong outcome verb). A
    rule-based first pass; an LLM refinement (verimem.openie / sleep) can replace
    it later for higher recall.
  - ``archive_and_extract_narration`` — the reversible migration (``dry_run`` by
    default, like ``admission_cleanup``): report what WOULD move before touching
    the live corpus.
"""
from __future__ import annotations

import re
from typing import Any

# A session/cycle JOURNAL marker at the very start — these are always narratives.
# NB (critic counterexample 2026-06-13): a bare project name (Engram/HippoAgent)
# is NOT a marker — real atomic facts routinely open with it ("Engram exposes 45
# hippo_* tools …"), and flagging those would wrongly archive REAL knowledge.
# Narration is distinguished by an explicit session/cycle marker OR a DATE in the
# opening window (the dated self-summaries), never by the project name alone.
_SESSION_MARKER = re.compile(
    r"^\s*(?:"
    r"Cycle\s*#?\d|CICLO\b|Wave\s*\d|WAVE\s+\d|Loop\s*\d|LOOP\s*\d|"
    r"HANDOFF\b|RESUME\b|SESSIONE\b|RIPRENDI\b"
    r")",
    re.IGNORECASE,
)
#: The proposition OPENS with an ISO date — a dated record/summary.
_LEADING_DATE = re.compile(r"^\s*\d{4}-\d\d-\d\d")
#: A project name immediately FOLLOWED (within 30 chars) by a date — the
#: "ENGRAM 2026-06-13 sera: …" session-summary shape. The date next to the name
#: is what makes it a journal; the name ALONE is not (see _SESSION_MARKER note).
_PROJECT_DATE = re.compile(
    r"^\s*(?:ENGRAM|Engram|HippoAgent|HIPPOAGENT)\b.{0,30}?\d{4}-\d\d-\d\d",
    re.IGNORECASE,
)

#: A clause carries a VERIFIABLE anchor if it cites concrete evidence.
#: The SHA branch (2026-06-19 fix) excludes UUID segments: a hex run adjacent to a
#: dash+hex (``82f5aa75-856d-…``) is a UUID/session-id, NOT a commit SHA — the old
#: ``\b[0-9a-f]{7,40}\b`` matched those and emitted raw ids as "atoms".
_VERIFY_ANCHOR = re.compile(
    r"(?:(?<![0-9a-f-])[0-9a-f]{7,40}(?![0-9a-f-])"   # commit SHA (not a UUID segment)
    r"|#\d{1,5}\b|\bPR\s?\d+\b"        # PR / issue number
    r"|\b\w+\.py:\d+\b|\b\w+\.py\b"    # file or file:line
    r"|\b(?:merged|shipped|fixed|bounded|verified|critic|claim_holds|"
    r"resolved|deleted|added|removed|renamed|reverted)\b"
    r"|\d+\s?(?:s|ms|x|%|chars?|facts?|episodes?|tests?)(?![a-z]))",  # number + unit
    re.IGNORECASE,  # (?![a-z]): the unit must end a word, so '8 sopravvive'/'10 SNLI' don't match
)

# Split into clauses on sentence ends, newlines, and the bullet separators the
# narration uses (· | ; → ·).
_CLAUSE_SPLIT = re.compile(r"(?<=[.;:])\s+|\n+|\s+[·|→]\s+|\s{2,}")

#: Markdown emphasis/quote to strip. NB: NOT ``_`` (code identifiers like
#: anti_confab_gate.py) and NOT ``#`` mid-text (PR/issue refs like #5) — only a
#: LEADING ``#`` heading marker is removed (_LEAD_HEADING below).
_MD_STRIP = re.compile(r"[*`>]+")
_LEAD_HEADING = re.compile(r"^\s*#+\s*")
#: A real atomic clause must carry an actual word, not be a bare id / heading / symbol run.
_ALPHA_WORD = re.compile(r"[A-Za-z]{3,}")


def _clean_clause(clause: str) -> str:
    """Strip markdown emphasis/heading/bullet noise and surrounding punctuation."""
    c = _LEAD_HEADING.sub("", clause)   # leading '#' heading marker (keeps mid-text #5)
    c = _MD_STRIP.sub("", c)
    return c.strip(" \t—-–·|:[]()").strip()


def _has_real_content(clause: str) -> bool:
    """Reject bare ids / heading fragments / symbol runs: require >=1 real word AND a
    majority of alphanumeric characters (a raw UUID has 0 words >=3 letters)."""
    if not _ALPHA_WORD.search(clause):
        return False
    alnum = sum(ch.isalnum() or ch.isspace() for ch in clause)
    return alnum >= 0.6 * len(clause)


def is_session_narration(
    proposition: str | None, *, min_len: int = 300, date_window: int = 60,
) -> bool:
    """True when ``proposition`` is a long dated/session narrative, NOT an atomic
    fact. PRECISION-tuned: requires length >= ``min_len`` AND either an explicit
    session/cycle marker at the start OR an ISO date within the first
    ``date_window`` chars. A long atomic technical fact that merely opens with a
    project name (Engram/HippoAgent) — or a short fact, even a dated one — is
    NEVER flagged, so the reversible archive can't remove real knowledge."""
    p = (proposition or "").strip()
    if len(p) < min_len:
        return False
    del date_window  # kept for signature stability; opening-anchored now
    return bool(
        _LEADING_DATE.match(p)        # opens with a date: "2026-06-13 VERIFIED …"
        or _PROJECT_DATE.match(p)     # "ENGRAM 2026-06-13 sera: …"
        or _SESSION_MARKER.match(p)   # "Cycle #74 …", "HANDOFF …", "RESUME …"
    )


def extract_atomic_candidates(
    proposition: str | None, *, min_clause: int = 12, max_clause: int = 220,
) -> list[str]:
    """Pull the short, VERIFIABLE clauses out of a narrative.

    Each returned string is a candidate atomic fact: between ``min_clause`` and
    ``max_clause`` chars AND carrying a concrete anchor (SHA / PR# / file:line /
    outcome verb / number+unit). Deterministic and order-preserving; duplicates
    (case-folded) are dropped. Safe on empty input. This is the rule-based first
    pass — an LLM extractor can raise recall later without changing the contract.
    """
    text = (proposition or "").strip()
    if not text:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in _CLAUSE_SPLIT.split(text):
        clause = _clean_clause(raw)
        if not (min_clause <= len(clause) <= max_clause):
            continue
        if not _VERIFY_ANCHOR.search(clause):
            continue
        if not _has_real_content(clause):   # drop bare ids / headings / symbol runs
            continue
        key = re.sub(r"\s+", " ", clause.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(clause)
    return out


def archive_and_extract_narration(
    db_path, *, dry_run: bool = True, llm: Any = None,
) -> dict[str, Any]:
    """Reversible: move NARRATION facts out of the curated ``facts`` table into a
    ``narrative`` archive, after extracting their atomic candidate claims.

    Atomic extraction: rule-based by default (``extract_atomic_candidates``); when
    an ``llm`` is given (``verimem.llm.get_llm()``), the higher-recall LLM extractor
    (``verimem.narration_llm.extract_atomic_facts``) is used instead.

    Safety contract (mirrors verimem.admission_cleanup):
      - ``dry_run=True`` by DEFAULT — reports only, mutates nothing.
      - Non-lossy: the full prose is preserved in ``narrative`` (id, topic,
        proposition, created_at); the extracted atomic candidates are reported
        (and, when not dry-run, are NOT auto-inserted here — insertion as real
        facts is a separate, reviewed step so a crude rule-pass can't pollute).
      - Run with the MCP server STOPPED; the authoritative undo is the pre-run
        DB backup.

    Returns ``{scanned, narration_found, atomic_candidates, archived, dry_run}``.
    """
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, topic, proposition, created_at FROM facts "
            "WHERE superseded_by IS NULL"
        ).fetchall()
        narration = [r for r in rows if is_session_narration(r["proposition"])]
        if llm is not None:
            from .narration_llm import extract_atomic_facts
            n_atoms = sum(len(extract_atomic_facts(r["proposition"], llm)) for r in narration)
        else:
            n_atoms = sum(len(extract_atomic_candidates(r["proposition"])) for r in narration)
        archived = 0
        if not dry_run and narration:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS narrative ("
                "id TEXT PRIMARY KEY, topic TEXT, proposition TEXT, created_at REAL)"
            )
            for r in narration:
                conn.execute(
                    "INSERT OR REPLACE INTO narrative(id, topic, proposition, created_at) "
                    "VALUES(?,?,?,?)",
                    (r["id"], r["topic"], r["proposition"], r["created_at"]),
                )
                conn.execute("DELETE FROM facts WHERE id=?", (r["id"],))
                archived += 1
            conn.commit()
        return {
            "scanned": len(rows),
            "narration_found": len(narration),
            "atomic_candidates": n_atoms,
            "archived": archived,
            "dry_run": dry_run,
        }
    finally:
        conn.close()


__all__ = [
    "is_session_narration",
    "extract_atomic_candidates",
    "archive_and_extract_narration",
]
