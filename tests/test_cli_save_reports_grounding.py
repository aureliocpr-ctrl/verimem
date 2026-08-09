"""`verimem save` must say whether the moat judged the write.

`save` is the canonical way an agent records its work, and its receipt printed
the disposition, the id and the lineage — nothing about grounding. So a
checkpoint written WITHOUT a source (the moat cannot run: there is nothing to
check the fact against) looked exactly like one the moat had judged and passed.

That silence has a measured cost. On the real corpus, 2026-07-28:

    6414 facts, 0 with a grounding_score
    42 of 42 written in the previous 24h, none judged

The write path was never broken — `--source` exists and works: the same
checkpoint scores 99.9 with it and null without. What was missing is that
nothing ever told the operator which of the two they had just done.

Same discipline the gate already applies to its own L4-skipped advisory ("say
so out loud, NEVER a silent skip"), on the surface most people actually type.
"""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()


def test_save_without_source_says_the_moat_did_not_run(
        isolated_corpus: Path) -> None:
    r = runner.invoke(app, ["save", "Closed the read-path cycle this evening.",
                            "--topic", "session/dogfood"])
    assert r.exit_code == 0, r.output
    low = r.output.lower()
    assert "not verified" in low or "no source" in low, (
        f"the receipt must say the entailment check did not run:\n{r.output}")


def test_save_with_source_reports_the_verdict(isolated_corpus: Path) -> None:
    r = runner.invoke(app, [
        "save", "Rex is a labrador.", "--topic", "session/dogfood",
        "--source", "The kennel registry lists Rex as a labrador.",
    ])
    assert r.exit_code == 0, r.output
    low = r.output.lower()
    assert "grounded" in low or "entail" in low, (
        f"a judged write must report its verdict:\n{r.output}")


def test_the_json_receipt_is_unchanged(isolated_corpus: Path) -> None:
    """--json is a machine contract: the new line is for humans only."""
    import json
    r = runner.invoke(app, ["save", "A plain checkpoint.", "--topic",
                            "session/dogfood", "--json"])
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output.strip().splitlines()[-1])
    assert payload["stored"] is True
    assert "grounding_score" in payload
