"""TDD — HolographicMemory.forget non deve corrompere l'aggregate se il fatto NON esiste
(scan 68-Opus 2026-06-02). Bug: forget() faceva `self.aggregate -= bound` PRIMA del check
di esistenza (cleanup_pool.remove) -> un forget di un fatto mai memorizzato sottraeva un
bound mai aggiunto -> drift permanente dello stato HRR. Test HERMETIC (in-memory, no DB)."""
from __future__ import annotations

from verimem.holographic_memory import HolographicMemory


def test_forget_nonexistent_does_not_corrupt_aggregate():
    mem = HolographicMemory(d=4096)
    mem.remember("t1", "real proposition one content")
    norm_before = mem.stats()["aggregate_norm"]
    n_before = mem.stats()["n_facts"]
    res = mem.forget("ghost_topic", "mai memorizzata proposition")
    assert res["ok"] is False, f"forget di fatto inesistente deve fallire: {res}"
    assert mem.stats()["aggregate_norm"] == norm_before, (
        f"aggregate CORROTTO da un forget fallito: {norm_before} -> {mem.stats()['aggregate_norm']}")
    assert mem.stats()["n_facts"] == n_before


def test_forget_existing_still_works():
    mem = HolographicMemory(d=4096)
    mem.remember("t1", "real proposition one content")
    mem.remember("t2", "real proposition two content")
    res = mem.forget("t1", "real proposition one content")
    assert res["ok"] is True, f"forget di fatto reale deve riuscire: {res}"
    assert mem.stats()["n_facts"] == 1
