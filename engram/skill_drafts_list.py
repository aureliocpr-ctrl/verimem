"""Cycle 227 (2026-05-23) — list persisted skill drafts.

Reads the on-disk layout produced by cycle 222 ``persist_drafts``::

    <root>/<YYYYMMDD-HHMMSS>/<skill_name>.md
    <root>/<YYYYMMDD-HHMMSS>/<skill_name>.meta.json

and returns a structured listing, newest batch first. Used by the
cycle 228 MCP tool ``hippo_skill_drafts_list`` to surface the
audit trail to MCP clients (Claude Code, Cursor, ...).

Defensive
---------
* Missing / empty root → ``{"n_batches": 0, "batches": []}``.
* Corrupt meta JSON → draft listed with ``evidence={}``.
* Orphan ``.md`` without ``.meta.json`` → draft listed with
  ``evidence={}``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def list_persisted_drafts(
    root_dir: Path | str,
    *,
    max_batches: int = 10,
    max_drafts_per_batch: int = 50,
) -> dict[str, Any]:
    """List persisted draft batches, newest first.

    Args:
        root_dir: parent directory (e.g. ``~/.engram/skill_drafts``).
        max_batches: cap on returned batches (newest survive).
        max_drafts_per_batch: cap on drafts surfaced per batch.

    Returns:
        ``{"n_batches": int, "batches": [{
              "batch_id": str,           # the YYYYMMDD-HHMMSS dir name
              "n_drafts": int,
              "drafts": [
                 {"skill_name", "trigger_keywords",
                  "fact_ids", "evidence"},
                 ...
              ],
           }, ...]}``
    """
    root = Path(root_dir)
    if not root.exists() or not root.is_dir():
        return {"n_batches": 0, "batches": []}

    # List subdirs only (each is a YYYYMMDD-HHMMSS batch).
    subdirs = sorted(
        (p for p in root.iterdir() if p.is_dir()),
        reverse=True,  # newest first by lexicographic timestamp
    )
    if not subdirs:
        return {"n_batches": 0, "batches": []}

    out_batches: list[dict[str, Any]] = []
    for sub in subdirs[: int(max_batches)]:
        md_files = sorted(sub.glob("*.md"))
        drafts: list[dict[str, Any]] = []
        for md in md_files[: int(max_drafts_per_batch)]:
            skill_name = md.stem
            meta_path = md.with_suffix("").with_suffix(".meta.json")
            # `md.with_suffix("").with_suffix(".meta.json")` strips
            # .md and adds .meta.json — but if filename has dots
            # already (e.g. cycle 222.1 __c-010), with_suffix may
            # not roundtrip. Build path manually:
            meta_path = md.parent / f"{skill_name}.meta.json"
            evidence: dict[str, Any] = {}
            trigger_keywords: list[str] = []
            fact_ids: list[str] = []
            if meta_path.exists():
                try:
                    loaded = json.loads(
                        meta_path.read_text(encoding="utf-8"),
                    )
                except (json.JSONDecodeError, OSError):
                    loaded = None
                if isinstance(loaded, dict):
                    evidence = dict(loaded.get("evidence", {}) or {})
                    trigger_keywords = list(
                        loaded.get("trigger_keywords", []) or [],
                    )
                    fact_ids = list(loaded.get("fact_ids", []) or [])
                    # Allow meta to override skill_name when present.
                    skill_name = str(
                        loaded.get("skill_name", skill_name) or skill_name,
                    )
            drafts.append({
                "skill_name": skill_name,
                "trigger_keywords": trigger_keywords,
                "fact_ids": fact_ids,
                "evidence": evidence,
            })
        out_batches.append({
            "batch_id": sub.name,
            "n_drafts": len(drafts),
            "drafts": drafts,
        })

    return {"n_batches": len(out_batches), "batches": out_batches}


__all__ = ["list_persisted_drafts"]
