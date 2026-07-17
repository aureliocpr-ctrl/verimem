"""Collapse the auto-hook pre-compact snapshot ballast — daily supersede, reversible.

The live corpus carries ~1471 facts under ``handoff/pre-compact-auto-hook-*``:
near-identical state snapshots an auto-hook wrote every 10-20 minutes (measured by
the corpus truth scan: they saturate the top of the pair list at cosine ~1.0, all
correctly classified EVOLUTION). They are 27% of the live corpus and pure recall
ballast: for any query they can only crowd out real facts.

Policy (conservative, deterministic — no NLI needed for a known-automated pattern):
group by UTC day, keep the DAY'S LAST snapshot live, supersede the others WITH the
winner as ``superseded_by``. Nothing is deleted: superseding is the store's own
reversible mechanism, and every change is journaled to an undo file
(``~/.engram/maintenance/autohook_collapse_<ts>.json``) that records the prior
state. Restore = clear superseded_by/at/reason on the listed ids.

    python -m scripts.collapse_autohook_snapshots            # DRY-RUN (default)
    python -m scripts.collapse_autohook_snapshots --apply    # execute + undo file
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

PREFIX = "handoff/pre-compact-auto-hook"
_DB = Path.home() / ".engram" / "semantic" / "semantic.db"
_UNDO_DIR = Path.home() / ".engram" / "maintenance"


def plan_collapse(rows: list[dict]) -> list[dict]:
    """Pure planning: group live snapshot rows by UTC day of created_at; per day
    the LAST (max created_at, id as tiebreak for determinism) survives, the rest
    are losers. Returns [{day, winner_id, loser_ids}] sorted by day; single-row
    days produce no entry (nothing to collapse)."""
    by_day: dict[str, list[dict]] = {}
    for r in rows:
        ts = float(r.get("created_at") or 0)
        day = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        by_day.setdefault(day, []).append(r)
    plan = []
    for day in sorted(by_day):
        group = sorted(by_day[day],
                       key=lambda r: (float(r.get("created_at") or 0),
                                      str(r.get("id"))))
        if len(group) < 2:
            continue
        plan.append({"day": day, "winner_id": str(group[-1]["id"]),
                     "loser_ids": [str(r["id"]) for r in group[:-1]]})
    return plan


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(_DB))
    ap.add_argument("--prefix", default=PREFIX)
    ap.add_argument("--apply", action="store_true",
                    help="execute the supersedes (default: dry-run report only)")
    a = ap.parse_args(argv)

    con = sqlite3.connect(f"file:{Path(a.db).as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT id, topic, created_at FROM facts WHERE "
        "(superseded_by IS NULL OR superseded_by='') AND topic LIKE ?",
        (a.prefix + "%",))]
    con.close()

    plan = plan_collapse(rows)
    n_losers = sum(len(p["loser_ids"]) for p in plan)
    print(json.dumps({
        "live_snapshots": len(rows), "days": len(plan),
        "would_supersede": n_losers,
        "would_remain_live": len(rows) - n_losers,
        "mode": "apply" if a.apply else "DRY-RUN",
    }, indent=2))
    if not a.apply or not plan:
        return 0

    from verimem.semantic import SemanticMemory
    sm = SemanticMemory(db_path=Path(a.db))
    undo = {"created": time.time(), "db": str(a.db), "prefix": a.prefix,
            "note": "restore = set superseded_by/superseded_at/superseded_reason "
                    "back to NULL/'' for each loser id",
            "entries": []}
    done = 0
    errors = 0
    for p in plan:
        for lid in p["loser_ids"]:
            try:
                r = sm.supersede(
                    lid, p["winner_id"],
                    reason="autohook-snapshot daily collapse (kept the day's "
                           "last snapshot; corpus truth scan 2026-07-02)")
                ok = bool(r.get("ok", True))
            except Exception as exc:  # noqa: BLE001 — journal and continue
                ok = False
                errors += 1
                print(f"ERROR superseding {lid}: {exc!r}")
            if ok:
                done += 1
                undo["entries"].append({"loser_id": lid,
                                        "winner_id": p["winner_id"]})
    _UNDO_DIR.mkdir(parents=True, exist_ok=True)
    undo_path = _UNDO_DIR / f"autohook_collapse_{int(time.time())}.json"
    undo_path.write_text(json.dumps(undo, indent=2), encoding="utf-8")

    # verify from a fresh read-only connection
    con = sqlite3.connect(f"file:{Path(a.db).as_posix()}?mode=ro", uri=True)
    remain = con.execute(
        "SELECT COUNT(*) FROM facts WHERE (superseded_by IS NULL OR "
        "superseded_by='') AND topic LIKE ?", (a.prefix + "%",)).fetchone()[0]
    con.close()
    print(json.dumps({"superseded": done, "errors": errors,
                      "remaining_live": remain,
                      "undo_file": str(undo_path)}, indent=2))
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
