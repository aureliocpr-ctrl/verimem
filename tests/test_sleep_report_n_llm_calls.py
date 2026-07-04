"""FORGIA pezzo #83 — `SleepReport.n_llm_calls` field tests.

Pins the contract:
  1. Default is 0 (a no-op cycle reports zero calls).
  2. Field is declared on the dataclass (not a runtime hack).
  3. asdict() roundtrip preserves n_llm_calls.
"""
from __future__ import annotations

from dataclasses import asdict, fields

from engram.sleep import SleepReport


def test_n_llm_calls_default_zero():
    r = SleepReport()
    assert r.n_llm_calls == 0


def test_n_llm_calls_declared_field():
    field_names = {f.name for f in fields(SleepReport)}
    assert "n_llm_calls" in field_names


def test_n_llm_calls_serialises():
    r = SleepReport(n_llm_calls=7, tokens_used=1234)
    d = asdict(r)
    assert d["n_llm_calls"] == 7
    assert d["tokens_used"] == 1234
