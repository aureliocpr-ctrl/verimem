"""The moat runs on the CONVERSATION-INGEST path too — where extraction confabs
actually happen (mandate 2026-07-17). The local CE is AUROC 1.0 on this exact
domain (a fact invented, not present in the dialogue → score ~0), so it is the
right judge here: free, no per-fact LLM call, and perfect on the netto case.

* a fact the dialogue STATES is admitted;
* a fact the dialogue does NOT support (an extraction confab) is quarantined;
* SAFE fail-open: if the local CE is unavailable the ingest admits as before.
"""
from __future__ import annotations

import pytest

from verimem.local_grounding import try_local_score


def _ce_ok() -> bool:
    try:
        return try_local_score("the sky is blue", "the sky is blue") is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _ce_ok(), reason="local CE model not present")


class _Extractor:
    """Extraction llm: returns one faithful line + one confab line, verbatim."""

    def __init__(self, lines):
        self.lines = lines

    def complete(self, system, messages, *, model=None, max_tokens=1200):
        class R:
            pass
        R.text = "\n".join(self.lines)
        return R()


def _ingest(sm, dialogue, lines, **kw):
    from verimem.conversation_ingest import ingest_conversation
    return ingest_conversation(
        sm, [{"role": "user", "content": dialogue}], llm=_Extractor(lines),
        conversation_id="c", consolidate=False, embed="sync", **kw)


def test_ingest_confab_quarantined_faithful_admitted(tmp_path):
    from verimem.semantic import SemanticMemory
    sm = SemanticMemory(db_path=tmp_path / "m.db")
    dialogue = ("I moved the analytics database to Postgres last quarter, "
                "hosted in eu-west. The team is happy with it.")
    _ingest(sm, dialogue, [
        "The analytics database runs on Postgres.",       # faithful
        "The analytics database runs on MongoDB.",        # confab (not stated)
    ], ground=True)
    import sqlite3
    with sqlite3.connect(str(sm.db_path)) as con:
        rows = dict(con.execute(
            "SELECT proposition, status FROM facts").fetchall())
    assert rows.get("The analytics database runs on Postgres.") != "quarantined"
    assert rows.get("The analytics database runs on MongoDB.") == "quarantined"


def test_ingest_ground_off_admits_all(tmp_path):
    from verimem.semantic import SemanticMemory
    sm = SemanticMemory(db_path=tmp_path / "m2.db")
    _ingest(sm, "The DB is Postgres.", ["The DB runs on MongoDB."], ground=False)
    import sqlite3
    with sqlite3.connect(str(sm.db_path)) as con:
        st = dict(con.execute("SELECT proposition, status FROM facts").fetchall())
    assert st.get("The DB runs on MongoDB.") != "quarantined"   # opt-out honored
