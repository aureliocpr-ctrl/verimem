"""Audit#2 2026-06-08 A-5: register_emerging_drafts_as_facts opened the SQLite
connection with NO busy_timeout (so a contended write raised 'database is
locked' immediately instead of waiting — the real deployment is multi-process)
AND swallowed any sqlite3.Error silently (`except sqlite3.Error: pass`-style),
so a persistent write failure vanished with no operator signal. Fix: connect
with timeout=60s (matches the other DBs) and LOG the error before returning the
skipped count.
"""
from __future__ import annotations

import logging

from verimem.emerging_skill_register import register_emerging_drafts_as_facts


def test_sql_error_is_logged_not_swallowed(tmp_path, caplog):
    # A DIRECTORY at the db path passes the `.exists()` guard but makes
    # sqlite3.connect raise OperationalError -> the except branch fires.
    bad = tmp_path / "is_a_dir"
    bad.mkdir()
    drafts = [{"skill_name": "s1"}, {"skill_name": "s2"}]

    with caplog.at_level(logging.WARNING):
        res = register_emerging_drafts_as_facts(str(bad), drafts)

    assert res["n_skipped"] == len(drafts)
    assert res["n_inserted"] == 0 and res["n_updated"] == 0
    assert any(
        "emerging" in r.getMessage().lower() or "register" in r.getMessage().lower()
        for r in caplog.records
    ), "SQL error swallowed without any log record (A-5)"
