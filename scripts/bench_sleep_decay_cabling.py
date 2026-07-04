"""Bench: cabling decay_prune into sleep cycle — end-to-end memory bound.

Pezzo #9 is a CABLING, not a new primitive. The value is in showing that
after wiring `decay_prune` into the sleep loop, the memory corpus stays
bounded across many cycles instead of growing monotonically.

Three dimensions declared BEFORE measuring:

  1. UNBOUNDED GROWTH (legacy):
     With decay disabled, after N sleep cycles the corpus equals the
     total episodes ever stored. This is the bug.

  2. BOUNDED CORPUS (ferrari):
     With decay enabled, after the same N cycles the corpus stays
     within a steady-state band. The hot episodes survive, the
     ancient ones fade out.

  3. RECALL QUALITY HOLDS:
     Even after aggressive decay, top-k recall on a "live" query
     (one related to the hot episodes) returns the hot episodes —
     the system learns and forgets, but doesn't forget what it's
     using right now.
"""
from __future__ import annotations

import dataclasses
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram import config as config_mod
from engram.config import CONFIG
from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory
from engram.skill import SkillLibrary
from engram.sleep import SleepEngine, SleepReport


@dataclass
class BenchOutcome:
    label: str
    final_count: int
    peak_count: int
    hot_recall_share: float


def _patch(**fields) -> None:
    """Direct CONFIG rebind across the modules that imported it.

    The bench drives the engine directly so we don't bother with
    pytest monkeypatch — manual patch + restore at the end.
    """
    new = dataclasses.replace(CONFIG, **fields)
    config_mod.CONFIG = new
    from engram import memory as memory_mod
    from engram import sleep as sleep_mod
    memory_mod.CONFIG = new
    sleep_mod.CONFIG = new


def _store_random_old(mem: EpisodicMemory, n: int, base_age_days: float):
    """Store `n` ancient unrelated episodes — all should decay."""
    for i in range(n):
        mem.store(Episode(
            id=f"old_{int(time.time()*1000)}_{i}",
            task_id="t",
            task_text=f"old random task {i} unrelated to anything live",
            outcome="success", final_answer="ok",
            created_at=time.time() - base_age_days * 86400 - i * 60,
            traces=[Trace(
                step=1, thought="x", action="x", action_input="{}",
                observation="x",
            )],
        ))


def _store_hot(mem: EpisodicMemory, n: int):
    """Store `n` fresh, frequently-used episodes — should survive."""
    for i in range(n):
        ep = Episode(
            id=f"hot_{int(time.time()*1000)}_{i}",
            task_id="t",
            task_text=f"live task fix calc.py arithmetic {i}",
            outcome="success", final_answer="ok",
            created_at=time.time() - 2.0,
            last_accessed_at=time.time() - 1.0,
            access_count=5,
            salience_score=0.7,
            traces=[Trace(
                step=1, thought="x", action="x", action_input="{}",
                observation="x",
            )],
        )
        mem.store(ep)


def _evaluate(label: str, decay_enabled: bool, *, n_cycles: int = 6) -> BenchOutcome:
    _patch(
        episode_decay_enabled=decay_enabled,
        episode_decay_threshold=0.30,
        episode_decay_max_per_cycle=200,
        sleep_min_episodes=2,
    )
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        skills = SkillLibrary(
            dir_path=root / "skills_dir", db_path=root / "sk.db",
        )
        mem = EpisodicMemory(db_path=root / "ep.db")
        sem = SemanticMemory(db_path=root / "sm.db")
        engine = SleepEngine(
            memory=mem, skills=skills, semantic=sem, llm=None, seed=42,
        )

        peak = 0
        # Each "day": store 50 old + 5 hot, then run the decay stage.
        for day in range(n_cycles):
            _store_random_old(mem, 50, base_age_days=90.0 + day * 5)
            _store_hot(mem, 5)
            peak = max(peak, mem.count())
            report = SleepReport()
            engine._stage_episode_decay(report)

        final = mem.count()

        # Hot recall: query for live tasks → are the hot episodes still there?
        results = mem.recall(
            "live task fix calc.py arithmetic 0", k=5, track_access=False,
        )
        hot_share = sum(
            1 for ep, _ in results if ep.id.startswith("hot_")
        ) / max(1, len(results))

    return BenchOutcome(
        label=label, final_count=final, peak_count=peak,
        hot_recall_share=hot_share,
    )


def main() -> int:
    legacy = _evaluate("legacy", decay_enabled=False)
    ferrari = _evaluate("ferrari", decay_enabled=True)

    print()
    print("Bench: sleep decay cabling — 6 simulated days, "
          "55 episodes/day stored")
    print()
    print(f"  legacy   final={legacy.final_count:>3}  "
          f"peak={legacy.peak_count:>3}  hot_recall={legacy.hot_recall_share:.2f}")
    print(f"  ferrari  final={ferrari.final_count:>3}  "
          f"peak={ferrari.peak_count:>3}  hot_recall={ferrari.hot_recall_share:.2f}")
    print()
    print("Verdict (3 dimensions, declared up front):")
    growth_ok = legacy.final_count >= 250  # legacy: at least 6*50=300 minus skipped, hits 300+
    bounded_ok = ferrari.final_count <= 100  # ferrari: ~30 hot survive
    hot_preserved = ferrari.hot_recall_share >= 0.5
    print(
        f"  legacy unbounded growth (>=250 final): "
        f"{legacy.final_count}  {'+' if growth_ok else '!'}"
    )
    print(
        f"  ferrari bounded (<=100 final): "
        f"{ferrari.final_count}  {'+' if bounded_ok else '!'}"
    )
    print(
        f"  hot recall preserved (>=0.5 share): "
        f"{ferrari.hot_recall_share:.2f}  "
        f"{'+' if hot_preserved else '!'}"
    )
    return 0 if (growth_ok and bounded_ok and hot_preserved) else 1


if __name__ == "__main__":
    sys.exit(main())
