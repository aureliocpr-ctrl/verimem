"""Cycle 222 (2026-05-23) — disk persistence for emergent skill drafts.

Adds an audit trail layer on top of the cycle 217 ``draft_skill_from_community``
output. Every batch of drafts is written to::

    <root_dir>/<YYYYMMDD-HHMMSS>/<skill_name>.md
    <root_dir>/<YYYYMMDD-HHMMSS>/<skill_name>.meta.json

so the user (and future Auto-Dream cycles) can `ls + cat` the directory
to track which emergent skills have surfaced over time. The default
caller location is ``~/.engram/skill_drafts/`` but the path is fully
parameterised.

Defensive
---------
* Empty list → no directory created.
* Empty / missing ``skill_name`` → that draft skipped.
* Path-traversal-style names (``../foo``) → sanitised by replacing
  every non-alphanumeric run with ``_``.
* ``root_dir`` is created with ``mkdir(parents=True)`` if missing.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

#: Allowed chars in a sanitised filename.  Anything else collapses to ``_``.
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_name(raw: str) -> str:
    """Make a filename safe: strip path separators, collapse unsafe runs."""
    s = (raw or "").strip()
    if not s:
        return ""
    # Replace path separators + control chars + unsafe runs.
    s = _SAFE_NAME_RE.sub("_", s)
    # Collapse runs of ``_`` and trim.
    s = re.sub(r"_+", "_", s).strip("._-")
    # Final defensive cap on length.
    return s[:120]


def persist_drafts(
    drafts: list[dict[str, Any]],
    *,
    root_dir: Path | str,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Write each draft to a timestamped subdirectory of ``root_dir``.

    Args:
        drafts: list of dicts as produced by
            ``engram.skill_drafter.draft_skill_from_community``.
        root_dir: parent directory; created if missing.
        timestamp: override for the subdir name (mainly for tests).
            Defaults to ``YYYYMMDD-HHMMSS`` of the current local time.

    Returns:
        ``{"n_written": int, "batch_dir": str, "skipped": int}``.
        ``batch_dir`` is the path of the created subdir (or "" when
        no drafts written).
    """
    if not drafts:
        return {"n_written": 0, "batch_dir": "", "skipped": 0}

    root = Path(root_dir)
    if timestamp is None:
        timestamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())

    batch_dir = root / timestamp
    # Don't create dirs until we have at least one valid draft.
    n_written = 0
    skipped = 0

    used_names: set[str] = set()
    for d in drafts:
        raw_name = str(d.get("skill_name", "") or "")
        safe_name = _sanitize_name(raw_name)
        if not safe_name:
            skipped += 1
            continue

        # Cycle 222.1: when two drafts share a normalised name (e.g.
        # the corpus produces two `emerging_skill_master-fact`
        # communities with identical family key), append the
        # community_id so neither overwrites the other.
        if safe_name in used_names:
            evidence = d.get("evidence", {}) or {}
            cid = _sanitize_name(str(evidence.get("community_id", "")))
            if cid:
                safe_name = f"{safe_name}__{cid}"
            else:
                # Last-resort numeric suffix.
                i = 2
                while f"{safe_name}__{i}" in used_names:
                    i += 1
                safe_name = f"{safe_name}__{i}"
        used_names.add(safe_name)

        # Create root + batch dir lazily on the first valid draft.
        if n_written == 0:
            batch_dir.mkdir(parents=True, exist_ok=True)

        md_path = batch_dir / f"{safe_name}.md"
        meta_path = batch_dir / f"{safe_name}.meta.json"

        md_text = str(d.get("draft_text", "") or "")
        md_path.write_text(md_text, encoding="utf-8")

        meta_obj = {
            "skill_name": d.get("skill_name", ""),
            "trigger_keywords": list(d.get("trigger_keywords", []) or []),
            "fact_ids": list(d.get("fact_ids", []) or []),
            "evidence": dict(d.get("evidence", {}) or {}),
        }
        meta_path.write_text(
            json.dumps(meta_obj, ensure_ascii=False, indent=2,
                       default=str),
            encoding="utf-8",
        )
        n_written += 1

    return {
        "n_written": n_written,
        "batch_dir": str(batch_dir) if n_written else "",
        "skipped": skipped,
    }


__all__ = ["persist_drafts"]
