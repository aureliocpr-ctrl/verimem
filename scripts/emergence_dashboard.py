"""Cycle 238 (2026-05-23) — emergence pipeline observability dashboard.

Aggregates the cycle 213-237 pipeline state from disk + DB into a
single textual report. Useful for empirical reviews + cross-instance
handoff.

Reports:
  1. Active emerging_skill/* facts in semantic.db (with confidence,
     lineage_to anchor).
  2. Auto-Dream disk batches under ~/.engram/skill_drafts/.
  3. Candidate Skill rows (stage=manual) in skills_index.db.
  4. Last Auto-Dream firing timestamp + dream_id.

Usage::

    python -m scripts.emergence_dashboard
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path


def _format_age(epoch: float) -> str:
    delta = max(0, int(time.time() - epoch))
    if delta < 60:
        return f"{delta}s ago"
    if delta < 3600:
        return f"{delta // 60}m ago"
    if delta < 86400:
        return f"{delta // 3600}h ago"
    return f"{delta // 86400}d ago"


def report_emerging_facts(semantic_db: Path) -> dict:
    if not semantic_db.exists():
        return {"n": 0, "facts": []}
    try:
        conn = sqlite3.connect(str(semantic_db))
        try:
            rows = conn.execute(
                "SELECT id, topic, confidence, lineage_to, created_at "
                "FROM facts WHERE topic LIKE 'emerging_skill/%' "
                "ORDER BY confidence DESC, created_at DESC LIMIT 20",
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return {"n": 0, "facts": [], "error": str(exc)}
    facts = [
        {
            "id": r[0],
            "topic": r[1],
            "confidence": float(r[2] or 0.0),
            "lineage_to": r[3],
            "age": _format_age(float(r[4] or 0.0)),
        }
        for r in rows
    ]
    return {"n": len(facts), "facts": facts}


def report_disk_batches(drafts_root: Path) -> dict:
    if not drafts_root.exists():
        return {"n_batches": 0, "batches": []}
    batches = sorted(
        (p for p in drafts_root.iterdir() if p.is_dir()),
        reverse=True,
    )[:10]
    return {
        "n_batches": len(list(drafts_root.iterdir())),
        "batches": [
            {
                "batch_id": b.name,
                "n_drafts": len(list(b.glob("*.md"))),
            }
            for b in batches
        ],
    }


def report_candidate_skills(skills_db: Path) -> dict:
    if not skills_db.exists():
        return {"n": 0, "skills": []}
    try:
        conn = sqlite3.connect(str(skills_db))
        try:
            rows = conn.execute(
                "SELECT id, name, status, stage, trials, successes "
                "FROM skills WHERE stage = 'manual' "
                "AND status = 'candidate' "
                "ORDER BY created_at DESC LIMIT 20",
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return {"n": 0, "skills": [], "error": str(exc)}
    skills = [
        {
            "id": r[0], "name": r[1], "status": r[2],
            "stage": r[3], "trials": int(r[4] or 0),
            "successes": int(r[5] or 0),
        }
        for r in rows
    ]
    return {"n": len(skills), "skills": skills}


def report_last_dream(engram_dir: Path) -> dict:
    last_path = engram_dir / "auto_dream_last.json"
    if not last_path.exists():
        return {"present": False}
    try:
        data = json.loads(last_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {"present": True, "error": str(exc)}
    finished = float(data.get("worker_finished_at", 0.0))
    data["age"] = _format_age(finished) if finished else "unknown"
    return {"present": True, **data}


def render(engram_dir: Path) -> str:
    facts = report_emerging_facts(
        engram_dir / "semantic" / "semantic.db",
    )
    batches = report_disk_batches(engram_dir / "skill_drafts")
    skills = report_candidate_skills(
        engram_dir / "skills" / "skills_index.db",
    )
    last = report_last_dream(engram_dir)

    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("HippoAgent Emergence Pipeline Dashboard (cycle 213-237)")
    lines.append("=" * 70)
    lines.append(f"\n[1] emerging_skill/* facts in semantic.db: {facts['n']}")
    for f in facts.get("facts", [])[:10]:
        lin = (f["lineage_to"] or "")[:8] or "-"
        lines.append(
            f"  - [{f['id'][:8]}] conf={f['confidence']:.3f} "
            f"lineage→{lin}  {f['topic']}  ({f['age']})",
        )

    lines.append(f"\n[2] disk batches under skill_drafts/: {batches['n_batches']} (10 most recent)")
    for b in batches["batches"]:
        lines.append(f"  - {b['batch_id']} ({b['n_drafts']} drafts)")

    lines.append(f"\n[3] candidate Skills (stage=manual): {skills['n']}")
    for s in skills.get("skills", []):
        lines.append(
            f"  - [{s['id'][:10]}] {s['name']!r}  "
            f"trials={s['trials']}  successes={s['successes']}",
        )

    lines.append("\n[4] last Auto-Dream firing:")
    if last.get("present"):
        lines.append(
            f"  dream_id: {last.get('dream_id', '?')}  "
            f"age: {last.get('age', '?')}  "
            f"new_items: {last.get('new_items', 0)}",
        )
    else:
        lines.append("  (no auto_dream_last.json present)")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    engram_dir = Path.home() / ".engram"
    print(render(engram_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
