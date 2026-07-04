"""TDD for benchmark/justified_belief_bench — the JBI experiment (new axis)."""
from __future__ import annotations

from benchmark.justified_belief_bench import run, run_transitive


def test_tms_beats_naive_on_jbi() -> None:
    r = run(24)
    assert r["tms_store"]["jbi"] > r["naive_store"]["jbi"]
    assert r["jbi_gain"] > 0.0
    assert r["H_JM1_holds"] is True


def test_tms_preserves_valid_recall() -> None:
    r = run(24)
    assert r["valid_recall_preserved"] is True
    assert r["tms_store"]["valid_recall"] == 1.0  # TMS does not over-retract valid facts


def test_naive_serves_falsehoods_tms_does_not() -> None:
    r = run(24)
    assert r["naive_store"]["stale_served"] > 0
    assert r["naive_store"]["contradiction_served"] > 0
    assert r["naive_store"]["superseded_served"] > 0
    assert r["tms_store"]["stale_served"] == 0.0
    assert r["tms_store"]["contradiction_served"] == 0.0
    assert r["tms_store"]["superseded_served"] == 0.0


def test_propagate_beats_supersession_only_on_chains() -> None:
    # the novel core: maintain/supersede alone keeps facts derived from a retracted
    # foundation; ATMS propagate cascades the retraction -> strictly higher JBI
    t = run_transitive()
    assert t["propagate_jbi"] > t["maintain_only_jbi"]
    assert t["propagate_jbi"] == 1.0
    assert t["cascade_retracted"] == ["D1", "D2", "D3"]
    assert "D1" in t["maintain_only_served"]  # supersession-only leaks the derived facts
