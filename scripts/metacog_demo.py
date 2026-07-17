"""Round 3 demo — metacognition. HippoAgent knows what it knows.

3 simulated recall scenarios:
  A) Strong match (3+ high-sim concordant episodes) → "high" confidence
  B) Vague match (1 medium-sim episode) → "low" → fallback advised
  C) No match (empty recall) → "none" → ask user / search external

Run: python scripts/metacog_demo.py
"""
from __future__ import annotations

from verimem.metacognition import assess_recall_confidence


def fmt(name: str, results: list[dict]) -> None:
    out = assess_recall_confidence(results)
    print(f"\n>> Scenario {name}: {len(results)} recall result(s)")
    for r in results:
        print(f"    sim={r['similarity']:.2f}  outcome={r['outcome']}  task={r['task'][:50]}")
    print(f"   VERDICT: level={out['level']}  score={out['score']}  "
          f"max_sim={out['max_similarity']}  agree={out['outcome_agreement']}")
    print(f"   → {out['fallback_suggestion']}")


def main():
    print("=" * 70)
    print("Round 3 demo — Metacognition (calibrated uncertainty)")
    print("=" * 70)

    # A — strong match
    a = [
        {"similarity": 0.85, "outcome": "success", "task": "WordPress CF7 RCE"},
        {"similarity": 0.80, "outcome": "success", "task": "wp plugin exploit"},
        {"similarity": 0.78, "outcome": "success", "task": "contact-form-7 chain"},
        {"similarity": 0.72, "outcome": "success", "task": "RCE via file_attachment"},
    ]
    fmt("A (strong match)", a)

    # B — vague
    b = [
        {"similarity": 0.42, "outcome": "success", "task": "unrelated nginx config"},
    ]
    fmt("B (vague match)", b)

    # C — no match
    fmt("C (no match)", [])

    # D — split outcomes (failure prevails) — should be 'medium' (downgraded)
    d = [
        {"similarity": 0.85, "outcome": "success", "task": "X"},
        {"similarity": 0.80, "outcome": "failure", "task": "X bis"},
        {"similarity": 0.75, "outcome": "failure", "task": "X tris"},
    ]
    fmt("D (split outcomes)", d)

    # E — high sim but only 1 episode — downgraded to 'medium'
    e = [
        {"similarity": 0.90, "outcome": "success", "task": "Lonely hit"},
    ]
    fmt("E (high sim, 1 episode)", e)

    print("\n" + "=" * 70)
    print("KEY INSIGHT")
    print("=" * 70)
    print("HippoAgent now signals CALIBRATED uncertainty:")
    print("  high  → proceed confidently")
    print("  med   → verify key facts first")
    print("  low   → don't rely on memory, search externally")
    print("  none  → ask user, no memory exists")
    print()
    print("This prevents *bluffing* — the worst failure mode of LLM agents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
