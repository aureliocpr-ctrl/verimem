"""Deduplicate byte-identical live facts — deterministic, reversible.

The corpus truth scan surfaced exact-text repeats (e.g. an event-log line
"User dismounted the app from ShellAi slot 'lay1'" stored dozens of times, test
diary entries ×27-70). These are byte-identical after whitespace normalization —
pure recall ballast with ZERO false-positive risk (no NLI, no cosine, no threshold:
same text is the same fact).

Policy: group live facts by whitespace-normalized proposition; per group with >1
member keep the EARLIEST (min created_at, id tiebreak — provenance root) and
supersede the rest with it. Reversible: superseding is the store's own mechanism and
every change is journaled to ``~/.engram/maintenance/dedup_exact_<ts>.json``.

    python -m scripts.dedup_exact_facts            # DRY-RUN
    python -m scripts.dedup_exact_facts --apply    # execute + undo journal
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
from pathlib import Path

_DB = Path.home() / ".engram" / "semantic" / "semantic.db"
_UNDO_DIR = Path.home() / ".engram" / "maintenance"
_WS = re.compile(r"\s+")


def _norm(prop: str) -> str:
    return _WS.sub(" ", (prop or "").strip())


def plan_dedup(rows: list[dict]) -> list[dict]:
    """Pure: group live rows by normalized proposition; the earliest member wins,
    the rest lose. Whitespace-only propositions are ignored (not real facts).
    Returns [{key, winner_id, loser_ids}] for groups with >1 member, sorted by
    descending group size (biggest wins first, deterministic)."""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        key = _norm(r.get("proposition", ""))
        if not key:
            continue
        groups.setdefault(key, []).append(r)
    plan = []
    for key, members in groups.items():
        if len(members) < 2:
            continue
        ordered = sorted(members, key=lambda r: (float(r.get("created_at") or 0),
                                                 str(r.get("id"))))
        plan.append({"key": key[:120], "winner_id": str(ordered[0]["id"]),
                     "loser_ids": [str(r["id"]) for r in ordered[1:]]})
    plan.sort(key=lambda p: -len(p["loser_ids"]))
    return plan


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(_DB))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)

    con = sqlite3.connect(f"file:{Path(a.db).as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT id, proposition, topic, created_at FROM facts WHERE "
        "(superseded_by IS NULL OR superseded_by='') AND proposition != ''")]
    con.close()

    plan = plan_dedup(rows)
    n_losers = sum(len(p["loser_ids"]) for p in plan)
    print(json.dumps({
        "live_facts": len(rows), "dup_groups": len(plan),
        "would_supersede": n_losers,
        "top_groups": [{"n": len(p["loser_ids"]) + 1, "text": p["key"]}
                       for p in plan[:8]],
        "mode": "apply" if a.apply else "DRY-RUN",
    }, indent=2))
    if not a.apply or not plan:
        return 0

    from engram.semantic import SemanticMemory
    sm = SemanticMemory(db_path=Path(a.db))
    undo = {"created": time.time(), "db": str(a.db),
            "note": "restore = clear superseded_by/at/reason on each loser id",
            "entries": []}
    done = errors = 0
    for p in plan:
        for lid in p["loser_ids"]:
            try:
                r = sm.supersede(lid, p["winner_id"],
                                 reason="exact-text dedup (corpus truth scan "
                                        "2026-07-02; byte-identical proposition)")
                ok = bool(r.get("ok", True))
            except Exception as exc:  # noqa: BLE001
                ok = False
                errors += 1
                print(f"ERROR superseding {lid}: {exc!r}")
            if ok:
                done += 1
                undo["entries"].append({"loser_id": lid, "winner_id": p["winner_id"]})
    _UNDO_DIR.mkdir(parents=True, exist_ok=True)
    undo_path = _UNDO_DIR / f"dedup_exact_{int(time.time())}.json"
    undo_path.write_text(json.dumps(undo, indent=2), encoding="utf-8")

    con = sqlite3.connect(f"file:{Path(a.db).as_posix()}?mode=ro", uri=True)
    live = con.execute("SELECT COUNT(*) FROM facts WHERE (superseded_by IS NULL "
                       "OR superseded_by='')").fetchone()[0]
    con.close()
    print(json.dumps({"superseded": done, "errors": errors,
                      "live_now": live, "undo_file": str(undo_path)}, indent=2))
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
