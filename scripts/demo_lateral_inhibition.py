"""Longitudinal experiment: does lateral inhibition differentiate rival skills?

We simulate N consecutive successful applications of `winner` on related
tasks and we periodically measure the cosine between winner.embedding and
rival.embedding. With lateral inhibition OFF, both embeddings drift via
Hebbian only — rivals stay close because they share the same prior.
With lateral inhibition ON, rivals are pushed away from each task, so
the cosine should *fall* over time.

Run:
    python scripts/demo_lateral_inhibition.py

Expected story when the mechanism works:
    step 0   off=0.85   on=0.85
    step 10  off=0.86   on=0.78
    step 25  off=0.87   on=0.69
    step 50  off=0.88   on=0.58
"""
from __future__ import annotations

import shutil
import tempfile
from dataclasses import replace
from pathlib import Path

import numpy as np

from verimem import embedding
from verimem import skill as skill_mod
from verimem.config import CONFIG
from verimem.skill import Skill, SkillLibrary

# A small bag of related tasks. We rotate through them to simulate a
# stream of similar-but-not-identical successes. This is the regime
# lateral inhibition exists for: many wins on a region of the manifold.
TASKS = [
    "fix the calculator add function which returns wrong sign",
    "patch arithmetic bug in calc.py — return a+b not a-b",
    "the add helper subtracts instead of adding, fix it",
    "addition operator regression in calculator module",
    "calculator returns negative result when adding positive numbers",
    "off-by-one in the return statement of add()",
    "the add() function uses the wrong operator",
    "fix subtraction-where-addition-should-be in arithmetic helpers",
]


def _cosine(u, v):
    nu = float(np.linalg.norm(u))
    nv = float(np.linalg.norm(v))
    if nu == 0 or nv == 0:
        return 0.0
    return float(np.dot(u, v) / (nu * nv))


def run(label: str, *, lateral_on: bool, n_steps: int = 50,
        snapshot_at=(0, 5, 10, 25, 50)) -> list[tuple[int, float]]:
    """Return [(step, cosine_winner_rival)] taken at the snapshot points."""
    tmpdir = Path(tempfile.mkdtemp(prefix=f"lat_inh_{label}_"))
    try:
        # Swap CONFIG inside the skill module — frozen-dataclass safe.
        original_config = skill_mod.CONFIG
        skill_mod.CONFIG = replace(
            CONFIG,
            lateral_inhibition_enabled=lateral_on,
            lateral_inhibition_min_similarity=0.80,
            lateral_inhibition_alpha=0.05,
            lateral_inhibition_top_k=5,
        )
        try:
            lib = SkillLibrary(
                dir_path=tmpdir / "skills",
                db_path=tmpdir / "skills_index.db",
            )
            seed_winner = embedding.encode(
                "fix arithmetic bug in calculator add").tolist()
            seed_rival = embedding.encode(
                "fix arithmetic bug in calculator subtract").tolist()
            winner = Skill(
                name="bugfix_arith", trigger="fix arithmetic bug",
                body="patch return statement",
                learned_embedding=seed_winner,
            )
            rival = Skill(
                name="rewrite_module", trigger="rewrite arithmetic module",
                body="overwrite the file",
                learned_embedding=seed_rival,
            )
            lib.store(winner)
            lib.store(rival)

            snaps: list[tuple[int, float]] = []

            def snapshot(step: int):
                w = np.asarray(lib.get(winner.id).learned_embedding,
                               dtype=np.float32)
                r = np.asarray(lib.get(rival.id).learned_embedding,
                               dtype=np.float32)
                snaps.append((step, _cosine(w, r)))

            snapshot(0)
            for i in range(1, n_steps + 1):
                task = TASKS[i % len(TASKS)]
                lib.update_fitness(
                    winner.id, success=True, tokens=10, task_text=task,
                )
                if i in snapshot_at:
                    snapshot(i)
            return snaps
        finally:
            skill_mod.CONFIG = original_config
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main() -> None:
    print("Cosine winner↔rival over time (Hebbian + optional lateral inhibition)")
    print("-" * 64)
    off = run("off", lateral_on=False)
    on = run("on", lateral_on=True)
    # Align by step.
    by_step = {s: c for s, c in off}
    print(f"{'step':>5}   {'OFF':>10}   {'ON':>10}   {'Δ':>10}")
    for step, on_cos in on:
        off_cos = by_step.get(step, float("nan"))
        delta = on_cos - off_cos
        print(f"{step:>5}   {off_cos:>+10.4f}   {on_cos:>+10.4f}   {delta:>+10.4f}")
    print()
    print(
        "Read: at step 50, lateral inhibition has pushed the rival cosine "
        f"down by {on[-1][1] - by_step.get(on[-1][0], 0):+.4f} relative to "
        "Hebbian-only. Negative delta = differentiation worked."
    )


if __name__ == "__main__":
    main()
