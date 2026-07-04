"""CYCLE #28 — skill dedup per (name, status) identici.

Bug scoperto live: 318 skill totali, 75 paia con cosine ≥0.95 — molte
sono dup ESATTI (stesso name, stesso status). Top: 15x "Use ReAct
format for trivial repeat tasks" candidate. Significa che il sleep
cycle (REM cross-over / nrem extraction) crea nuove skill invece di
re-usare la esistente quando il body è praticamente identico.

Strategia (safe, retire-by-name-collision):
  Raggruppa skill per (name, status).
  Per ogni gruppo con count > 1:
    - winner = skill con max trials (signal evolutivo migliore)
    - tiebreaker: created_at più recente
    - losers → status='retired' (non delete, recuperabile via skill_recover)

NON tocca:
  - promoted skill (presunte stabili, dedup richiede review umano)
  - skill di gruppi diversi (name diverso = funzionalità diversa anche se
    semantica simile — usare skill_semantic_dedup separato)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

_LOG = logging.getLogger(__name__)


def find_name_duplicate_groups(skills: list[Any]) -> list[dict[str, Any]]:
    """Ritorna gruppi di skill con (name, status) identici, sorted by count desc."""
    by_key: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for s in skills:
        name = (getattr(s, "name", "") or "").strip()
        status = getattr(s, "status", "")
        if not name:
            continue
        by_key[(name, status)].append(s)

    groups = []
    for (name, status), members in by_key.items():
        if len(members) <= 1:
            continue
        # Winner: max trials, tiebreaker created_at desc
        ranked = sorted(
            members,
            key=lambda s: (
                getattr(s, "trials", 0),
                getattr(s, "created_at", 0.0),
            ),
            reverse=True,
        )
        winner = ranked[0]
        losers = ranked[1:]
        groups.append({
            "name": name,
            "status": status,
            "count": len(members),
            "winner_id": getattr(winner, "id", ""),
            "winner_trials": int(getattr(winner, "trials", 0)),
            "loser_ids": [getattr(s, "id", "") for s in losers],
        })
    groups.sort(key=lambda g: -g["count"])
    return groups


def dedup_skills_by_name(
    skills_store: Any,
    *,
    apply: bool = False,
    max_retire: int = 200,
    only_status: str | None = "candidate",
) -> dict[str, Any]:
    """Retire skill duplicate per nome.

    Args:
        skills_store: SkillLibrary instance (has .all() and .store()).
        apply: False = dry-run. True = applica retire.
        max_retire: cap di sicurezza.
        only_status: filtra solo questo status (default "candidate" —
            mai toccare promoted senza review esplicito).

    Returns:
        {
          "dry_run": bool,
          "groups_found": int,
          "total_skills": int,
          "skills_to_retire": int,
          "applied_retired": int,
          "applied_skipped_cap": int,
          "preview_groups": top 20 by count,
        }
    """
    all_sk = list(skills_store.all())
    if only_status:
        all_sk_filtered = [s for s in all_sk if getattr(s, "status", "") == only_status]
    else:
        all_sk_filtered = all_sk
    groups = find_name_duplicate_groups(all_sk_filtered)

    losers_total: list[str] = []
    for g in groups:
        losers_total.extend(g["loser_ids"])

    applied = 0
    failed = 0
    skipped_cap = 0
    if apply:
        for lid in losers_total:
            if applied >= max_retire:
                skipped_cap = len(losers_total) - applied
                break
            try:
                s = skills_store.get(lid)
                if s is None or getattr(s, "status", "") == "retired":
                    continue
                s.status = "retired"
                skills_store.store(s)
                applied += 1
            except Exception:
                # Scan #29: a failed store() (disk/lock/validation) used to be
                # swallowed silently, so applied_retired under-counted with no
                # trace. Count + log it so the operator sees the partial result.
                failed += 1
                _LOG.warning("dedup retire failed for skill %s", lid,
                             exc_info=True)

    preview = [
        {
            "name": g["name"][:80],
            "status": g["status"],
            "count": g["count"],
            "winner_id": g["winner_id"],
            "winner_trials": g["winner_trials"],
            "n_losers": len(g["loser_ids"]),
        }
        for g in groups[:20]
    ]

    return {
        "dry_run": not apply,
        "groups_found": len(groups),
        "total_skills": len(all_sk),
        "skills_to_retire": len(losers_total),
        "applied_retired": applied,
        "applied_failed": failed,
        "applied_skipped_cap": skipped_cap,
        "preview_groups": preview,
    }


__all__ = ["find_name_duplicate_groups", "dedup_skills_by_name"]
