"""TDD for benchmark/sycophancy_mem — two-sided memory-sycophancy (Ph3)."""
from __future__ import annotations

from benchmark.sycophancy_mem import run, run_both


def test_gate_off_caves_to_bare_assertions() -> None:
    # without the gate, a more-recent, more-confident BARE claim supersedes the truth
    assert run(require_evidence=False)["cave_rate"] > 0.5


def test_gate_on_drives_cave_to_zero() -> None:
    assert run(require_evidence=True)["cave_rate"] == 0.0


def test_evidenced_corrections_never_blocked() -> None:
    # the gate must NOT over-rigidify: legitimate EVIDENCED corrections still apply
    assert run(require_evidence=False)["false_rigidity"] == 0.0
    assert run(require_evidence=True)["false_rigidity"] == 0.0


def test_clean_two_sided_win() -> None:
    out = run_both()
    assert out["clean_win"] is True
    assert out["gate_on"]["cave_rate"] < out["gate_off"]["cave_rate"]
    assert out["gate_on"]["false_rigidity"] <= out["gate_off"]["false_rigidity"]
