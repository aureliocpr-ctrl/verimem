"""`facts add --jsonl-stdin` must not crash a whole batch on confidence:null.

Scan low #28: a JSONL record with ``"confidence": null`` hit
``float(p.get("confidence", confidence))`` — get() returns None for a
PRESENT null key (the default is only used for a MISSING key), so
float(None) raised TypeError. That exception was outside the per-record
try, so ONE bad record aborted the whole import, dropping every valid
record after it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from verimem.cli import app
from verimem.semantic import SemanticMemory

runner = CliRunner()


def _db(tmp_path: Path) -> Path:
    return tmp_path / "semantic" / "semantic.db"


def test_jsonl_null_confidence_does_not_abort_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    (tmp_path / "semantic").mkdir(parents=True, exist_ok=True)

    lines = [
        {"proposition": "first valid fact about alpha region",
         "topic": "ops", "status": "model_claim"},
        {"proposition": "second fact with explicit null confidence here",
         "topic": "ops", "status": "model_claim", "confidence": None},
        {"proposition": "third valid fact about gamma region",
         "topic": "ops", "status": "model_claim"},
    ]
    stdin = "\n".join(json.dumps(o) for o in lines) + "\n"

    r = runner.invoke(app, ["facts", "add", "--jsonl-stdin"], input=stdin)
    assert r.exit_code == 0, r.output

    sm = SemanticMemory(db_path=_db(tmp_path))
    props = {f.proposition for f in sm.all()}
    # The null-confidence record must NOT take the two valid ones down with it.
    assert any("alpha region" in p for p in props), r.output
    assert any("gamma region" in p for p in props), r.output
    # The null record itself should persist with the default confidence,
    # not crash and not silently vanish.
    assert any("explicit null confidence" in p for p in props), r.output
    null_fact = next(f for f in sm.all()
                     if "explicit null confidence" in f.proposition)
    assert 0.0 <= null_fact.confidence <= 1.0
