"""FORGIA pezzo #82 — `WakeResult.used_macro` flag tests.

The flag tells callers whether the wake loop took the procedural
fast-path or fell through to the full ReAct loop. This test pins
the contract:

  1. Default value is False (a fresh agent has no macros).
  2. The flag survives via_dict round-trip (kept as part of the
     stable API).
"""
from __future__ import annotations

from dataclasses import asdict, fields

from engram.wake import WakeResult


def test_used_macro_defaults_to_false():
    """A fresh agent never has macros; default must be False."""
    # Build a minimal WakeResult — most fields can be defaults.
    wr = WakeResult(
        episode=None,  # type: ignore[arg-type]
        success=True,
        message="ok",
    )
    assert wr.used_macro is False


def test_used_macro_is_documented_on_dataclass():
    """`used_macro` must be a declared field, not a runtime hack."""
    field_names = {f.name for f in fields(WakeResult)}
    assert "used_macro" in field_names


def test_used_macro_serialises_via_asdict():
    """asdict() roundtrip preserves used_macro."""
    wr = WakeResult(
        episode=None,  # type: ignore[arg-type]
        success=True,
        message="hit",
        used_macro=True,
    )
    d = asdict(wr)
    assert d["used_macro"] is True
