"""Ph4 — epistemic-health snapshot of a REAL Engram corpus (reproducible, no LLM).

"A memory that reports its own epistemic state." Reads a semantic facts DB and reports,
over the ALIVE (non-superseded) facts: status distribution, provenance coverage
(verified_by / source_episodes), and the verified fraction. This is the corpus-level
companion to ``engram.epistemic_health`` (which grounds individual facts via the LLM gate):
here we measure, instantly and on the whole corpus, how much of what a memory stored is
actually verified / has any provenance at all — the gap that provenance-on-write closes.

Pure SQL, read-only. Run: ``python -m benchmark.corpus_health_snapshot --db <path>``.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from typing import Any

_EMPTY = ("", "[]", "null", "{}")


def snapshot(db_path: str) -> dict[str, Any]:
    c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cols = {r[1] for r in c.execute("pragma table_info(facts)")}
        tot = c.execute("select count(*) from facts").fetchone()[0]
        alive = c.execute("select count(*) from facts where superseded_by is null").fetchone()[0]
        superseded = tot - alive
        status = {s: n for s, n in c.execute(
            "select status, count(*) from facts where superseded_by is null "
            "group by status order by 2 desc")}

        def has(col: str) -> int:
            if col not in cols:
                return -1
            ph = ",".join("?" for _ in _EMPTY)
            return c.execute(
                f"select count(*) from facts where superseded_by is null and {col} is not null "
                f"and {col} not in ({ph})", _EMPTY).fetchone()[0]

        verified = status.get("verified", 0)
        prov_vby = has("verified_by")
        prov_ep = has("source_episodes")
        denom = alive or 1
        return {
            "total": tot, "alive": alive, "superseded": superseded,
            "verified": verified, "verified_frac": round(verified / denom, 4),
            "with_verified_by": prov_vby,
            "provenance_frac": round(prov_vby / denom, 4) if prov_vby >= 0 else None,
            "with_source_episodes": prov_ep,
            "source_episode_frac": round(prov_ep / denom, 4) if prov_ep >= 0 else None,
            "status_distribution": status,
        }
    finally:
        c.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Real-corpus epistemic-health snapshot (Ph4).")
    p.add_argument("--db", required=True)
    p.add_argument("--out", type=argparse.FileType("w"), default=None)
    args = p.parse_args(argv)
    res = snapshot(args.db)
    print(json.dumps(res, indent=2))
    if args.out:
        json.dump(res, args.out, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["snapshot", "main"]
