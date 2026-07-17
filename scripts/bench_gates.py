"""Bench: macro / forward-replay gate — `mean` vs `lower_bound`.

Three dimensions declared BEFORE measuring (FORGIA discipline):

  1. OVER-CONFIDENCE CATCHES:
     skills the legacy mean-gate would fire on, but the Ferrari
     lower-bound gate correctly blocks. These are the "3/3
     successes ⇒ mean 0.80" trap cases — high mean masking thin
     evidence. Ferrari should catch some; if zero, the threshold
     pair is mis-tuned (or the legacy was already conservative).

  2. MATURE-SKILL RECALL (no false negatives):
     skills with lower_bound ≥ 0.65 (genuinely well-evidenced)
     should fire on BOTH gates. If Ferrari stops firing on
     a clearly mature skill, the threshold is too aggressive.

  3. DECISION BOUNDARY RATIONALITY:
     plot which (trials, successes) pairs trigger which gate.
     The Ferrari boundary should require MORE trials before
     the same mean fires — i.e. it bends with sample size.
     The legacy boundary should be flat at mean = threshold,
     ignoring sample size — that's exactly the pathology.

If catches > 0 AND mature_recall preserved AND boundary bends with
trials, the pezzo is forged.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.skill import Skill


@dataclass
class GateOutcome:
    name: str
    n_total_skills: int
    n_fires: int
    fired_ids: set[str]
    n_mature_recalled: int

    def render(self) -> str:
        return (
            f"  {self.name:<8}  fires={self.n_fires:>3}/{self.n_total_skills}  "
            f"mature_recalled={self.n_mature_recalled:>3}"
        )


def _make_population() -> list[Skill]:
    """Realistic library snapshot — varied evidence levels.

    The grid covers low-evidence high-mean traps (the failure mode
    pezzo #4 closes) and well-tested skills at every quality level.
    """
    pop: list[Skill] = []
    for trials in (1, 2, 3, 5, 10, 20, 40, 60):
        for successes_frac in (0.50, 0.70, 0.85, 1.00):
            successes = int(round(trials * successes_frac))
            pop.append(Skill(
                id=f"sk_{trials}_{successes}",
                name="x",
                trigger="x",
                body="x",
                trials=trials,
                successes=successes,
            ))
    return pop


def _eval_gate(
    skills: list[Skill],
    *,
    use_lower_bound: bool,
    threshold: float,
) -> GateOutcome:
    fired_ids: set[str] = set()
    n_mature_recalled = 0
    for s in skills:
        score = s.fitness_lower_bound if use_lower_bound else s.fitness_mean
        fired = score >= threshold
        if fired:
            fired_ids.add(s.id)
            if s.fitness_lower_bound >= 0.65:
                n_mature_recalled += 1
    return GateOutcome(
        name="ferrari" if use_lower_bound else "legacy",
        n_total_skills=len(skills),
        n_fires=len(fired_ids),
        fired_ids=fired_ids,
        n_mature_recalled=n_mature_recalled,
    )


def main() -> int:
    pop = _make_population()
    n_mature = sum(1 for s in pop if s.fitness_lower_bound >= 0.65)

    print()
    print(f"Population: {len(pop)} skills, {n_mature} mature (lower_bound >= 0.65)")
    print()
    print("--- Macro gate (compile_apply_min_*) ---")
    legacy = _eval_gate(pop, use_lower_bound=False, threshold=0.80)
    ferrari = _eval_gate(pop, use_lower_bound=True, threshold=0.65)
    print(legacy.render())
    print(ferrari.render())

    print()
    print("--- Forward-replay gate (forward_replay_min_*) ---")
    legacy_fr = _eval_gate(pop, use_lower_bound=False, threshold=0.50)
    ferrari_fr = _eval_gate(pop, use_lower_bound=True, threshold=0.30)
    print(legacy_fr.render())
    print(ferrari_fr.render())

    macro_catches = legacy.fired_ids - ferrari.fired_ids
    replay_catches = legacy_fr.fired_ids - ferrari_fr.fired_ids
    macro_false_neg = ferrari.fired_ids - legacy.fired_ids  # ferrari fires, legacy doesn't
    replay_false_neg = ferrari_fr.fired_ids - legacy_fr.fired_ids

    print()
    print("Verdict (3 dimensions, declared up front):")
    macro_ok = (
        len(macro_catches) > 0
        and ferrari.n_mature_recalled == legacy.n_mature_recalled
    )
    replay_ok = (
        len(replay_catches) > 0
        and ferrari_fr.n_mature_recalled == legacy_fr.n_mature_recalled
    )
    print(
        f"  macro:        over-confidence catches = {len(macro_catches)}  "
        f"mature recall preserved = {ferrari.n_mature_recalled}/{legacy.n_mature_recalled}  "
        f"{'+' if macro_ok else '!'}"
    )
    print(
        f"  fwd_replay:   over-confidence catches = {len(replay_catches)}  "
        f"mature recall preserved = {ferrari_fr.n_mature_recalled}/{legacy_fr.n_mature_recalled}  "
        f"{'+' if replay_ok else '!'}"
    )
    if macro_false_neg:
        print(f"  WARN: macro ferrari fires on skills legacy doesn't: {macro_false_neg}")
    if replay_false_neg:
        print(f"  WARN: replay ferrari fires on skills legacy doesn't: {replay_false_neg}")

    # Decision rationality — render the boundary table
    print()
    print("Decision boundary (1 = gate fires, 0 = blocks):")
    print("  trials | mean=0.80 macro_legacy | macro_ferrari | replay_legacy | replay_ferrari")
    for trials in (1, 2, 3, 5, 10, 20, 40, 60):
        successes = int(round(trials * 0.85))
        s = Skill(
            id="x", name="x", trigger="x", body="x",
            trials=trials, successes=successes,
        )
        legacy_mac = int(s.fitness_mean >= 0.80)
        ferrari_mac = int(s.fitness_lower_bound >= 0.65)
        legacy_rep = int(s.fitness_mean >= 0.50)
        ferrari_rep = int(s.fitness_lower_bound >= 0.30)
        print(
            f"  {trials:>4} ({successes}/{trials})  mean={s.fitness_mean:.2f} "
            f"lower={s.fitness_lower_bound:.2f}   "
            f"{legacy_mac}            {ferrari_mac}                {legacy_rep}              {ferrari_rep}"
        )

    return 0 if macro_ok and replay_ok else 1


if __name__ == "__main__":
    sys.exit(main())
