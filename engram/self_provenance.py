"""P85 actor/self-provenance — signed footprints for engine writes.

Vivarium P85 (2026-07-11, verified on the lab's acting-agent world): an agent
that writes records conforming to its own BELIEFS poisons its own learning —
past a self-ratio of 0.5 in the stream, the world's drift becomes invisible
because the stale belief is the best fit on the contaminated flow (an exact
phase transition at 0.5). The fix is not "write less": it is SIGN your own
footprints and verify only against the world.

Operationally, before any composition/consolidation daemon writes into the
store (the ORGANISM plan), three properties must hold:

  1. engine writes carry an ``actor:<component>[:run]`` ref in ``verified_by``
     — recognisable provenance, never masquerading as the ``user`` fallback;
  2. actor sources are NEVER independent witnesses (source_trust filters them
     from confirmations and acceptance): the engine cannot manufacture
     consensus about its own claims — its facts earn admission through
     VERIFICATION (epistemic labels, grounding), not reputation;
  3. the self-write ratio over the recent window is monitored, alarming past
     the P85 threshold (default 0.5, env ENGRAM_SELF_RATIO_MAX).

Pure helpers + one SQL read; no write path here.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

__all__ = ["SELF_PREFIX", "actor_of", "is_self_ref", "self_write_check"]

SELF_PREFIX = "actor"


def is_self_ref(ref: str) -> bool:
    """True iff ``ref`` is an engine-signed footprint (``actor:...``)."""
    return isinstance(ref, str) and ref.strip().lower().startswith(
        f"{SELF_PREFIX}:")


def actor_of(ref: str) -> str | None:
    """``actor:composer:run42`` -> ``composer``; None for non-actor refs."""
    if not is_self_ref(ref):
        return None
    parts = ref.strip().split(":", 2)
    return parts[1] if len(parts) > 1 and parts[1] else None


def _threshold() -> float:
    try:
        return float(os.environ.get("ENGRAM_SELF_RATIO_MAX", "0.5"))
    except ValueError:
        return 0.5


def self_write_check(db_path: str | Path, *, window: int = 500) -> dict[str, Any]:
    """Fraction of engine-written facts among the ``window`` most recent ones,
    with the P85 alarm. Read-only, best-effort (an unreadable store returns a
    neutral no-alarm answer rather than breaking a health probe)."""
    n = self_n = 0
    try:
        with sqlite3.connect(str(db_path)) as conn:
            rows = conn.execute(
                "SELECT verified_by FROM facts "
                "ORDER BY created_at DESC LIMIT ?", (int(window),)).fetchall()
    except sqlite3.Error:
        rows = []
    for (vb_raw,) in rows:
        try:
            refs = json.loads(vb_raw or "[]")
        except (ValueError, TypeError):
            refs = []
        n += 1
        if any(is_self_ref(r) for r in refs if isinstance(r, str)):
            self_n += 1
    ratio = (self_n / n) if n else 0.0
    thr = _threshold()
    return {"n": n, "self_writes": self_n, "self_ratio": ratio,
            "threshold": thr, "alarm": ratio > thr}
