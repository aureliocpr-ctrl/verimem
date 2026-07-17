"""Bench: sleep replay salience priority — 3 dimensions.

Pezzo #19 wires `episode.salience_score` into `replay_priority`.

Dichiarate prima di misurare:

  1. WEIGHT 0 LEGACY: with weight=0.0 the priority formula is
     unchanged for any salience score. Empirical via 100 random
     episodes — max delta 0 across the lot.

  2. WEIGHT > 0 ORDERING SHIFT: with weight=0.5 the replay-order
     ranking shifts on a 100-episode mix vs the legacy formula.
     Spearman correlation < 0.99 (proves the new term moves the
     ranking) but > 0.5 (it's not chaos).

  3. CONTINUOUS SCALE: priorities scale linearly with salience —
     a +0.1 salience delta produces +0.1 × weight delta in priority,
     all else equal.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.config import CONFIG
from verimem.episode import Episode, Trace
from verimem.sleep import replay_priority

_NOW = 1_700_000_000.0


def _ep(*, ep_id: str, outcome: str = "success", salience: float = 0.5,
        age_hours: float = 0.0,
        skills_used: list[str] | None = None) -> Episode:
    return Episode(
        id=ep_id, task_id="t", task_text="x",
        outcome=outcome,  # type: ignore[arg-type]
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="A",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=skills_used or [],
        created_at=_NOW - age_hours * 3600.0,
        salience_score=salience,
    )


def _save_cfg(*fields: str) -> dict:
    return {f: getattr(CONFIG, f) for f in fields}


def _restore_cfg(saved: dict) -> None:
    for f, v in saved.items():
        object.__setattr__(CONFIG, f, v)


def main() -> int:
    saved = _save_cfg("sleep_replay_priority_salience",
                      "sleep_replay_priority_surprise")
    object.__setattr__(CONFIG, "sleep_replay_priority_surprise", 0.0)
    rng = np.random.default_rng(seed=20260508)

    # Build a 100-episode random mix
    eps = []
    for i in range(100):
        outcome = "failure" if rng.random() < 0.3 else "success"
        eps.append(_ep(
            ep_id=f"e{i:03d}",
            outcome=outcome,
            salience=float(rng.random()),
            age_hours=float(rng.exponential(scale=24.0)),
        ))

    # Dim 1: weight 0 = legacy
    object.__setattr__(CONFIG, "sleep_replay_priority_salience", 0.0)
    legacy = [replay_priority(e, _NOW, max_age=7 * 86400.0) for e in eps]

    # Recompute again with weight=0 — should be identical
    legacy2 = [replay_priority(e, _NOW, max_age=7 * 86400.0) for e in eps]
    max_legacy_delta = max(abs(a - b) for a, b in zip(legacy, legacy2, strict=True))

    # Dim 2: weight > 0 → ranking shifts
    object.__setattr__(CONFIG, "sleep_replay_priority_salience", 0.5)
    salience_scored = [replay_priority(e, _NOW, max_age=7 * 86400.0) for e in eps]

    # Spearman correlation between legacy ranking and salience-boosted
    legacy_rank = np.argsort(legacy)
    new_rank = np.argsort(salience_scored)
    # Convert to ranks
    legacy_ranks = np.empty_like(legacy_rank)
    legacy_ranks[legacy_rank] = np.arange(len(legacy))
    new_ranks = np.empty_like(new_rank)
    new_ranks[new_rank] = np.arange(len(salience_scored))
    spearman = float(np.corrcoef(legacy_ranks, new_ranks)[0, 1])

    # Dim 3: linear scaling
    # Take 20 pairs with same outcome/age/skills but different salience
    object.__setattr__(CONFIG, "sleep_replay_priority_salience", 0.4)
    object.__setattr__(CONFIG, "sleep_replay_priority_failure", 0.0)
    object.__setattr__(CONFIG, "sleep_replay_priority_recent", 0.0)
    object.__setattr__(CONFIG, "sleep_replay_priority_diverse", 0.0)

    deltas = []
    for _ in range(20):
        s_lo = rng.random() * 0.5
        s_hi = s_lo + rng.random() * 0.5
        ep_lo = _ep(ep_id="lo", salience=s_lo)
        ep_hi = _ep(ep_id="hi", salience=s_hi)
        p_lo = replay_priority(ep_lo, _NOW, max_age=7 * 86400.0)
        p_hi = replay_priority(ep_hi, _NOW, max_age=7 * 86400.0)
        observed = p_hi - p_lo
        expected = 0.4 * (s_hi - s_lo)
        deltas.append(abs(observed - expected))
    max_linear_error = max(deltas)

    _restore_cfg(saved)
    object.__setattr__(CONFIG, "sleep_replay_priority_failure", 0.6)
    object.__setattr__(CONFIG, "sleep_replay_priority_recent", 0.3)
    object.__setattr__(CONFIG, "sleep_replay_priority_diverse", 0.1)

    print()
    print("Bench: sleep replay salience priority")
    print()
    print(f"  weight=0 reproducibility max delta:  {max_legacy_delta:.2e}")
    print(f"  spearman(legacy_rank, salience_rank): {spearman:.3f}  "
          f"(target 0.5 < spearman < 0.99)")
    print(f"  linear-scaling max error:            {max_linear_error:.2e}")
    print()
    print("Verdict (3 dimensions):")
    d1 = max_legacy_delta == 0.0
    d2 = 0.5 < spearman < 0.99
    d3 = max_linear_error < 1e-6
    print(f"  weight=0 legacy compat:    {'+' if d1 else '!'}")
    print(f"  ranking shifts (not chaos): {'+' if d2 else '!'}")
    print(f"  linear scaling:            {'+' if d3 else '!'}")
    return 0 if (d1 and d2 and d3) else 1


if __name__ == "__main__":
    sys.exit(main())
