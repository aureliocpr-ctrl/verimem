"""Disk-size report per memory tier.

FORGIA pezzo #227 — Wave 26. Pure filesystem inspection. Useful for
the user to answer "quanto pesa la mia memoria persistente?".
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _safe_size(path: Path) -> int:
    """File size or 0 if missing."""
    try:
        if path.is_file():
            return path.stat().st_size
    except Exception:
        pass
    return 0


def _dir_size(path: Path) -> tuple[int, int]:
    """(total bytes, file count) for a directory's immediate children
    (non-recursive). Returns (0, 0) on missing."""
    total = 0
    n = 0
    try:
        if path.is_dir():
            for child in path.iterdir():
                if child.is_file():
                    total += child.stat().st_size
                    n += 1
    except Exception:
        pass
    return total, n


def corpus_size_report(*, data_dir: Path) -> dict[str, Any]:
    """Return disk usage per memory tier.

    Args:
      - `data_dir`: HippoAgent data directory (e.g.
        `~/.hippoagent/data`).

    Returns: `{data_dir, episodes_bytes, semantic_bytes,
    skills_bytes, total_bytes, total_mb, n_skill_files}`. Missing
    tiers contribute 0 — never raises.
    """
    ep_bytes = _safe_size(data_dir / "episodes" / "episodes.db")
    # Schema-tolerant: try both new and legacy layouts.
    sem_bytes = _safe_size(data_dir / "semantic" / "semantic.db")
    if sem_bytes == 0:
        sem_bytes = _safe_size(data_dir / "semantic.db")
    skills_bytes, n_skill_files = _dir_size(data_dir / "skills")

    total = ep_bytes + sem_bytes + skills_bytes
    return {
        "data_dir": str(data_dir),
        "episodes_bytes": ep_bytes,
        "semantic_bytes": sem_bytes,
        "skills_bytes": skills_bytes,
        "total_bytes": total,
        "total_mb": total / (1024 * 1024),
        "n_skill_files": n_skill_files,
    }


__all__ = ["corpus_size_report"]
