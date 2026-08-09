"""A save that retires an older fact says nothing about it.

`save_checkpoint` returns the ids it superseded — client.py:495 sets
``_out["superseded"]`` — and the CLI receipt drops the key. So the write that
takes a fact OUT of default recall is reported exactly like one that adds a new
one.

Seen live 2026-07-29: "il branch ha ventuno commit" was saved this morning, "ha
ventinove commit" this afternoon. The store did the right thing — the first now
carries superseded_by pointing at the second, and recall correctly answers
"ventinove". Nothing in the receipt mentioned that a fact had been retired.

That matters more here than for an ordinary field. Supersession is not additive:
the old value stops being served, and if the routing was wrong (the write path
reads "porta 8080" -> "porta 9090" as two different subjects, not one changed
value — a deliberate call, see quantity_match:683) the only person who can
notice is the one who just wrote it, in the second where they are still looking.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Path:
    d = Path(tempfile.mkdtemp(prefix="save_receipt_"))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(d))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(d))
    monkeypatch.setenv("VERIMEM_DATA_DIR", str(d))
    return d


def test_the_receipt_names_the_fact_it_retired(store: Path) -> None:
    first = runner.invoke(app, [
        "save", "Il servizio gira sulla versione 0.7.0.",
        "--topic", "test/versione",
    ])
    assert first.exit_code == 0, first.output
    second = runner.invoke(app, [
        "save", "Il servizio gira sulla versione 0.8.0.",
        "--topic", "test/versione",
    ])
    assert second.exit_code == 0, second.output
    out = second.output.lower()
    assert "supersed" in out or "retired" in out or "sostitu" in out, (
        "a write that took a fact out of recall reported it like an ordinary "
        f"append:\n{second.output}"
    )


def test_an_ordinary_save_does_not_claim_to_have_retired_anything(
    store: Path,
) -> None:
    """The line must appear only when something WAS retired — a message on
    every save is noise, and noise is how the grounding line got ignored."""
    r = runner.invoke(app, [
        "save", "Il primo checkpoint di questo topic.",
        "--topic", "test/nuovo",
    ])
    assert r.exit_code == 0, r.output
    assert "supersed" not in r.output.lower()
