"""Diagnose the candidate-skill Catch-22.

Audit 2026-05-12 finding: on the live 318-skill corpus, only 9
skills are promoted (2.8%). The pipeline writes ~80% of all
generated candidates into the library and then never invokes them:
``SkillLibrary.retrieve`` is called from ``mcp_server`` with
``status="promoted"``, so candidates with 0 trials cannot accumulate
any. They sit forever as "candidate, trials=0".

Live numbers:
  - 266 candidate skills total
  - 233 with trials == 0  (87.6% of candidates, 73.3% of *all* skills)
  - 23 with trials == 1
  - 4 with trials == 2
  - 1 with trials >= 3 and fitness >= 0.7 (only one eligible to promote)
  - 5 with trials >= 3 and fitness < 0.2 (eligible to retire)

This module surfaces the population so an operator can decide what
to do (manually promote a sample, retire stale ones, or rethink the
retrieval policy). It is *read-only* — no policy change is made
here. Changing the retrieval policy (e.g. ε-greedy exploration of
candidates) is a separate design discussion with its own safety
review.
"""
from __future__ import annotations

import time
from collections import Counter
from typing import Any


def stuck_candidates_report(
    skills: list[Any],
    *,
    min_age_days: float = 7.0,
    now_ts: float | None = None,
    top_k: int = 50,
) -> dict[str, Any]:
    """Identify candidate skills stuck at trials==0 for more than min_age_days.

    Args:
        skills: every skill in the library.
        min_age_days: only flag candidates older than this. Skills
            created in the last week may still be live-tested
            normally — don't pre-judge them.
        now_ts: override clock for tests.
        top_k: cap on returned items, sorted by age descending.

    Returns:
        {
          "n_total_skills": int,
          "summary": {
              "candidate_total": int,
              "candidate_trials_0": int,
              "candidate_trials_0_aged": int,   # >= min_age_days old
              "promoted_total": int,
              "retired_total": int,
              "catch_22_fraction": float,  # aged 0-trial / candidate_total
          },
          "stuck_skills": [
              {id, name, created_at, age_days, trials, status},
              ...  # sorted by age desc, capped at top_k
          ]
        }
    """
    now_ts = now_ts if now_ts is not None else time.time()
    threshold = min_age_days * 86_400.0

    counts: Counter[str] = Counter()
    candidate_zero_aged: list[tuple[Any, float]] = []  # (skill, age_seconds)
    for s in skills:
        status = getattr(s, "status", "")
        counts[status] += 1
        if status == "candidate":
            trials = int(getattr(s, "trials", 0) or 0)
            if trials == 0:
                counts["candidate_trials_0"] += 1
                created = float(getattr(s, "created_at", 0) or 0)
                age = now_ts - created if created > 0 else 0.0
                if age >= threshold:
                    candidate_zero_aged.append((s, age))

    candidate_zero_aged.sort(key=lambda x: -x[1])

    cand_total = counts.get("candidate", 0)
    aged_count = len(candidate_zero_aged)
    catch22 = aged_count / cand_total if cand_total else 0.0

    return {
        "n_total_skills": len(skills),
        "summary": {
            "candidate_total": cand_total,
            "candidate_trials_0": counts.get("candidate_trials_0", 0),
            "candidate_trials_0_aged": aged_count,
            "promoted_total": counts.get("promoted", 0),
            "retired_total": counts.get("retired", 0),
            "catch_22_fraction": round(catch22, 4),
            "min_age_days": float(min_age_days),
        },
        "stuck_skills": [
            {
                "id": getattr(s, "id", ""),
                "name": getattr(s, "name", ""),
                "trials": int(getattr(s, "trials", 0) or 0),
                "status": getattr(s, "status", ""),
                "created_at": float(getattr(s, "created_at", 0) or 0),
                "age_days": round(age / 86_400.0, 2),
            }
            for s, age in candidate_zero_aged[:top_k]
        ],
    }


__all__ = ["stuck_candidates_report"]
