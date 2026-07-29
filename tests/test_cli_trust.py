"""`engram trust <claim>` — the anti-confab governance moat made demonstrable.

Flags unsupported hype and explains WHY (which L1 detector fired); a benign
fact passes; real provenance clears the relevant detector. Exit 0 = trusted,
1 = flagged. (validate=fast -> L1 only, no agent needed.)
"""
from __future__ import annotations

from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()


def test_trust_flags_hype_with_reasons():
    r = runner.invoke(app, ["trust", "This module is production-ready and fully tested"])
    assert r.exit_code == 1, r.output
    assert "FLAGGED" in r.output or "QUARANTINED" in r.output
    assert "L1.11" in r.output  # the production-ready detector is named in the "why"


def test_trust_accepts_benign_fact():
    """Passes, and says what that means.

    2026-07-29: the verdict used to read "TRUSTED ✓" here. Without a --source
    the only layer that CAN run is the L1 lexical screen, so the tick was
    reporting "no hype words" as if it were verification — an invented module
    with a fabricated ISO 27001 date earned the same green TRUSTED. The
    disposition is unchanged (exit 0, the gate would store it); the label now
    matches the check that produced it.
    """
    r = runner.invoke(app, ["trust", "The capital of France is Paris"])
    assert r.exit_code == 0, r.output
    assert "NO FLAGS" in r.output, r.output
    assert "TRUSTED" not in r.output, (
        "a lexical-only pass must not claim the word the moat earns"
    )


def test_trust_evidence_clears_tested_claim():
    r = runner.invoke(
        app, ["trust", "The auth module is tested", "--verified-by", "pytest:auth_PASS"],
    )
    assert r.exit_code == 0, r.output  # the pytest PASS ref clears L1.15


def test_trust_json_emits_action():
    r = runner.invoke(app, ["trust", "Everything is fully tested", "--json"])
    assert "action" in r.output
