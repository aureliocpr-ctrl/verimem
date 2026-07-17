"""FORGIA pezzo #238 — Wave 37: decay-prune simulation.

Read-only preview: which episodes WOULD be pruned by the next
consolidate_light cycle? Helps the user decide whether to pin
something before it disappears.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _FakeEp:
    id: str
    task_text: str = ""
    outcome: str = "success"
    salience_score: float = 0.0
    pinned: bool = False
    skills_used: list[str] = field(default_factory=list)


class _FakeMemory:
    def __init__(self, eps: list[_FakeEp]) -> None:
        self._eps = eps

    def decay_pruning_candidates(self, *, retention_threshold: float = 0.30,
                                 tau_base_s: float | None = None,
                                 limit: int | None = None) -> list[_FakeEp]:
        # Firma ALLINEATA a EpisodicMemory.decay_pruning_candidates. Prima era
        # `top_k` (drift) e mascherava il bug d'integrazione: decay_simulate
        # chiamava top_k= ma la firma reale vuole limit= -> TypeError -> [].
        active = [e for e in self._eps if not e.pinned]
        ordered = sorted(active, key=lambda e: e.salience_score)
        return ordered[:limit] if limit is not None else ordered


class _FakeAgent:
    def __init__(self, eps: list[_FakeEp]) -> None:
        self.memory = _FakeMemory(eps)


def test_empty_no_candidates():
    from verimem.decay_simulate import decay_simulate

    out = decay_simulate(agent=_FakeAgent([]))
    assert out["candidates"] == []
    assert out["n_total"] == 0


def test_excludes_pinned():
    from verimem.decay_simulate import decay_simulate

    eps = [
        _FakeEp("safe", pinned=True, salience_score=0.01),
        _FakeEp("doomed", pinned=False, salience_score=0.01),
    ]
    out = decay_simulate(agent=_FakeAgent(eps))
    ids = [c["id"] for c in out["candidates"]]
    assert "doomed" in ids
    assert "safe" not in ids


def test_sorted_by_salience_asc():
    """Lowest salience first (closest to pruning)."""
    from verimem.decay_simulate import decay_simulate

    eps = [
        _FakeEp("mid", salience_score=0.5),
        _FakeEp("low", salience_score=0.1),
        _FakeEp("high", salience_score=0.9),
    ]
    out = decay_simulate(agent=_FakeAgent(eps))
    saliences = [c["salience_score"] for c in out["candidates"]]
    assert saliences == sorted(saliences)


def test_top_k_respected():
    from verimem.decay_simulate import decay_simulate

    eps = [_FakeEp(f"e{i}", salience_score=i / 100.0) for i in range(10)]
    out = decay_simulate(agent=_FakeAgent(eps), top_k=3)
    assert len(out["candidates"]) == 3


def test_payload_shape_complete():
    from verimem.decay_simulate import decay_simulate

    out = decay_simulate(agent=_FakeAgent([]))
    for k in ("candidates", "n_total", "top_k"):
        assert k in out
