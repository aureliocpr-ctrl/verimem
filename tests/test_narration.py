"""Narration detection / atomic extraction / reversible archive (2026-06-13).

Aurelio: "la narrazione ci faceva deragliare e hallucinare e confabulare" — ~34%
of curated facts are long dated session stories that recall surfaces as current
truth. Decision: extract the atomic verifiable claims, archive the prose.
"""
from __future__ import annotations

import sqlite3

from engram.narration import (
    archive_and_extract_narration,
    extract_atomic_candidates,
    is_session_narration,
)

_NARR = (
    "ENGRAM 2026-06-13 sera: PIVOT al dolore vero di Aurelio (blocchi save/recall). "
    "#217 merged (commit 8d848fa), recall encode bounded a 2s in semantic.py:2129. "
    "Critic 3-0-0. Il junk telemetria e sparito dal recall live, ri-probato due volte. "
    "#218 telemetry single-source merged, #219 episodi call-telemetria in CI. "
    "Quartetto memoria-proattiva validato live in produzione, campi presenti in hippo_briefing. "
    "PROSSIMO: estendere la signature semantica a risk-guard e emerging via memory.recall."
)


def test_detects_dated_session_narration():
    assert is_session_narration(_NARR) is True
    assert is_session_narration(
        "HippoAgent roadmap 2026-05-11 P0 (sblocca tutto, 3-4 giorni): #1 Hook automatici "
        "Claude Code via engram install-hooks; #2 reasoning layer con STRIPS; #3 confidence "
        "assessment reale non stub; #4 entity-KG live sul corpus; #5 PPR ranking top-k; e cosi "
        "via per parecchie altre righe ancora, ben oltre la soglia minima di trecento caratteri."
    ) is True
    assert is_session_narration("Cycle #74 RAMO 11 FASE A.2 esplorare 9 progetti " + "x" * 300) is True


def test_does_not_flag_atomic_facts():
    # short atomic fact, even if it mentions a date -> NOT narration
    assert is_session_narration("PR #217 was merged into main on 2026-06-13.") is False
    assert is_session_narration("recall query-encode is bounded at 2s.") is False
    # a long but non-session technical fact (no session prefix) -> NOT narration
    long_tech = ("The cross-encoder reranker is loaded lazily under _RERANKER_LOCK and "
                 "joined with a 3s wall-clock budget so a cold load never hangs recall; "
                 "on overrun the bi-encoder order is kept and the model warms in the background "
                 "for the next query, which keeps the path bounded under contention.")
    assert is_session_narration(long_tech) is False
    # CRITIC COUNTEREXAMPLE (2026-06-13, re-critic): a LONG atomic fact that merely
    # OPENS with a project name (Engram/HippoAgent) and has NO date/marker must NOT
    # be flagged. These MUST be >= min_len (300) — otherwise the length gate
    # short-circuits to False and the test would PASS even on the buggy pre-fix
    # detector, exercising nothing (exactly the flaw the re-critic caught).
    engram_atomic = (
        "Engram exposes 45 hippo_* MCP tools that are free in hosted mode because every "
        "internal LLM call is routed via MCP sampling to the active subscription host, so "
        "there is zero external API cost; recall ranks facts by cosine over a cached numpy "
        "matrix with an optional cross-encoder rerank, while keyword search uses SQL LIKE "
        "with proper wildcard escaping, all over the local SQLite curated corpus of facts."
    )
    hippo_atomic = (
        "HippoAgent persistent memory is an SQLite-backed three-tier store of episodes, facts "
        "and skills that survives across sessions and is queried by cosine recall plus keyword "
        "search; it exposes a hippo_health preflight verifying all three tiers reachable and "
        "returning their counts, plus a hippo_briefing that assembles the session-context "
        "payload deterministically without any LLM call at all in hosted mode."
    )
    assert len(engram_atomic) >= 300 and len(hippo_atomic) >= 300, (
        "counterexamples must clear min_len so they reach the prefix branch (re-critic flaw)"
    )
    assert is_session_narration(engram_atomic) is False
    assert is_session_narration(hippo_atomic) is False


def test_extract_atomic_candidates_keeps_verifiable_clauses():
    atoms = extract_atomic_candidates(_NARR)
    joined = " || ".join(atoms)
    assert any("8d848fa" in a or "#217" in a for a in atoms), f"must keep the SHA/PR clause: {joined}"
    assert any("semantic.py:2129" in a for a in atoms), f"must keep the file:line clause: {joined}"
    # the vague "PROSSIMO: estendere ..." has no verifiable anchor -> dropped
    assert all("PROSSIMO" not in a for a in atoms), f"vague planning clause must be dropped: {joined}"


def test_extract_is_safe_and_dedups():
    assert extract_atomic_candidates("") == []
    assert extract_atomic_candidates(None) == []
    dup = "PR #5 merged. PR #5 merged. file.py:10 fixed."
    atoms = extract_atomic_candidates(dup)
    assert len([a for a in atoms if "#5" in a]) == 1, "case-folded duplicates collapse"


def _seed_db(path):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE facts (id TEXT PRIMARY KEY, topic TEXT, proposition TEXT, "
                "created_at REAL, superseded_by TEXT)")
    con.execute("INSERT INTO facts VALUES('n1','project/engram',?,1.0,NULL)", (_NARR,))
    con.execute("INSERT INTO facts VALUES('a1','geo','Paris is the capital of France.',1.0,NULL)")
    con.commit()
    con.close()


def test_archive_dry_run_reports_without_mutating(tmp_path):
    db = tmp_path / "s.db"
    _seed_db(db)
    out = archive_and_extract_narration(db, dry_run=True)
    assert out["dry_run"] is True
    assert out["scanned"] == 2
    assert out["narration_found"] == 1   # only n1
    assert out["atomic_candidates"] >= 2  # SHA/PR + file:line clauses
    assert out["archived"] == 0
    # nothing moved
    con = sqlite3.connect(db)
    assert con.execute("SELECT count(*) FROM facts").fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM sqlite_master WHERE name='narrative'").fetchone()[0] == 0
    con.close()


def test_archive_live_moves_narration_only_nonlossy(tmp_path):
    db = tmp_path / "s.db"
    _seed_db(db)
    out = archive_and_extract_narration(db, dry_run=False)
    assert out["archived"] == 1
    con = sqlite3.connect(db)
    # the narration left facts, the atomic fact stayed
    facts_ids = {r[0] for r in con.execute("SELECT id FROM facts").fetchall()}
    assert facts_ids == {"a1"}, f"only the narration should leave facts, got {facts_ids}"
    # non-lossy: the prose is preserved verbatim in `narrative`
    row = con.execute("SELECT proposition FROM narrative WHERE id='n1'").fetchone()
    assert row is not None and row[0] == _NARR
    con.close()
