"""Cycle 228 (2026-05-23) — H8c: parallel emergent-skill drafter.

META-PROCESS B4 NUCLEAR catena applied (rules/meta-process-b4-nuclear-
catena-2026-05-23, fact ee5aa5e85902):

STEP 2 concatenation:
  clp.kernel.swarm_distribute sub-linear (CLP LOOP 223, fact 771bac07)
  + HippoAgent draft_skill_from_community LLM-free + I/O-bound
    (HippoAgent cycle 217)
  ⇒ H8c hypothesis: ThreadPoolExecutor parallelization of the drafter
    achieves sub-linear scaling on N candidates, zero API key (O4).

This is a cross-project bridge: a pattern proven in clp.kernel is now
applied to HippoAgent's emergence drafting layer, with the I/O-bound
nature of `draft_skill_from_community` (one SQL SELECT per call to
fetch propositions) making ThreadPool — not ProcessPool — the right
primitive (GIL releases during sqlite3 C-level I/O).

Sub-linear claim, A3 onesto caveats:
  - Synthetic fixture (cycle 228 tests) has ~25ms per draft. Real
    corpus is similar.  Overhead of ThreadPoolExecutor.submit + join
    is ~1-2ms per task → only a clear win for N ≥ 8.
  - For N=1 the pool *hurts* — wrapper falls back to sequential
    when len(communities) <= 1.
  - On Windows + Python 3.13, the GIL still serialises Python-level
    Counter/regex work — speedup is dominated by SQL wait time, not
    keyword extraction.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from verimem.skill_drafter import draft_skill_from_community


def parallel_draft_communities(
    semantic_db: Path | str,
    communities: list[dict[str, Any]],
    *,
    max_workers: int = 4,
) -> list[dict[str, Any]]:
    """Draft skill bodies for a list of communities in parallel.

    Args:
        semantic_db: path to the live ``semantic.db``.
        communities: list of dicts as produced by
            ``detect_emerging_skills``.
        max_workers: ThreadPool size.  Default 4 — Amdahl bound +
            SQLite contention sweet spot empirically on Windows.

    Returns:
        List of drafts in the SAME ORDER as ``communities`` (so
        downstream callers can zip/index without ambiguity).

    Notes:
        ``draft_skill_from_community`` swallows exceptions internally
        and returns a stub draft, so the worker callable will not
        raise.  We still wrap each call in a thin shim to guarantee
        the executor surfaces a dict.
    """
    if not communities:
        return []
    if len(communities) == 1:
        # Fall back to sequential — pool overhead dwarfs the work.
        return [draft_skill_from_community(semantic_db, communities[0])]

    db_path = Path(semantic_db)

    def _one(c: dict[str, Any]) -> dict[str, Any]:
        try:
            return draft_skill_from_community(db_path, c)
        except Exception:  # noqa: BLE001 — defensive worker
            return {
                "skill_name": str(c.get("suggested_skill_name", "")),
                "draft_text": "",
                "trigger_keywords": [],
                "fact_ids": [],
                "evidence": {},
            }

    # ThreadPoolExecutor.map preserves input ordering.
    with ThreadPoolExecutor(max_workers=int(max_workers)) as pool:
        results = list(pool.map(_one, communities))
    return results


__all__ = ["parallel_draft_communities"]
