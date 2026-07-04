"""G4 (RELEASE_GATE): the claims registry must stay backed by artifacts.

cmd_verify() == 0 is a standing guard: if a results artifact referenced by a
published number disappears (or its key path breaks), the SUITE fails — a
claim can then only survive by re-running its benchmark or removing it from
the docs. This is the anti-"numbers drift from evidence" lock.
"""
from __future__ import annotations

from benchmark.repro_all import REGISTRY, cmd_verify


def test_registry_entries_well_formed() -> None:
    for k, e in REGISTRY.items():
        assert e["claim"] and e["artifact"] and e["command"], k
        assert e["cost"] in ("local", "claude-p"), k
        assert isinstance(e["value_at"], list), f"{k}: value_at must be a key LIST"


def test_every_claim_backed_by_artifact() -> None:
    assert cmd_verify() == 0
