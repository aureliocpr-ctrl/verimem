"""Unit tests for cycle #76 L2 dedup helpers.

The cleanup script delegates two decisions to pure helpers:
  - is_pure_pollution_cluster(propositions) — are these all the same
    short boilerplate?
  - pick_representative(facts) — among knowledge duplicates, which
    one survives?

These tests pin the contract. RED before GREEN (helpers ship with
the script — the test must FAIL until the script defines them).
"""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

# Load the script module dynamically so tests don't depend on it being
# on PYTHONPATH.
_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "cycle76_cleanup_l2_duplicates.py"
_spec = importlib.util.spec_from_file_location("cycle76_dedup", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["cycle76_dedup"] = _mod
_spec.loader.exec_module(_mod)


@dataclass
class _Fact:
    id: str = "x"
    proposition: str = ""
    topic: str = ""
    confidence: float = 0.5
    source_episodes: list[str] = field(default_factory=list)
    created_at: float = 0.0


# ---------------------------------------------------------------------------
# is_pure_pollution_cluster
# ---------------------------------------------------------------------------

class TestIsPurePollutionCluster:
    def test_identical_short_boilerplate(self):
        # Real corpus case: "Stub rationale for bench" x18
        props = ["Stub rationale for bench"] * 18
        assert _mod.is_pure_pollution_cluster(props) is True

    def test_identical_short_endpoint_pattern(self):
        props = ["consistent endpoint pattern"] * 6
        assert _mod.is_pure_pollution_cluster(props) is True

    def test_long_propositions_not_pollution(self):
        # Real knowledge dup — 80+ chars each, not pure
        long = "Real knowledge fact with enough detail to carry information across rebuilds X"
        assert len(long) >= 50
        assert _mod.is_pure_pollution_cluster([long, long]) is False

    def test_paraphrased_short_not_pollution(self):
        # Two short propositions but DIFFERENT — could be legit
        assert _mod.is_pure_pollution_cluster(["alpha v1", "alpha v2"]) is False

    def test_empty_input(self):
        assert _mod.is_pure_pollution_cluster([]) is False

    def test_single_short_still_pollution(self):
        # Technically a 1-cluster is degenerate but the helper should
        # report True if the lone proposition is short boilerplate.
        assert _mod.is_pure_pollution_cluster(["x"]) is True


# ---------------------------------------------------------------------------
# pick_representative
# ---------------------------------------------------------------------------

class TestPickRepresentative:
    def test_prefers_higher_confidence(self):
        a = _Fact(id="a", confidence=0.5, proposition="x")
        b = _Fact(id="b", confidence=0.9, proposition="x")
        assert _mod.pick_representative([a, b]).id == "b"

    def test_tiebreak_longer_proposition(self):
        a = _Fact(id="a", confidence=0.9, proposition="short")
        b = _Fact(id="b", confidence=0.9, proposition="much longer with more detail")
        assert _mod.pick_representative([a, b]).id == "b"

    def test_tiebreak_oldest_created_at(self):
        a = _Fact(id="a", confidence=0.9, proposition="same", created_at=200.0)
        b = _Fact(id="b", confidence=0.9, proposition="same", created_at=100.0)
        # b is older — keep it
        assert _mod.pick_representative([a, b]).id == "b"

    def test_single_fact(self):
        a = _Fact(id="solo", confidence=0.5)
        assert _mod.pick_representative([a]).id == "solo"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _mod.pick_representative([])
