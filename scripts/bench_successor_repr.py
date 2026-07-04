"""Bench: Successor Representation — 3 dimensions.

Pezzo #20 forges the SR primitive (Dayan 1993, Stachenfeld 2017).

Dichiarate prima di misurare:

  1. PREDICT @1 ACCURACY: on a synthetic Markov chain dataset (10
     skills, 200 episodes, transition matrix with one strong path),
     `predict_next` should hit the truly-most-likely-next ≥ 0.90.

  2. CLOSED-FORM AGREEMENT: the iterative SR matches the closed-form
     `(I - γP)^(-1)` (row-normalised) within 1e-4 max element-wise.

  3. SCALABILITY: building SR for 100 unique skills × 1000 episodes
     completes in < 200ms (the inverse + iteration are O(S³)).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.successor_repr import (
    build_successor_matrix,
    build_transition_matrix,
    predict_next,
)


def main() -> int:
    rng = np.random.default_rng(seed=20260508)

    # ---- Dimension 1: predict @1 accuracy --------------------------
    # Synthetic 10-skill Markov chain. For each skill, pick a
    # "favourite" successor; transitions follow that 80% of the time
    # and a uniform random other skill 20%.
    n_skills = 10
    skills = [f"S{i}" for i in range(n_skills)]
    rng_perm = rng.permutation(n_skills)
    favourite = {skills[i]: skills[rng_perm[i]] for i in range(n_skills)}
    # Avoid self-favourites (mask diagonal).
    for s in skills:
        if favourite[s] == s:
            favourite[s] = skills[(skills.index(s) + 1) % n_skills]

    episodes = []
    for _ in range(200):
        ep_len = rng.integers(3, 7)
        cur = rng.choice(skills)
        seq = [cur]
        for _ in range(ep_len - 1):
            if rng.random() < 0.8:
                cur = favourite[cur]
            else:
                cur = rng.choice(skills)
            seq.append(cur)
        episodes.append(seq)

    ids, P = build_transition_matrix(episodes)
    correct = 0
    for s in skills:
        pred = predict_next(s, ids, P, top_k=1)
        if pred and pred[0] == favourite[s]:
            correct += 1
    p_at_1 = correct / n_skills

    # ---- Dimension 2: iterative vs closed-form ---------------------
    gamma = 0.85
    ids_iter, M_iter = build_successor_matrix(episodes, gamma=gamma, n_iter=200)
    ids_p, P_full = build_transition_matrix(episodes)
    n = P_full.shape[0]
    M_closed = np.linalg.inv(np.eye(n) - gamma * P_full)
    row_sums = M_closed.sum(axis=1, keepdims=True)
    row_sums[row_sums < 1e-12] = 1.0
    M_closed_norm = (M_closed / row_sums).astype(np.float32)
    max_disagreement = float(np.max(np.abs(M_iter - M_closed_norm)))

    # ---- Dimension 3: scalability ---------------------------------
    big_skills = [f"S{i:03d}" for i in range(100)]
    big_eps: list[list[str]] = []
    for _ in range(1000):
        ep = list(rng.choice(big_skills, size=rng.integers(2, 6), replace=False))
        big_eps.append(ep)
    t0 = time.perf_counter()
    build_successor_matrix(big_eps, gamma=0.9, n_iter=50)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    print()
    print("Bench: Successor Representation (Dayan 1993 / Stachenfeld 2017)")
    print()
    print("  predict@1 accuracy on synthetic chain (10 skills, 200 ep):")
    print(f"    rate: {p_at_1:.2f} ({correct}/{n_skills}) (target ≥ 0.90)")
    print()
    print(f"  iterative vs closed-form max disagreement: "
          f"{max_disagreement:.2e}  (target < 1e-4)")
    print()
    print(f"  scalability (100 skills × 1000 episodes): "
          f"{elapsed_ms:.1f} ms  (target < 200 ms)")
    print()
    print("Verdict (3 dimensions):")
    d1 = p_at_1 >= 0.90
    d2 = max_disagreement < 1e-4
    d3 = elapsed_ms < 200.0
    print(f"  predict@1 ≥ 0.90:           {'+' if d1 else '!'}")
    print(f"  iter ≈ closed-form:         {'+' if d2 else '!'}")
    print(f"  scalability < 200 ms:       {'+' if d3 else '!'}")
    return 0 if (d1 and d2 and d3) else 1


if __name__ == "__main__":
    sys.exit(main())
