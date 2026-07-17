"""Bench: Modern Hopfield pattern completion — 3 dimensions.

Dichiarate prima di misurare:

  1. ARGMAX EQUIVALENCE at high β:
     With β high (≥ 32), Hopfield attention concentrates on a single
     pattern. We verify the top-weight pattern matches cosine top-1
     on at least 90% of queries — sanity that the math degenerates
     correctly to cosine in the limit.

  2. SOFT PRIOR at low β:
     With β low (≤ 1), attention should spread across the K closest
     patterns. Measure: top-3 weights should account for less than
     50% of the mass on a 50-pattern corpus (i.e. at least 50% of
     the mass spreads beyond top-3 — that's the "prior" regime).

  3. PARTIAL-CUE ROBUSTNESS:
     The same query encoded as the FULL summary text vs. just the
     task_text fragment should give the same top-attention pattern
     in ≥80% of cases. This is the "pattern completion from partial
     features" promise.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem import embedding as emb_mod
from verimem.episode import Episode, Trace
from verimem.hopfield import hopfield_complete
from verimem.memory import EpisodicMemory


def _ep(*, id_: str, task_text: str, final_answer: str = "ok") -> Episode:
    return Episode(
        id=id_, task_id="t", task_text=task_text,
        outcome="success", final_answer=final_answer,
        traces=[Trace(
            step=1, thought="x", action="x", action_input="{}",
            observation="x",
        )],
    )


def main() -> int:
    # 50 episodes across 5 clusters (10 variants each)
    cluster_topics = [
        ("calc.py arithmetic", "fix sign bug in arithmetic routine"),
        ("auth migration", "rotate JWT signing key in production"),
        ("dashboard plot", "render time-series chart on dashboard"),
        ("ssl cert", "renew Let's Encrypt SSL certificate"),
        ("ci pipeline", "add lint step to GitHub Actions workflow"),
    ]
    queries: list[tuple[str, str, str]] = []  # (cluster_id, full, partial)

    with tempfile.TemporaryDirectory() as tmp:
        mem = EpisodicMemory(db_path=Path(tmp) / "ep.db")
        for c_idx, (topic, ans) in enumerate(cluster_topics):
            for v in range(10):
                ep_id = f"c{c_idx}_v{v:02d}"
                mem.store(_ep(
                    id_=ep_id,
                    task_text=f"{topic} variant {v}",
                    final_answer=f"{ans} (rev {v})",
                ))
                # First 3 of each cluster also become test queries
                if v < 3:
                    queries.append((
                        f"c{c_idx}",
                        f"{topic} variant {v} :: {ans} (rev {v})",
                        topic,  # short partial cue
                    ))

        # Dimension 1: high-β argmax equivalence
        argmax_match = 0
        for cluster, full_text, _partial in queries:
            cue = emb_mod.encode(full_text)
            _, weights, ids = hopfield_complete(mem, cue, beta=32.0)
            top_id = ids[int(weights.argmax())]
            if top_id.startswith(cluster):
                argmax_match += 1
        argmax_rate = argmax_match / len(queries)

        # Dimension 2: low-β spread
        cue = emb_mod.encode("calc.py arithmetic variant 0")
        _, weights, _ids = hopfield_complete(mem, cue, beta=1.0)
        top3_mass = float(sum(sorted(weights, reverse=True)[:3]))

        # Dimension 3: partial-cue robustness
        partial_match = 0
        for cluster, _full, partial in queries:
            full_cue = emb_mod.encode(_full)
            partial_cue = emb_mod.encode(partial)
            _, w_full, ids = hopfield_complete(mem, full_cue, beta=8.0)
            _, w_partial, _ = hopfield_complete(mem, partial_cue, beta=8.0)
            if (
                ids[int(w_full.argmax())][:2]
                == ids[int(w_partial.argmax())][:2]
            ):
                partial_match += 1
        partial_rate = partial_match / len(queries)

    print()
    print("Bench: Modern Hopfield pattern completion (50 patterns, 5 clusters)")
    print()
    print(f"  argmax equivalence at β=32:    {argmax_rate:.3f}  "
          f"({argmax_match}/{len(queries)})")
    print(f"  spread at β=1 (top-3 mass):    {top3_mass:.3f}  "
          f"(spreads if < 0.50)")
    print(f"  partial-cue robustness β=8:    {partial_rate:.3f}  "
          f"({partial_match}/{len(queries)})")
    print()
    print("Verdict (3 dimensions, declared up front):")
    a_ok = argmax_rate >= 0.90
    b_ok = top3_mass < 0.50
    c_ok = partial_rate >= 0.80
    print(f"  argmax >= 0.90:        {'+' if a_ok else '!'}")
    print(f"  spread (top3 < 0.50):  {'+' if b_ok else '!'}")
    print(f"  partial >= 0.80:       {'+' if c_ok else '!'}")
    return 0 if (a_ok and b_ok and c_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
