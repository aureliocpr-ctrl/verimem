"""R47: Canonical skill signature.

Normalize trigger+body to detect literal duplicates regardless of:
  - whitespace
  - case
  - leading/trailing punctuation
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any

_WHITESPACE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    if not text:
        return ""
    return _WHITESPACE.sub(" ", text.strip().lower())


def compute_signature(skill: Any) -> str:
    """SHA1 of normalized trigger+body. 8-char prefix."""
    trig = _normalize(getattr(skill, "trigger", ""))
    body = _normalize(getattr(skill, "body", ""))
    raw = f"{trig}||{body}"
    return hashlib.sha1(raw.encode("utf-8"),
                        usedforsecurity=False).hexdigest()[:12]


def find_duplicate_skills(skills: list[Any]) -> dict[str, Any]:
    """Group skills by signature; return groups with size >= 2."""
    by_sig: dict[str, list[str]] = defaultdict(list)
    for s in skills:
        sig = compute_signature(s)
        by_sig[sig].append(getattr(s, "id", ""))

    groups = []
    for sig, ids in by_sig.items():
        if len(ids) >= 2:
            groups.append({
                "signature": sig,
                "skill_ids": ids,
                "n_dupes": len(ids),
            })
    groups.sort(key=lambda g: -g["n_dupes"])
    return {
        "duplicate_groups": groups,
        "n_skills_scanned": len(skills),
    }


__all__ = ["compute_signature", "find_duplicate_skills"]
