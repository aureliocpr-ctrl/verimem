"""Dedup degli episodi duplicati nel corpus.

CYCLE #9 — discovery empirica: 562 episodi totali, ma solo 117 task_text
distinct (28 gruppi con duplicati). 164x "task one", 164x "task two"
sono FIXTURE DI TEST che inquinano il DB di produzione (qualcuno ha
runnato test senza isolare HIPPO_DATA_DIR). Effetti:
  - `hippo_recall` ritorna duplicati esatti → context pollution
  - Embedding del cluster "task one/two" attira similarità verso noise
  - Metriche corpus_health misleading: il segnale utile è 117 ep, non 562

Strategia dedup STRETTA (safe):
  Raggruppa per la chiave `(task_text, final_answer, outcome)`. Per ogni
  gruppo con count>1: tieni l'episodio più recente (max created_at),
  delete gli altri.

  Episodi con final_answer diversi NON vengono fusi anche se task_text
  è uguale — preserva diversità di soluzioni per lo stesso task.

API:
  find_duplicate_groups(memory) → list[dict]
  dedup_episodes(memory, apply=False) → dict report

I caller (CLI / MCP tool) decidono apply. Default dry-run.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from .memory import EpisodicMemory


def _key(row: sqlite3.Row | dict[str, Any]) -> tuple[str, str, str]:
    """Strict dedup key. None / NULL normalised to empty string."""
    return (
        (row["task_text"] or "")[:8000],
        (row["final_answer"] or "")[:8000],
        (row["outcome"] or ""),
    )


def find_duplicate_groups(memory: EpisodicMemory) -> list[dict[str, Any]]:
    """Ritorna i gruppi di episodi con chiave dedup duplicata.

    Args:
        memory: EpisodicMemory instance (uses `episodes_db` path).

    Returns:
        Lista di dict ordinata per count decrescente:
        [{
          "task_text": str,
          "final_answer": str,
          "outcome": str,
          "count": int,
          "ids": list[str],                # tutti gli id del gruppo
          "winner_id": str,                # most recent (sopravvive)
          "loser_ids": list[str],          # quelli da rimuovere
        }, ...]
    """
    with sqlite3.connect(memory.db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, task_text, final_answer, outcome, created_at "
            "FROM episodes ORDER BY created_at DESC"
        ).fetchall()

    by_key: dict[tuple[str, str, str], list[sqlite3.Row]] = {}
    for r in rows:
        by_key.setdefault(_key(r), []).append(r)

    groups: list[dict[str, Any]] = []
    for key, members in by_key.items():
        if len(members) <= 1:
            continue
        # members già sorted DESC per created_at (winner = members[0]).
        winner = members[0]
        losers = members[1:]
        groups.append({
            "task_text": key[0],
            "final_answer": key[1],
            "outcome": key[2],
            "count": len(members),
            "ids": [r["id"] for r in members],
            "winner_id": winner["id"],
            "loser_ids": [r["id"] for r in losers],
            "winner_created_at": float(winner["created_at"]),
        })
    groups.sort(key=lambda g: -g["count"])
    return groups


def dedup_episodes(
    memory: EpisodicMemory,
    *,
    apply: bool = False,
    max_remove: int = 1000,
) -> dict[str, Any]:
    """Esegue (o simula) il dedup degli episodi.

    Args:
        memory: EpisodicMemory live.
        apply: se False (default) → dry run, nessun delete.
        max_remove: cap di sicurezza sul numero di delete per singola call.

    Returns:
        {
          "dry_run": bool,
          "groups_found": int,
          "episodes_total": int,
          "episodes_to_remove": int,
          "applied_removed": int,
          "applied_skipped_cap": int,
          "preview_groups": list[dict] (top 20 by count, senza ids elenco completo),
        }
    """
    groups = find_duplicate_groups(memory)
    with sqlite3.connect(memory.db_path) as conn:
        episodes_total = int(conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0])

    losers_total: list[str] = []
    for g in groups:
        losers_total.extend(g["loser_ids"])

    applied = 0
    skipped_cap = 0
    if apply:
        for lid in losers_total:
            if applied >= max_remove:
                skipped_cap = len(losers_total) - applied
                break
            try:
                if memory.delete(lid):
                    applied += 1
            except Exception:
                # Singola failure non blocca il batch.
                pass

    preview = []
    for g in groups[:20]:
        preview.append({
            "task_text": g["task_text"][:100],
            "final_answer": g["final_answer"][:80],
            "outcome": g["outcome"],
            "count": g["count"],
            "winner_id": g["winner_id"],
            "n_losers": len(g["loser_ids"]),
        })

    return {
        "dry_run": not apply,
        "groups_found": len(groups),
        "episodes_total": episodes_total,
        "episodes_to_remove": len(losers_total),
        "applied_removed": applied,
        "applied_skipped_cap": skipped_cap,
        "preview_groups": preview,
    }


__all__ = ["find_duplicate_groups", "dedup_episodes"]
