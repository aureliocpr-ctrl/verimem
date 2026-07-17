"""audit#3-r3 R6: ``engram facts add`` must exit NON-ZERO when it persisted
nothing — e.g. a bulk ``--jsonl-stdin`` import where every line was malformed
(or every payload got rejected/skipped).

Pre-fix it printed a yellow "no facts inserted" note and returned normally
(exit 0), so a pipeline like ``cat findings.jsonl | engram facts add
--jsonl-stdin`` could not distinguish an all-dropped import from a successful
one.
"""
from __future__ import annotations

from typer.testing import CliRunner

from verimem.cli import facts_app


def _iso_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))


def test_facts_add_jsonl_all_malformed_exits_nonzero(tmp_path, monkeypatch):
    _iso_env(tmp_path, monkeypatch)
    runner = CliRunner()
    bad = 'this is not json\n{also not: valid}\n{"oops"\n'
    result = runner.invoke(facts_app, ["add", "--jsonl-stdin"], input=bad)
    assert result.exit_code == 1, (
        f"all-malformed jsonl import must exit 1, got {result.exit_code}\n"
        f"{result.output}"
    )


def test_facts_add_valid_flag_still_exits_zero(tmp_path, monkeypatch):
    """The guard must NOT regress the happy path: a real insert exits 0."""
    _iso_env(tmp_path, monkeypatch)
    runner = CliRunner()
    result = runner.invoke(
        facts_app,
        [
            "add",
            "-p", "the box runs nginx 1.24 on port 443",
            "-t", "proj/x",
            "--validate", "off",
        ],
    )
    assert result.exit_code == 0, result.output
