"""Emerging-task early-warning — atomic idea #1 (2026-06-13).

The flip: instead of recalling the whole corpus when you start a task, the
briefing notices when the INCOMING task matches a *rising* signature — something
you've done several times this week but almost never before — and surfaces ONLY
the recent episodes that share it, flagged ``[EMERGING]``. You accelerate what
you're getting good at instead of re-deriving it.

Pure, deterministic, no-LLM. Composes two existing real capabilities verified
in the codebase:
  - ``emerging_patterns._signature`` (the 4-token task signature)
  - ``emerging_patterns.find_emerging_patterns`` (which signatures are rising)

This module is the curation core; wiring it into ``briefing.get_briefing``
(which already accepts ``task_text``) is a separate, additive step.
"""
from __future__ import annotations

import time
from typing import Any

from .emerging_patterns import _signature, find_emerging_patterns

_DAY = 86400.0


def _sig_tokens(text: str) -> set[str]:
    return {t for t in _signature(text).split(",") if t}


def curate_emerging_briefing(
    task_text: str,
    episodes: list[Any],
    *,
    now: float | None = None,
    recent_window_days: float = 7.0,
    min_token_overlap: int = 3,
) -> dict[str, Any]:
    """If ``task_text``'s signature matches a rising one, flag it and return the
    recent same-signature episodes (most-recent first).

    Returns ``{is_emerging, task_signature, matched_pattern, episodes_recent}``.
    Match is token-overlap (not exact signature equality) so paraphrases of the
    same task still connect. Side-effect free; safe on empty input.
    """
    if now is None:
        now = time.time()
    task_sig = _signature(task_text or "")
    base = {
        "is_emerging": False,
        "task_signature": task_sig,
        "matched_pattern": None,
        "episodes_recent": [],
    }
    if not (task_text or "").strip() or not episodes:
        return base

    task_tokens = _sig_tokens(task_text)
    emerging = find_emerging_patterns(
        episodes, now=now, recent_window_days=recent_window_days,
    ).get("emerging", [])

    # Best-matching rising signature: most shared tokens, at/above the threshold.
    best: dict[str, Any] | None = None
    best_overlap = min_token_overlap - 1
    for pat in emerging:
        overlap = len(task_tokens & {t for t in pat["signature"].split(",") if t})
        if overlap > best_overlap:
            best_overlap = overlap
            best = pat
    if best is None:
        return base

    # Surface the recent episodes that share the matched rising signature.
    recent_cutoff = now - recent_window_days * _DAY
    matched_tokens = {t for t in best["signature"].split(",") if t}
    recent: list[dict[str, Any]] = []
    for ep in episodes:
        ts = float(getattr(ep, "created_at", 0.0) or 0.0)
        if ts < recent_cutoff:
            continue
        if len(_sig_tokens(getattr(ep, "task_text", "")) & matched_tokens) >= min_token_overlap:
            recent.append({
                "id": getattr(ep, "id", None),
                "task_text": getattr(ep, "task_text", ""),
                "outcome": getattr(ep, "outcome", None),
                "age_days": round((now - ts) / _DAY, 2),
            })
    recent.sort(key=lambda e: e["age_days"])  # most-recent first
    return {
        "is_emerging": True,
        "task_signature": task_sig,
        "matched_pattern": best,
        "episodes_recent": recent,
    }


__all__ = ["curate_emerging_briefing"]
