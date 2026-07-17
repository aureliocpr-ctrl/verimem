"""TDD — e2e_cycle51_54_chain.main() non deve toccare il corpus REALE senza
opt-in esplicito (scan 68-Opus medium [46], conf 0.95).
Bug: lo script (NON raccolto da pytest, gira via __main__ sul corpus reale per
design) faceva insert+delete su ~/.engram; un run accidentale o un crash a
meta inquinava la produzione. Fix: guard HIPPO_ALLOW_REAL_E2E=1 -> senza, main()
ritorna 0 SENZA costruire memoria/DB. Test HERMETIC (monkeypatch + spy)."""
from __future__ import annotations

import importlib


def test_main_skips_without_optin_and_touches_nothing(monkeypatch):
    m = importlib.import_module("tests.perf.e2e_cycle51_54_chain")
    spy = {"mem": 0}

    class FakeMem:
        def __init__(self):
            spy["mem"] += 1

        def all(self):
            return []

    monkeypatch.delenv("HIPPO_ALLOW_REAL_E2E", raising=False)
    monkeypatch.setattr("verimem.memory.EpisodicMemory", FakeMem)

    rc = m.main()

    assert rc == 0, "senza opt-in main() deve uscire pulito (skip), non fallire"
    assert spy["mem"] == 0, (
        "senza HIPPO_ALLOW_REAL_E2E=1 NON deve costruire EpisodicMemory "
        "(zero contatto col corpus reale)")
