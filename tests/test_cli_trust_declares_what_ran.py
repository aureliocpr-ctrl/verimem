"""`verimem trust` called an invention "adequate evidence".

Measured 2026-07-29. The claim

    "il modulo di fatturazione di verimem usa PostgreSQL con sharding su otto
     nodi e ha superato la certificazione ISO 27001 nel marzo 2026"

— a module that does not exist, with a fabricated certification — returned:

    Anti-confab trust check   TRUSTED ✓
      provenance:  (none)
      no anti-confab flags — adequate evidence / not a risky assertion

The verdict is not wrong: the handler calls run_validation_gate with agent=None
and no source, so only the L1 lexical screens can run, and they found no hype
words. What is wrong is the sentence. "Adequate evidence" was printed by a check
that looked at NO evidence: L3 needs the corpus, L4 needs a source, and the
command had no way to pass one — `--source` did not exist.

So this does not change any verdict. It makes the command say which layers ran,
the same way build_trust_report already reports `verify: {ce_gate, sufficiency}`
instead of letting an unfiltered result look like a filtered one. And it adds
the argument that lets the moat — the product's headline check — actually run
from the command named after trust.
"""
from __future__ import annotations

import re

from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()

INVENZIONE = ("il modulo di fatturazione di verimem usa PostgreSQL con "
              "sharding su otto nodi")


def test_it_does_not_call_an_unchecked_claim_adequate_evidence():
    r = runner.invoke(app, ["trust", INVENZIONE])
    assert "adequate evidence" not in r.output.lower(), (
        "printed 'adequate evidence' for a claim whose evidence was never "
        f"looked at:\n{r.output}"
    )


def test_it_says_which_layers_actually_ran():
    """A reader must be able to tell a lexical-only pass from a full one."""
    r = runner.invoke(app, ["trust", INVENZIONE])
    out = r.output.lower()
    assert "checked" in out or "screens" in out, (
        f"nothing in the output says what was checked:\n{r.output}"
    )
    # the moat cannot have run: no source was given
    assert "moat" in out or "source" in out, (
        f"the output never mentions the check that did NOT run:\n{r.output}"
    )


def test_the_command_named_after_trust_can_run_the_moat():
    """--source did not exist, so the headline check was unreachable from the
    command that advertises it."""
    r = runner.invoke(app, ["trust", "--help"])
    # L'help e' reso da rich, che COLORA le opzioni: `--source` esce come
    # `\x1b[1;36m-\x1b[0m\x1b[1;36m-source\x1b[0m`, cioe' i due trattini sono
    # separati da una sequenza ANSI e la stringa letterale non c'e' piu'.
    # Il test passava su Windows (niente colore) e cadeva su ubuntu e macos in
    # CI, dove il colore c'e' — sempre con l'opzione REGOLARMENTE PRESENTE
    # nell'help. Il difetto era nel modo di guardare, non in cio' che si
    # guardava: si toglie il colore PRIMA di cercare, cosi' il test misura
    # l'help e non il terminale che lo stampa.
    nudo = re.sub(r"\x1b\[[0-9;]*m", "", r.output)
    assert "--source" in nudo, (
        f"no way to give the moat something to check:\n{nudo}"
    )


def test_a_claim_with_no_provenance_still_reports_that():
    """Regression guard on the line that was already right."""
    r = runner.invoke(app, ["trust", INVENZIONE])
    assert "(none)" in r.output
