"""Cycle 244 (2026-05-23) — H1 pilot baseline snapshot scaffold.

Cycle 175.2 task: measure whether the cycle 175.1 stuck-retry hook +
cycle 187 community hook + cycle 211 thompson hook + cycle 219
emergence hook (4-hook composition) raise the candidate-skill
promotion rate from the cycle-174 audit baseline (4.3 %) toward the
target (>10 %) over 20 Auto-Dream cycles.

This script takes a SNAPSHOT today + writes ``~/.engram/pilot_baseline.json``.
A future invocation will compute the delta.

Metrics captured:
  - total_skills, candidate, promoted, retired (per status)
  - promotion_rate = promoted / (candidate + promoted + retired)
  - n_emerging_skill_facts (cycle 229+)
  - n_auto_dream_firings_since (parsed from ~/.engram/dreams/)
  - last_dream_timestamp
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path


def _safe(fn):
    """Run fn, swallow exceptions and return None instead."""
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return None


def snapshot(engram_dir: Path) -> dict:
    sk_db = engram_dir / "skills" / "skills_index.db"
    se_db = engram_dir / "semantic" / "semantic.db"
    dreams_dir = engram_dir / "dreams"

    def _skill_counts():
        if not sk_db.exists():
            return {"total": 0, "candidate": 0, "promoted": 0, "retired": 0}
        conn = sqlite3.connect(str(sk_db))
        try:
            rows = conn.execute(
                "SELECT status, COUNT(*) FROM skills GROUP BY status",
            ).fetchall()
        finally:
            conn.close()
        d = dict(rows)
        return {
            "total": sum(d.values()),
            "candidate": int(d.get("candidate", 0)),
            "promoted": int(d.get("promoted", 0)),
            "retired": int(d.get("retired", 0)),
        }

    def _emerging_count():
        if not se_db.exists():
            return 0
        conn = sqlite3.connect(str(se_db))
        try:
            n = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE topic LIKE 'emerging_skill/%'",
            ).fetchone()[0]
        finally:
            conn.close()
        return int(n)

    def _dream_firings():
        if not dreams_dir.exists():
            return {"n_auto": 0, "last_ts": None}
        autos = sorted(
            d for d in dreams_dir.iterdir()
            if d.is_dir() and d.name.startswith("auto-")
        )
        last_ts = None
        if autos:
            # The dir name is `auto-<epoch>` (cycle 69 convention).
            last_name = autos[-1].name
            try:
                last_ts = int(last_name.split("-", 1)[1])
            except (ValueError, IndexError):
                last_ts = None
        return {"n_auto": len(autos), "last_ts": last_ts}

    sk = _safe(_skill_counts) or {}
    em = _safe(_emerging_count) or 0
    df = _safe(_dream_firings) or {}

    promotion_rate = 0.0
    denom = (
        sk.get("candidate", 0)
        + sk.get("promoted", 0)
        + sk.get("retired", 0)
    )
    if denom > 0:
        promotion_rate = sk.get("promoted", 0) / denom

    return {
        "captured_at": time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.localtime(),
        ),
        "captured_at_epoch": time.time(),
        "skills": sk,
        "promotion_rate": round(promotion_rate, 4),
        "promotion_rate_target": 0.10,
        "n_emerging_skill_facts": em,
        "dream_firings": df,
    }


def main(argv: list[str] | None = None) -> int:
    engram_dir = Path.home() / ".engram"
    out_path = engram_dir / "pilot_baseline.json"
    data = snapshot(engram_dir)

    # Preserve prior snapshot if any.
    history_path = engram_dir / "pilot_baseline_history.jsonl"
    if out_path.exists():
        try:
            history_path.parent.mkdir(parents=True, exist_ok=True)
            with history_path.open("a", encoding="utf-8") as h:
                h.write(out_path.read_text(encoding="utf-8").strip())
                h.write("\n")
        except OSError:
            pass

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
