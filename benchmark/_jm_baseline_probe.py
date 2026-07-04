"""Read-only baseline probe: current Justified-Memory state on the REAL corpus.

Confirms R23 empirically (propagate dormant because derives_from is ~empty live) and
measures the would-retract exposure. Operates on a COPY of the live semantic.db to avoid
any lock contention. No mutation. Throwaway diagnostic (not a test)."""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

from engram.justified_memory import audit_facts
from benchmark.lineage_cascade_exposure import run as lineage_exposure

LIVE = Path.home() / ".engram" / "semantic" / "semantic.db"


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="jm_probe_")) / "copy.db"
    shutil.copy2(LIVE, tmp)
    conn = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, proposition, topic, status, superseded_by, derives_from, valid_until "
        "FROM facts"
    ).fetchall()
    conn.close()

    facts = []
    for r in rows:
        df_raw = r["derives_from"] or ""
        facts.append({
            "id": r["id"],
            "proposition": r["proposition"] or "",
            "topic": r["topic"] or "",
            "status": r["status"] or "",
            "superseded_by": r["superseded_by"] or None,
            "derives_from": [s for s in df_raw.split(",") if s],
            "valid_until": r["valid_until"],
        })

    n = len(facts)
    n_with_df = sum(1 for f in facts if f["derives_from"])
    n_superseded = sum(1 for f in facts if f["superseded_by"])
    # foundations = facts that are cited as a derives_from parent by someone
    parents = set()
    for f in facts:
        parents.update(f["derives_from"])
    n_foundations = sum(1 for f in facts if f["id"] in parents)

    audit = audit_facts(facts, now=time.time())

    print("=== Justified-Memory BASELINE (live corpus copy, read-only) ===")
    print(f"db                : {LIVE}")
    print(f"total facts        : {n}")
    print(f"superseded (input) : {n_superseded}")
    print(f"facts WITH derives_from (typed logical edge populated): {n_with_df}")
    print(f"facts that ARE a derivation parent (foundations)      : {n_foundations}")
    print(f"audit.served       : {audit['served']}")
    print(f"would_retract      : {len(audit['would_retract_ids'])}")
    print(f"would_stale        : {len(audit['would_stale_ids'])}")
    print(f"status_counts      : {audit['status_counts']}")
    print(f"--> propagate cascade CAN fire only if facts have derives_from parents that get "
          f"superseded. With n_with_df={n_with_df}, propagate is DORMANT (confirms R23)."
          if n_with_df == 0 else
          f"--> {n_with_df} facts carry a typed edge; propagate cascade is reachable.")


if __name__ == "__main__":
    main()
