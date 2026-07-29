""""Gate actions (all time)" is not all time, and the same screen proves it.

`verimem stats` on the live store today:

    Gate actions (all time)
      admitted:    198
      quarantined: 9
    Live facts by status  ... quarantined:511 ...

Two numbers for the same word, three lines apart, differing 57-fold. Both are
correct: the first counts entries in trust_ledger, the second counts facts whose
status is quarantined. Nothing says the ledger only started recording on
2026-07-15, so 5836 of 6443 facts — 90.6% of the corpus — predate every number
under that heading.

A reader who takes "all time" at face value concludes their store was screened
and 9 things were held back. The honest version of that sentence is "9 out of
the 9.4% of writes this ledger has seen".

The fix is the heading, not the numbers. This is the same shape as the rest of
the audit: the product states something true in a way that reads as something
else.
"""
from __future__ import annotations

import re
import sqlite3
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _plain(text: str) -> str:
    return _ANSI.sub("", text or "")


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Path:
    d = Path(tempfile.mkdtemp(prefix="stats_window_"))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(d))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(d))
    monkeypatch.setenv("VERIMEM_DATA_DIR", str(d))
    # `--validate off` skips the gate, and the gate is what writes the ledger —
    # so this one exists in the store and NOT in the ledger, which is exactly
    # the 90.6% case on the live corpus.
    r = runner.invoke(app, ["facts", "add", "-p", "Il contatore vale quattro.",
                            "-t", "test/stats", "--validate", "off"])
    assert r.exit_code == 0, r.output
    db = d / "semantic" / "semantic.db"
    con = sqlite3.connect(str(db))
    con.execute("UPDATE facts SET created_at = 1000000000")
    con.commit()
    con.close()
    # and one through `save`, which goes via Memory() — the path that creates
    # and writes the trust ledger. `facts add` does not, which is itself part
    # of why the ledger has seen so little of the corpus.
    r2 = runner.invoke(app, ["save", "Il totale della fattura e 1240 euro.",
                             "--topic", "test/stats"])
    assert r2.exit_code == 0, r2.output
    return d


def test_the_heading_states_the_window_it_counts(store: Path):
    r = runner.invoke(app, ["stats"])
    assert r.exit_code == 0, r.output
    out = _plain(r.output)
    assert "Gate actions" in out, out
    heading = next(ln for ln in out.splitlines() if "Gate actions" in ln)
    assert "all time" not in heading.lower(), (
        f"still claims to cover everything: {heading!r}"
    )


def test_it_says_how_much_of_the_corpus_the_ledger_covers(store: Path):
    """A percentage, because the gap is the whole point: on the live store the
    ledger has seen 9.4% of the facts, and the reader cannot guess that."""
    r = runner.invoke(app, ["stats"])
    out = _plain(r.output)
    assert re.search(r"\d+(\.\d+)?%", out), (
        f"no coverage figure anywhere in stats:\n{out}"
    )
