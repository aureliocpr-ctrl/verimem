"""Correction-velocity detector — atomic idea #2 (2026-06-13).

Idea #1 (``emerging_briefing``) surfaces what you're doing a LOT lately. This
surfaces what you GET WRONG THEN FIX: when the incoming task's signature has a
history of FAILURE-then-SUCCESS for the *same* signature, the briefing hands you
the approach that eventually worked (and the failed attempts to avoid) so you
skip the failed first attempt instead of re-deriving the correction.

Pure, deterministic, no-LLM. Grounded in what real episodes actually carry —
``task_text`` + ``outcome`` + ``created_at`` — NOT step-level traces, which the
live corpus rarely populates (a trajectory diff there would look sophisticated
and return nothing). Reuses ``emerging_patterns._signature`` (the same 4-token
signature primitive as idea #1) for consistency.

Wiring it into ``briefing.get_briefing`` (which already accepts ``task_text``)
is a separate, additive step exercised by the wiring tests.
"""
from __future__ import annotations

import time
from typing import Any

from .emerging_patterns import _signature

_DAY = 86400.0

# Canonical outcome vocab is Literal["success","failure","partial"] (episode.py);
# we widen failures to the failure_clusters set and successes to the two clean
# positives. "partial" is deliberately NEITHER — a half-fix is not a correction.
_FAILURE = frozenset({"failure", "error", "fail", "failed"})
_SUCCESS = frozenset({"success", "ok"})


def _sig_tokens(text: str) -> set[str]:
    return {t for t in _signature(text).split(",") if t}


def _outcome(ep: Any) -> str:
    return str(getattr(ep, "outcome", "") or "").strip().lower()


def _ts(ep: Any) -> float:
    return float(getattr(ep, "created_at", 0.0) or 0.0)


def detect_correction_pattern(
    task_text: str,
    episodes: list[Any],
    *,
    now: float | None = None,
    min_token_overlap: int = 3,
    max_recent: int = 3,
    relevant_ids: set[Any] | None = None,
) -> dict[str, Any]:
    """If ``task_text``'s signature has a FAILURE-then-SUCCESS history, surface
    the correcting success and the failed attempts that preceded it.

    Returns ``{has_correction, task_signature, failures_before_success,
    correction_latency_days, success, recent_failures}``.

    Relevance modes:
      - ``relevant_ids`` given (the SEMANTIC path): the caller has already chosen
        the episodes whose MEANING matches this task (e.g. via ``memory.recall``
        cosine), so a paraphrase connects to past work that used different words.
        Only episodes whose ``id`` is in this set are considered.
      - ``relevant_ids`` is None (the TOKEN fallback): match on 4-token signature
        overlap (``>= min_token_overlap``) — keeps the function pure for tests and
        usable without an embedding store.

    Side-effect free; safe on empty/blank input.
    """
    if now is None:
        now = time.time()
    task_sig = _signature(task_text or "")
    base: dict[str, Any] = {
        "has_correction": False,
        "task_signature": task_sig,
        "failures_before_success": 0,
        "correction_latency_days": None,
        "success": None,
        "recent_failures": [],
    }
    if not (task_text or "").strip() or not episodes:
        return base

    if relevant_ids is not None:
        relevant = [ep for ep in episodes if getattr(ep, "id", None) in relevant_ids]
    else:
        task_tokens = _sig_tokens(task_text)
        if len(task_tokens) < min_token_overlap:
            return base  # too few tokens to ever reach the overlap threshold
        relevant = [
            ep for ep in episodes
            if len(_sig_tokens(getattr(ep, "task_text", "")) & task_tokens) >= min_token_overlap
        ]
    if not relevant:
        return base
    failures = sorted((ep for ep in relevant if _outcome(ep) in _FAILURE), key=_ts)
    successes = sorted((ep for ep in relevant if _outcome(ep) in _SUCCESS), key=_ts)
    if not failures or not successes:
        return base

    first_failure_ts = _ts(failures[0])
    # The correcting success is the EARLIEST success that comes AFTER a failure.
    # (A success that predates every failure is a regression, not a recovery.)
    correcting = next((s for s in successes if _ts(s) > first_failure_ts), None)
    if correcting is None:
        return base

    correcting_ts = _ts(correcting)
    failures_before = [f for f in failures if _ts(f) < correcting_ts]
    last_failure_ts = _ts(failures_before[-1])  # failures sorted asc

    recent = sorted(failures_before, key=_ts, reverse=True)[:max_recent]
    recent_failures = [
        {
            "id": getattr(f, "id", None),
            "task_text": getattr(f, "task_text", ""),
            "age_days": round((now - _ts(f)) / _DAY, 2),
        }
        for f in recent
    ]
    return {
        "has_correction": True,
        "task_signature": task_sig,
        "failures_before_success": len(failures_before),
        "correction_latency_days": round((correcting_ts - last_failure_ts) / _DAY, 2),
        "success": {
            "id": getattr(correcting, "id", None),
            "task_text": getattr(correcting, "task_text", ""),
            "outcome": getattr(correcting, "outcome", None),
            "age_days": round((now - correcting_ts) / _DAY, 2),
        },
        "recent_failures": recent_failures,
    }


__all__ = ["detect_correction_pattern"]
