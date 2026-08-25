"""G4 (RELEASE_GATE): every published number keeps BOTH its evidence and its recipe.

cmd_verify() == 0 is a standing guard: if a results artifact referenced by a
published number disappears (or its key path breaks), the SUITE fails — a
claim can then only survive by re-running its benchmark or removing it from
the docs. This is the anti-"numbers drift from evidence" lock.

Since 2026-08-25 cmd_verify() also fails when the module a command names does
not exist: G4 promises the number is *regenerable*, and an artifact on disk
does not make it so. See tests/test_la_ricetta_del_numero_deve_esistere.py,
which names the offending entry instead of only flipping the exit code.
"""
from __future__ import annotations

from benchmark.repro_all import REGISTRY, cmd_verify


def test_registry_entries_well_formed() -> None:
    for k, e in REGISTRY.items():
        assert e["claim"] and e["artifact"] and e["command"], k
        assert e["cost"] in ("local", "claude-p"), k
        assert isinstance(e["value_at"], list), f"{k}: value_at must be a key LIST"


def test_every_claim_backed_by_artifact_and_regenerable() -> None:
    assert cmd_verify() == 0, (
        "a published number lost its evidence (artifact) or its recipe "
        "(the module its command names): run `python -m benchmark.repro_all "
        "--verify` -- it prints both counts and names the entry"
    )
