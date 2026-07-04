"""Backlog cleanup for the EPISODE telemetry gate (2026-06-14).

The episode gate (engram.memory._store_episode_telemetry, opt-in) routes only NEW
cross-LLM call records ([agy-call …]) to ``episode_telemetry``. This is the gemello
of ``admission_cleanup.cleanup_telemetry`` for the EXISTING episode backlog: it
routes the call-telemetry episodes already sitting in ``episodes`` out to
``episode_telemetry``, reversibly (dry_run default, undo = DB backup).

Decision reuses ``engram._call_telemetry.is_call_telemetry`` (single source of
truth — same predicate the live write-gate uses), so the cleanup and the gate can
never disagree on what counts as telemetry.
"""
from __future__ import annotations

import json
import sqlite3

from engram.admission_cleanup import cleanup_episode_telemetry

# An episode schema with the embedding BLOB columns the live store carries, to
# prove they are DROPPED from the archived payload (telemetry is never recalled
# semantically — same choice as the fact gate).
_SCHEMA = (
    "CREATE TABLE episodes (id TEXT PRIMARY KEY, task_id TEXT, task_text TEXT, "
    "outcome TEXT, final_answer TEXT, created_at REAL, notes TEXT, "
    "summary_embedding BLOB, dg_embedding BLOB, context_embedding BLOB)"
)


def _seed(db):
    con = sqlite3.connect(db)
    con.execute(_SCHEMA)
    # one call-telemetry episode (with a real final_answer + an embedding blob)…
    con.execute(
        "INSERT INTO episodes VALUES('t1','task-1','[agy-call 2026-06-13T08] prompt=hi',"
        "'success','the model answered X',1.0,'note-a',?,?,?)",
        (b"\x01\x02\x03", b"\x04\x05", b"\x06"),
    )
    # …and one REAL task episode that must stay put.
    con.execute(
        "INSERT INTO episodes VALUES('r1','task-2','Fix recall hang in loop.py',"
        "'success','bounded at 2s, commit abc1234',2.0,'note-b',NULL,NULL,NULL)"
    )
    con.commit()
    con.close()


def test_dry_run_reports_but_mutates_nothing(tmp_path):
    db = tmp_path / "ep.db"
    _seed(db)
    res = cleanup_episode_telemetry(db)  # dry_run defaults True
    assert res == {"scanned": 2, "telemetry_found": 1, "moved": 0, "dry_run": True}
    con = sqlite3.connect(db)
    assert con.execute("SELECT count(*) FROM episodes").fetchone()[0] == 2
    # no archive table created on a dry run
    assert con.execute(
        "SELECT count(*) FROM sqlite_master WHERE name='episode_telemetry'"
    ).fetchone()[0] == 0
    con.close()


def test_apply_moves_only_telemetry_non_lossy(tmp_path):
    db = tmp_path / "ep.db"
    _seed(db)
    res = cleanup_episode_telemetry(db, dry_run=False)
    assert res == {"scanned": 2, "telemetry_found": 1, "moved": 1, "dry_run": False}
    con = sqlite3.connect(db)
    # the real task survives in episodes; the telemetry one is gone
    left = [r[0] for r in con.execute("SELECT id FROM episodes").fetchall()]
    assert left == ["r1"]
    arch = con.execute(
        "SELECT id, task_text, outcome, created_at, payload FROM episode_telemetry"
    ).fetchall()
    assert len(arch) == 1
    aid, atext, aout, acreated, payload = arch[0]
    assert aid == "t1" and aout == "success" and acreated == 1.0
    # non-lossy on the meaningful fields: final_answer + notes preserved in payload
    p = json.loads(payload)
    assert p["final_answer"] == "the model answered X"
    assert p["notes"] == "note-a"
    assert p["task_text"].startswith("[agy-call")
    # embeddings DROPPED (not str(bytes) blobs bloating the archive)
    assert "summary_embedding" not in p
    assert "dg_embedding" not in p
    assert "context_embedding" not in p
    con.close()


def test_idempotent_second_run_is_noop(tmp_path):
    db = tmp_path / "ep.db"
    _seed(db)
    cleanup_episode_telemetry(db, dry_run=False)
    again = cleanup_episode_telemetry(db, dry_run=False)
    assert again == {"scanned": 1, "telemetry_found": 0, "moved": 0, "dry_run": False}


def test_empty_or_no_telemetry_safe(tmp_path):
    db = tmp_path / "ep.db"
    con = sqlite3.connect(db)
    con.execute(_SCHEMA)
    con.execute(
        "INSERT INTO episodes VALUES('r1','t','Real task only','success','ans',1.0,"
        "'n',NULL,NULL,NULL)"
    )
    con.commit()
    con.close()
    res = cleanup_episode_telemetry(db, dry_run=False)
    assert res["telemetry_found"] == 0 and res["moved"] == 0


# --- critic counterexample 2026-06-14: linked traces must be archived + deleted,
#     never left orphaned (no reliance on PRAGMA foreign_keys) ---

_TRACES = (
    "CREATE TABLE traces (episode_id TEXT, step INTEGER, thought TEXT, action TEXT, "
    "action_input TEXT, observation TEXT)"
)


def test_linked_traces_archived_and_deleted_not_orphaned(tmp_path):
    db = tmp_path / "ep.db"
    con = sqlite3.connect(db)
    con.execute(_SCHEMA)
    con.execute(_TRACES)
    con.execute(
        "INSERT INTO episodes VALUES('t1','task','[gemini-call 2026] p','success',"
        "'ans',1.0,'n',NULL,NULL,NULL)"
    )
    con.execute("INSERT INTO traces VALUES('t1',0,'th0','act0','in0','obs0')")
    con.execute("INSERT INTO traces VALUES('t1',1,'th1','act1','in1','obs1')")
    # a REAL episode + its trace must be untouched
    con.execute(
        "INSERT INTO episodes VALUES('r1','task','Real task','success','ans',2.0,"
        "'n',NULL,NULL,NULL)"
    )
    con.execute("INSERT INTO traces VALUES('r1',0,'rth','ract','rin','robs')")
    con.commit()
    con.close()

    res = cleanup_episode_telemetry(db, dry_run=False)
    assert res["moved"] == 1
    con = sqlite3.connect(db)
    # telemetry traces deleted (no orphan), real trace kept
    assert con.execute(
        "SELECT count(*) FROM traces WHERE episode_id='t1'"
    ).fetchone()[0] == 0
    assert con.execute(
        "SELECT count(*) FROM traces WHERE episode_id='r1'"
    ).fetchone()[0] == 1
    # traces archived non-lossy in the payload
    payload = json.loads(
        con.execute("SELECT payload FROM episode_telemetry WHERE id='t1'").fetchone()[0]
    )
    assert len(payload["_traces"]) == 2
    assert payload["_traces"][0]["action"] == "act0"
    assert payload["_traces"][1]["observation"] == "obs1"
    con.close()


def test_cli_command_is_a_real_entry_point(tmp_path, monkeypatch):
    """The fix is wired to a CLI command (closes the critic's dead-code finding)."""
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    epdir = tmp_path / "episodes"
    epdir.mkdir()
    _seed(epdir / "episodes.db")
    from typer.testing import CliRunner

    from engram.cli import app

    res = CliRunner().invoke(app, ["facts", "cleanup-episode-telemetry"])
    assert res.exit_code == 0, res.output
    assert "DRY-RUN" in res.output and "episode_telemetry=1" in res.output
    # dry run mutated nothing
    con = sqlite3.connect(epdir / "episodes.db")
    assert con.execute("SELECT count(*) FROM episodes").fetchone()[0] == 2
    con.close()
