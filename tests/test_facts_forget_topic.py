"""Forgetting more than one fact, without dropping to SQL.

`verimem facts forget` takes ONE id and calls itself "privacy / GDPR / cleanup".
A GDPR erasure request is about every fact concerning a person, not one; so is
cleaning up a topic. With one id per invocation the cheapest path is a DELETE
against the store — and that path silently gives up the two things the command
exists to provide: the undo snapshot and the audit entry.

That is not hypothetical. On 2026-07-29 I removed three test facts from the live
store with raw SQL rather than run the command three times, having written the
command myself. `total_changes` then read 16 for 3 rows (FTS triggers), which
looked exactly like an over-delete until it was checked — with no undo to fall
back on if it had been one.

So: `--topic <prefix>`, same undo, same audit, one confirmation that states the
count before anything is removed.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Path:
    d = Path(tempfile.mkdtemp(prefix="forget_topic_"))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(d))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(d))
    monkeypatch.setenv("VERIMEM_DATA_DIR", str(d))
    for i, (topic, text) in enumerate([
        ("test/scarti", "Il primo fatto di prova numero uno."),
        ("test/scarti", "Il secondo fatto di prova numero due."),
        ("test/scarti/sotto", "Il terzo fatto di prova numero tre."),
        ("test/tenere", "Questo fatto deve sopravvivere alla pulizia."),
    ]):
        r = runner.invoke(app, ["facts", "add", "-p", text, "-t", topic, "--validate", "off"])
        assert r.exit_code == 0, r.output
    return d


def _n_facts(topic_like: str) -> int:
    r = runner.invoke(app, ["facts", "list", "--limit", "50"])
    return r.output.count(topic_like)


def test_a_topic_prefix_removes_its_facts_and_spares_the_others(store: Path):
    r = runner.invoke(app, ["facts", "forget", "--topic", "test/scarti", "--yes"])
    assert r.exit_code == 0, r.output
    assert "3" in r.output, f"the receipt must state how many: {r.output}"

    left = runner.invoke(app, ["facts", "list", "--limit", "50"])
    assert "sopravvivere" in left.output, "a sibling topic was removed too"
    assert "numero uno" not in left.output
    assert "numero tre" not in left.output, "the prefix must include sub-topics"


def test_removing_a_batch_is_still_undoable(store: Path):
    """The whole reason to use the command instead of a DELETE — asserted by
    actually restoring, not by reading the listing. A row in a table proves the
    bookkeeping; only a restored fact proves the undo."""
    r = runner.invoke(app, ["facts", "forget", "--topic", "test/scarti", "--yes"])
    assert r.exit_code == 0, r.output

    listing = runner.invoke(app, ["facts", "undo-list"])
    assert listing.exit_code == 0, listing.output
    assert listing.output.count("forget") >= 3, (
        f"3 facts removed, fewer undo entries recorded:\n{listing.output}"
    )

    op_ids = re.findall(r"\b([0-9a-f]{8,})…?", listing.output)
    assert op_ids, f"no op id to undo:\n{listing.output}"
    undone = runner.invoke(app, ["facts", "undo", op_ids[0]])
    assert undone.exit_code == 0, undone.output

    back = runner.invoke(app, ["facts", "list", "--limit", "50"])
    assert "numero" in back.output, (
        f"the undo reported success and restored nothing:\n{back.output}"
    )


def test_it_refuses_both_an_id_and_a_topic(store: Path):
    r = runner.invoke(app, ["facts", "forget", "abc123", "--topic", "test/scarti",
                            "--yes"])
    assert r.exit_code != 0
    assert "one" in r.output.lower() or "either" in r.output.lower(), r.output


def test_it_refuses_neither(store: Path):
    r = runner.invoke(app, ["facts", "forget", "--yes"])
    assert r.exit_code != 0


def test_a_topic_that_matches_nothing_deletes_nothing(store: Path):
    r = runner.invoke(app, ["facts", "forget", "--topic", "test/inesistente",
                            "--yes"])
    assert "0" in r.output or "no facts" in r.output.lower(), r.output
    left = runner.invoke(app, ["facts", "list", "--limit", "50"])
    assert "sopravvivere" in left.output


def test_undo_accepts_the_id_as_it_appears_on_screen(store: Path):
    """The safety net has to be reachable from its own listing.

    `facts undo-list` renders op_id in a Rich column that truncates it to
    "9969b43c039c44…", and `facts undo` used to require the full string — so
    pasting exactly what is displayed answered "not found". The undo existed,
    was recorded correctly, and could not be invoked. `facts forget` has always
    resolved fact ids by prefix; this makes undo consistent with it.
    """
    r = runner.invoke(app, ["facts", "forget", "--topic", "test/tenere", "--yes"])
    assert r.exit_code == 0, r.output

    listing = runner.invoke(app, ["facts", "undo-list"])
    shown = re.search(r"\b([0-9a-f]{10,})…", listing.output)
    assert shown, f"expected a truncated id in the table:\n{listing.output}"

    undone = runner.invoke(app, ["facts", "undo", shown.group(1)])
    assert undone.exit_code == 0, (
        f"could not undo with the id the listing shows:\n{undone.output}"
    )
    back = runner.invoke(app, ["facts", "list", "--limit", "50"])
    assert "sopravvivere" in back.output, back.output


def test_an_ambiguous_prefix_is_refused_not_guessed(store: Path):
    """Restoring the wrong fact is worse than asking for more characters."""
    r = runner.invoke(app, ["facts", "forget", "--topic", "test/scarti", "--yes"])
    assert r.exit_code == 0, r.output
    r2 = runner.invoke(app, ["facts", "undo", ""])
    assert r2.exit_code != 0
    assert "ambiguous" in r2.output.lower() or "not found" in r2.output.lower(), r2.output
