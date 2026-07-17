"""Rule-based episode classifier.

FORGIA pezzo #244 — Wave 43. Tags each episode with one or more
flags based on heuristic rules. Pure local, no LLM.

Flags:
  - `noisy_output`: outcome=success but final_answer has known
    header noise patterns (`OK\\n`, `Answer:\\n`, etc.)
  - `missing_skills`: outcome=success but skills_used is empty
  - `shell_warn`: task_text contains shell-injection-shaped strings
  - `long_running`: tokens_used > threshold (default 10000)
  - `failure_recovery`: success on a task_text that previously
    failed
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

_SHELL_PATTERNS = re.compile(
    r"(rm -rf|`\$|>\s*/dev/null|\|\s*sh|;\s*sh|&&\s*\w+|"
    r"chmod\s+\+x|/etc/passwd|wget\s+|curl\s+.+\|\s*bash)",
    re.IGNORECASE,
)

_NOISY_PATTERNS = re.compile(
    r"^\s*(OK\b|Answer:|Result:|Sure[!,]?|Here|Output:)",
    re.IGNORECASE,
)


def classify_episodes(
    episodes: list[Any],
    *,
    long_running_tokens: int = 10000,
) -> dict[str, Any]:
    """Apply heuristic rules to flag each episode.

    Args:
      - `episodes`: iterable of episode-likes.
      - `long_running_tokens`: threshold for `long_running` flag.

    Returns: `{n_total, flag_counts, episodes}` where each episode
    record is `{id, flags, outcome}`.
    """
    # SCAN-68 FIX 2026-06-02 (NONNA): TRUE two-pass. Prima era single-pass
    # (le failure venivano aggiunte a prior_failure DENTRO il loop) -> il flag
    # failure_recovery scattava solo se la failure precedeva il success
    # nell'ordine d'iterazione. Il caller usa memory.all() = newest-first ->
    # flag MORTO. Pass 1 raccoglie i task con QUALSIASI failure; pass 2 flagga
    # i success. (Senza confronto temporale per-coppia, "previously" =
    # set-membership, coerente con la docstring "any prior failure".)
    episodes = list(episodes)
    prior_failure: set[str] = {
        (getattr(ep, "task_text", "") or "")
        for ep in episodes
        if getattr(ep, "outcome", "") == "failure"
    }
    records: list[dict[str, Any]] = []
    flag_counts: Counter[str] = Counter()

    for ep in episodes:
        flags: list[str] = []
        outcome = getattr(ep, "outcome", "")
        task = getattr(ep, "task_text", "") or ""
        answer = getattr(ep, "final_answer", "") or ""
        skills = list(getattr(ep, "skills_used", None) or [])
        tokens = int(getattr(ep, "tokens_used", 0) or 0)

        if outcome == "success" and _NOISY_PATTERNS.match(answer):
            flags.append("noisy_output")
        if outcome == "success" and not skills:
            flags.append("missing_skills")
        if _SHELL_PATTERNS.search(task):
            flags.append("shell_warn")
        if tokens > long_running_tokens:
            flags.append("long_running")
        if outcome == "success" and task in prior_failure:
            flags.append("failure_recovery")

        for f in flags:
            flag_counts[f] += 1
        records.append({
            "id": getattr(ep, "id", ""),
            "outcome": outcome,
            "flags": flags,
        })

    return {
        "n_total": len(records),
        "flag_counts": dict(flag_counts),
        "episodes": records,
    }


__all__ = ["classify_episodes"]
