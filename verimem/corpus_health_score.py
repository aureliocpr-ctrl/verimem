"""Composite corpus health score (0-100).

FORGIA pezzo #272 — Wave 71. Combines:
  - % success rate on episodes (40%)
  - % promoted skills (30%)
  - avg fitness across promoted (20%)
  - inverse fragility (no cycles, low isolated rate) (10%)
"""
from __future__ import annotations

from typing import Any


def _safe_div(a: float, b: float) -> float:
    return a / b if b > 0 else 0.0


def _count_lineage_connected(skills_store: Any, skill_ids: set[str]) -> int:
    """LEGACY (cycle #29) — count skill in skill_lineage as parent OR child.

    Mantenuta per backward compat / tooling esterno. compute_health_score
    ora usa _compute_lineage_metrics (cycle #32) per discriminatività.
    """
    import sqlite3
    db_path = getattr(skills_store, "db_path", None)
    if db_path is None or not skill_ids:
        return 0
    placeholders = ",".join("?" * len(skill_ids))
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                f"""SELECT COUNT(DISTINCT id) FROM (
                    SELECT parent_id AS id FROM skill_lineage
                    UNION
                    SELECT child_id AS id FROM skill_lineage
                ) WHERE id IN ({placeholders})""",
                tuple(skill_ids),
            ).fetchone()
        return int(row[0]) if row else 0
    except (sqlite3.OperationalError, Exception):
        return 0


def _compute_lineage_metrics(
    skills_store: Any,
    skill_ids: set[str],
    *,
    relation: str | None = "derived_from",
) -> tuple[int, int]:
    """CYCLE #32 (refined CYCLE #33): ritorna (n_with_alive_parent, n_with_alive_child).

    CYCLE #33: filter `relation` default 'derived_from'. Audit live ha
    rivelato che 96% degli edges sono 'specialises' (schema-clustering, non
    vera derivazione). Mescolarli gonfiava fecundity (es. schema-root
    "ReAct format" appariva con 133 children → falsa fertilità). 'specialises'
    è clustering retrospettivo, non genealogia evolutiva. Pass `relation=None`
    per legacy behavior (tutti gli edges).

    Importante: conta SOLO edges alive↔alive (subset del skill_ids passato),
    perché retired sono già esclusi dal corpus attivo.
    """
    import sqlite3
    db_path = getattr(skills_store, "db_path", None)
    if db_path is None or not skill_ids:
        return (0, 0)
    placeholders = ",".join("?" * len(skill_ids))
    ids_tuple = tuple(skill_ids)
    rel_clause = " AND relation = ?" if relation is not None else ""
    rel_params: tuple = (relation,) if relation is not None else ()
    try:
        with sqlite3.connect(db_path) as conn:
            n_with_parent = conn.execute(
                f"""SELECT COUNT(DISTINCT child_id) FROM skill_lineage
                    WHERE child_id IN ({placeholders})
                    AND parent_id IN ({placeholders}){rel_clause}""",
                ids_tuple + ids_tuple + rel_params,
            ).fetchone()[0]
            n_with_child = conn.execute(
                f"""SELECT COUNT(DISTINCT parent_id) FROM skill_lineage
                    WHERE parent_id IN ({placeholders})
                    AND child_id IN ({placeholders}){rel_clause}""",
                ids_tuple + ids_tuple + rel_params,
            ).fetchone()[0]
        return (int(n_with_parent), int(n_with_child))
    except (sqlite3.OperationalError, Exception):
        return (0, 0)


def compute_health_score(*, agent: Any) -> dict[str, Any]:
    """Return `{score, components, verdict}` score in [0, 100].

    CYCLE #31: filtra retired dal corpus prima di calcolare le metriche.
    Bug live (pre-fix): 318 skill di cui 148 retired (47%). promoted_frac
    = 5/318 = 1.5% (matematicamente corretta ma fuorviante: 5/170 attive
    = 2.94%). connect_frac saturato a 1.0 perché i retired contano nel
    denominatore. Retired = morte → non rilevanti per la salute del
    corpus attivo. Stesso principio già usato in skill_top/skill_search.
    """
    skills_store = getattr(agent, "skills", None)
    memory = getattr(agent, "memory", None)

    skills: list[Any] = []
    if skills_store is not None and hasattr(skills_store, "all"):
        try:
            skills = list(skills_store.all())
        except Exception:
            skills = []
    # CYCLE #31: escludi retired (morte) — non contano per la salute attiva.
    skills = [s for s in skills if getattr(s, "status", "") != "retired"]

    eps: list[Any] = []
    if memory is not None and hasattr(memory, "all"):
        try:
            eps = list(memory.all())
        except Exception:
            eps = []

    # Component 1: success rate.
    n_success = sum(
        1 for e in eps if getattr(e, "outcome", "") == "success"
    )
    n_failure = sum(
        1 for e in eps if getattr(e, "outcome", "") == "failure"
    )
    n_total_ep = n_success + n_failure
    success_rate = _safe_div(n_success, n_total_ep) if n_total_ep > 0 else 0.5

    # Component 2: promoted fraction.
    n_promoted = sum(1 for s in skills if s.status == "promoted")
    promoted_frac = _safe_div(n_promoted, len(skills)) if skills else 0.0

    # Component 3: avg fitness of promoted.
    promoted_fitnesses = [
        float(s.fitness_mean) for s in skills if s.status == "promoted"
    ]
    avg_fitness = (
        sum(promoted_fitnesses) / len(promoted_fitnesses)
        if promoted_fitnesses else 0.5
    )

    # Component 4: connectedness — CYCLE #32 metrica composta.
    # = mean(derivedness, fecundity) dove
    #   derivedness = frac alive con alive-parent (skill che deriva da apprendimento)
    #   fecundity  = frac alive con alive-child  (skill che genera derivazioni)
    # Non satura a 1.0 (richiederebbe ogni nodo interno = no root, no leaf).
    # Su corpus reale (170 alive): 141 with_parent, 56 with_child → mean ≈ 0.58.
    skill_ids = {s.id for s in skills}
    if skill_ids and skills_store is not None:
        n_with_parent, n_with_child = _compute_lineage_metrics(skills_store, skill_ids)
    else:
        n_with_parent = n_with_child = 0
    if skills:
        derivedness = _safe_div(n_with_parent, len(skills))
        fecundity = _safe_div(n_with_child, len(skills))
        connect_frac = (derivedness + fecundity) / 2.0
    else:
        derivedness = fecundity = 0.5
        connect_frac = 0.5

    components = {
        "success_rate": float(success_rate),
        "promoted_frac": float(promoted_frac),
        "avg_promoted_fitness": float(avg_fitness),
        "connect_frac": float(connect_frac),
        # CYCLE #32: sub-componenti esposte per trasparenza.
        "derivedness": float(derivedness),
        "fecundity": float(fecundity),
    }

    # Weighted sum to 0..100.
    score = (
        success_rate * 40.0
        + promoted_frac * 30.0
        + avg_fitness * 20.0
        + connect_frac * 10.0
    )

    if score >= 75:
        verdict = "Healthy"
    elif score >= 50:
        verdict = "Acceptable"
    elif score >= 30:
        verdict = "Needs attention"
    else:
        verdict = "Poor"

    return {
        "score": float(score),
        "components": components,
        "verdict": verdict,
    }


__all__ = ["compute_health_score"]
