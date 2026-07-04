"""Cycle 198 (2026-05-23) — betweenness centrality cache.

Closes gap §5 of docs/sota/highway-nodes-pagerank-cache.md (cycle 188).
File-backed cache around cycle-189 ``get_highway_nodes`` so the
expensive sampled betweenness (~150 ms on 1.7k corpus) doesn't run
on every recall.

Storage
-------
A small JSON file ``~/.engram/cache/betweenness_cache.json`` (or
caller-supplied path) with shape:

    {
      "semantic_db_path": str,
      "computed_at": float,
      "graph_signature": str,    # see _graph_signature() below
      "highways": [[id, score], ...]
    }

Invalidation policy
-------------------
Cache is **considered stale** if:
  * file is older than ``max_age_seconds`` (default 30 min — same
    cadence as Auto-Dream cycle, cycle #69), OR
  * ``graph_signature`` no longer matches (cheap structural hash on
    node count + edge count + max created_at — DOES NOT detect
    edits to old facts but cheap and "good enough" for the
    Auto-Dream cadence).

The MCP / Auto-Dream worker calls ``ensure_highway_cache`` once per
firing; recall hot-paths read from the file directly.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from engram.highway_nodes import get_highway_nodes

_DEFAULT_CACHE_NAME = "betweenness_cache.json"
_DEFAULT_MAX_AGE_S = 30 * 60.0  # 30 min, matches Auto-Dream cadence


def _graph_signature(db_path: Path) -> str:
    """Cheap structural hash: ``node_count.edge_count.max_created_at``.

    Doesn't catch in-place edits to old facts but catches any
    insert / delete / supersession event in O(2-row-COUNT) SQL.
    """
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            n = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL"
            ).fetchone()[0]
            max_ts = conn.execute(
                "SELECT COALESCE(MAX(created_at), 0) FROM facts "
                "WHERE superseded_by IS NULL"
            ).fetchone()[0]
            try:
                m = conn.execute(
                    "SELECT COUNT(*) FROM causal_edges"
                ).fetchone()[0]
            except sqlite3.OperationalError:
                m = 0
        finally:
            conn.close()
    except sqlite3.Error:
        return ""
    return f"{int(n)}.{int(m)}.{float(max_ts or 0):.0f}"


def _read_cache(cache_path: Path) -> dict[str, Any] | None:
    if not cache_path.exists():
        return None
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(cache_path: Path, payload: dict[str, Any]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def ensure_highway_cache(
    semantic_db: Path | str,
    *,
    cache_dir: Path | str | None = None,
    max_age_seconds: float = _DEFAULT_MAX_AGE_S,
    k: int = 50,
    sample_size: int = 500,
    force_refresh: bool = False,
) -> list[tuple[str, float]]:
    """Return top-K highway nodes, refreshing the cache if stale.

    Args:
        semantic_db: path to ``semantic.db``.
        cache_dir: directory for the cache file. Defaults to
            ``<semantic_db.parent>/.engram_cache``.
        max_age_seconds: cache lifetime. Older → recompute.
        k: passed to ``get_highway_nodes``.
        sample_size: passed to ``get_highway_nodes``.
        force_refresh: bypass cache + recompute.

    Returns:
        ``[(fact_id, betweenness_score), ...]``. Empty list when the
        underlying ``get_highway_nodes`` returns empty.
    """
    db_path = Path(semantic_db)
    if not db_path.exists():
        return []

    cd = Path(cache_dir) if cache_dir is not None else (
        db_path.parent / ".engram_cache"
    )
    cache_path = cd / _DEFAULT_CACHE_NAME

    if not force_refresh:
        cached = _read_cache(cache_path)
        if cached is not None:
            age = time.time() - float(cached.get("computed_at", 0.0))
            current_sig = _graph_signature(db_path)
            if (
                age < max_age_seconds
                and cached.get("graph_signature") == current_sig
                and cached.get("semantic_db_path") == str(db_path)
            ):
                # Cache hit + fresh + graph-unchanged.
                highways = cached.get("highways") or []
                return [
                    (str(h[0]), float(h[1]))
                    for h in highways
                    if isinstance(h, (list, tuple)) and len(h) >= 2
                ]

    # Cache miss / stale / forced → recompute.
    highways = get_highway_nodes(
        db_path, k=int(k), sample_size=int(sample_size),
    )
    payload: dict[str, Any] = {
        "semantic_db_path": str(db_path),
        "computed_at": time.time(),
        "graph_signature": _graph_signature(db_path),
        "highways": [[fid, sc] for fid, sc in highways],
    }
    try:
        _write_cache(cache_path, payload)
    except OSError:
        # Cache write failure must not break the read path.
        pass
    return highways


__all__ = ["ensure_highway_cache"]
