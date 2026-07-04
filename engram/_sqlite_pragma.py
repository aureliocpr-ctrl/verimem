"""Single source of truth for the SQLite connection PRAGMA policy.

The four DB modules (semantic, memory/episodic, entity_kg, skill) each open
short-lived per-operation connections with the same PRAGMA set (WAL +
busy_timeout=60000 + synchronous=NORMAL + foreign_keys). The ``synchronous`` level
was hard-coded in 5 places; this centralizes the ONE knob a deployment may want to
tune (production-scaling review 2026-06-20).

``synchronous=NORMAL`` (default) is WAL-safe and fast but, between checkpoints, a
committed-but-uncheckpointed write can be lost on an OS crash / power loss.
``ENGRAM_SQLITE_SYNCHRONOUS=FULL`` trades write throughput for per-commit fsync
durability — for deployments that need it. Default keeps current behaviour.
"""
from __future__ import annotations

import os


def synchronous_mode() -> str:
    """Return the SQLite ``synchronous`` level: 'NORMAL' (default) or 'FULL'."""
    v = os.environ.get("ENGRAM_SQLITE_SYNCHRONOUS", "NORMAL").strip().upper()
    return "FULL" if v == "FULL" else "NORMAL"


__all__ = ["synchronous_mode"]
