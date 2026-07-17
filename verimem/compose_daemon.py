"""Nightly composition daemon — the ORGANISM scheduler shell around the ring.

One pass = P85 pre-flight -> compose_once(budget) -> P85 post-report:

  * **pre-flight**: if the self-write ratio over the recent window already
    ALARMS (past ENGRAM_SELF_RATIO_MAX, default 0.5), the daemon REFUSES to
    compose — an engine whose own output dominates the stream must not keep
    feeding on itself (past 0.5 the world's drift becomes invisible behind the
    engine's echo: the Vivarium P85 phase transition, here as an operational
    guard-rail, not a warning);
  * **budget**: the candidate bound is passed down to compose_once and any
    truncation is DECLARED in the report (no silent caps);
  * **post-report**: the self-ratio after the pass is reported so the operator
    sees the daemon consuming its own headroom.

The daemon deliberately writes NO telemetry facts about itself — a daemon
whose report inflates the very self-ratio that gates it would strangle its
own headroom (and violate the signed-footprints spirit). The report is the
return value / stdout, nothing else.

Scheduling stays with the OS (cron / Windows Task Scheduler) — local-first,
one-shot CLI:

    python -m verimem.compose_daemon --db path/to/store.db [--budget 100]
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from .composer import compose_once
from .self_provenance import self_write_check

__all__ = ["nightly_compose"]


def nightly_compose(mem: Any, *, budget_candidates: int = 100,
                    topic: str | None = None,
                    window: int = 500) -> dict[str, Any]:
    """One guarded composition pass. Returns an honest report:
    ``{skipped_self_ratio, self_ratio_pre, self_ratio_post, compose}`` —
    ``compose`` is the compose_once report, or None when the pre-flight
    refused."""
    pre = self_write_check(mem.semantic.db_path, window=window)
    if pre["alarm"]:
        return {"skipped_self_ratio": True,
                "reason": (f"self-write ratio {pre['self_ratio']:.2f} past "
                           f"{pre['threshold']:.2f} over the last {pre['n']} "
                           "facts — composing would feed the engine its own "
                           "echo (P85)"),
                "self_ratio_pre": pre["self_ratio"],
                "self_ratio_post": pre["self_ratio"],
                "compose": None}
    rep = compose_once(mem, topic=topic, max_candidates=budget_candidates)
    post = self_write_check(mem.semantic.db_path, window=window)
    return {"skipped_self_ratio": False,
            "self_ratio_pre": pre["self_ratio"],
            "self_ratio_post": post["self_ratio"],
            "compose": rep}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True, help="path to the verimem store")
    ap.add_argument("--budget", type=int, default=100)
    ap.add_argument("--topic", default=None)
    args = ap.parse_args(argv)
    from .client import Memory
    mem = Memory(args.db)
    report = nightly_compose(mem, budget_candidates=args.budget,
                             topic=args.topic)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
