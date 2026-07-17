"""TDD — classify_episodes.failure_recovery order-independent (scan 68-Opus P2).
Bug: il flag era calcolato in SINGLE pass (il commento dice 'First pass: build
a map' ma non c'e' seconda pass) -> scattava solo se la failure precedeva il
success nell'ordine d'iterazione. Il caller usa memory.all() = ORDER BY
created_at DESC (newest-first) -> il success (piu' recente) e' iterato PRIMA
della sua failure precedente -> prior_failure ancora vuoto -> flag MORTO.
Fix: true two-pass (pass 1 raccoglie i task con failure, pass 2 flagga i
success). Test HERMETIC (funzione pura, no DB)."""
from __future__ import annotations

from dataclasses import dataclass, field

from verimem.episode_classify import classify_episodes


@dataclass
class _Ep:
    id: str
    outcome: str
    task_text: str = ""
    final_answer: str = "task completed successfully"
    skills_used: list = field(default_factory=lambda: ["s1"])
    tokens_used: int = 0


def test_failure_recovery_fires_newest_first_order():
    # ordine come memory.all(): success piu' recente PRIMA, poi failure vecchia
    eps = [
        _Ep("e2", "success", task_text="taskX"),
        _Ep("e1", "failure", task_text="taskX"),
    ]
    out = classify_episodes(eps)
    rec = next(r for r in out["episodes"] if r["id"] == "e2")
    assert "failure_recovery" in rec["flags"], (
        "il success di un task con failure deve essere flaggato "
        "failure_recovery indipendentemente dall'ordine d'iterazione")
    assert out["flag_counts"].get("failure_recovery", 0) == 1


def test_failure_recovery_still_works_oldest_first_order():
    # ordine inverso: deve restare corretto
    eps = [
        _Ep("e1", "failure", task_text="taskY"),
        _Ep("e2", "success", task_text="taskY"),
    ]
    out = classify_episodes(eps)
    rec = next(r for r in out["episodes"] if r["id"] == "e2")
    assert "failure_recovery" in rec["flags"]


def test_no_failure_recovery_when_task_never_failed():
    eps = [
        _Ep("e2", "success", task_text="taskZ"),
        _Ep("e1", "success", task_text="taskZ"),
    ]
    out = classify_episodes(eps)
    assert out["flag_counts"].get("failure_recovery", 0) == 0
