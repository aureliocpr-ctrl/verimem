"""Audit dell'esposizione semantica delle skill candidate.

CYCLE #7 — diagnostica evidence-driven per la "stuck candidate" question.

Background (cycle #3 sensor `skill_stuck_diagnostic`):
  87% delle candidate ha 0 trials. Cycle #3 ha tagged la causa come
  "Catch-22 retrieve usa promoted only" ma la verifica del codice
  (`wake.py:573-580`, `mcp_server.py:3940-3942`) mostra che il fallback
  include candidate. Quindi la diagnosi era IMPRECISA.

Ipotesi corretta da verificare empiricamente:
  Le candidate non vengono mai invocate non perché il retrieve le esclude
  (lo fa solo come prima opzione, poi fallback) ma perché il loro
  `trigger_embedding` non raggiunge MAI il top-k semantico su task reali.
  Su `wake.retrieve(k=top_k, status='candidate')` con remaining<<n_candidate,
  solo le candidate più semanticamente vicine al task entrano nel pool.
  Se una candidate ha trigger generico/distante, resta stuck a 0 trials.

Misura proposta:
  Per ogni candidate c e ogni episodio recente e, calcola
  cos(c.trigger_embedding, e.summary_embedding). Per ogni e, ranking delle
  candidate per similarity. Conta per ogni candidate quante volte sarebbe
  stata nei top-k (configurabile, default 3).

  exposure_count[c] = sum over episodes of 1{c in top_k(e)}

  - exposure_count == 0 → candidate "invisibile": nessun task recente la
    pesca anche nel pool candidate. Senza intervento, resterà a 0 trials.
  - exposure_count > 0 ma trials == 0 → mistero secondario: la skill ENTRA
    nel pool ma update_fitness non viene chiamato. Tipicamente: wake() non
    è il path di esecuzione, oppure skills_used non viene popolato.

Output azionabile:
  `summary.invisible_fraction` >0.7 → fix possibili: (a) retire by age
  per skill invisibili vecchie, (b) trigger rephrase suggestion, (c) garantire
  un candidate slot dedicato nel pool retrieval anche quando promoted è pieno.

API:
  audit_candidate_exposure(skills, episodes, top_k=3, recent_n=200)
  → dict con summary + per-skill detail.

Pure-function, no I/O, no DB. I caller (CLI/MCP tool) caricano i dati e
passano in input. Questo modulo non sa di SQLite — testabile in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class CandidateExposure:
    """Per-skill exposure metric."""
    skill_id: str
    name: str
    trials: int
    age_days: float
    exposure_count: int           # quanti episodi recenti la mettono in top_k
    max_similarity: float         # max cosine vs gli episodi recenti
    mean_similarity: float        # media cosine vs gli episodi recenti
    rank_when_best: int           # rank della skill nel best-episode (0 = primo)


def _cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine matrix between rows of a [n×d] and rows of b [m×d].

    Assumes both already L2-normalised (which `embedding.encode` does).
    Returns [n×m]. Falls back to explicit normalisation if not unit-length.
    """
    if a.size == 0 or b.size == 0:
        return np.zeros((a.shape[0], b.shape[0]), dtype=np.float32)
    a_norm = np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = np.linalg.norm(b, axis=1, keepdims=True)
    # Avoid div-by-zero on degenerate zero vectors.
    a_norm = np.where(a_norm > 0, a_norm, 1.0)
    b_norm = np.where(b_norm > 0, b_norm, 1.0)
    a_unit = a / a_norm
    b_unit = b / b_norm
    return (a_unit @ b_unit.T).astype(np.float32)


def audit_candidate_exposure(
    *,
    candidates: list[dict[str, Any]],
    episodes: list[dict[str, Any]],
    top_k: int = 3,
    now: float | None = None,
) -> dict[str, Any]:
    """Misura quante volte ogni candidate sarebbe entrata nel top-k semantico.

    Args:
        candidates: lista di dict con chiavi {id, name, trials, age_days,
            embedding (np.ndarray 1D)}.
        episodes: lista di dict con chiavi {id, embedding (np.ndarray 1D)}.
        top_k: dimensione top-k del ranking per episodio (default 3).
        now: epoch override (testability), default tempo corrente.

    Returns:
        {
          "summary": {
            "n_candidates": int, "n_episodes": int, "top_k": int,
            "invisible_count": int,        # exposure_count == 0
            "invisible_fraction": float,   # invisible / n_candidates
            "ever_seen_count": int,        # exposure_count > 0
            "mean_exposure": float,
            "median_exposure": float,
            "candidates_with_trials_0": int,
            "ever_seen_but_no_trials": int,  # mistero secondario
          },
          "least_exposed": list[CandidateExposure as dict, sorted by exposure asc],
          "most_exposed": list[same, sorted by exposure desc, top 20],
        }
    """
    if not candidates:
        return {
            "summary": {
                "n_candidates": 0, "n_episodes": len(episodes), "top_k": top_k,
                "invisible_count": 0, "invisible_fraction": 0.0,
                "ever_seen_count": 0, "mean_exposure": 0.0, "median_exposure": 0.0,
                "candidates_with_trials_0": 0, "ever_seen_but_no_trials": 0,
            },
            "least_exposed": [], "most_exposed": [], "invisible_all": [],
        }
    if not episodes:
        # Nessun episodio recente: tutte le candidate sono per definizione "invisibili" su questa finestra.
        details = [
            CandidateExposure(
                skill_id=c["id"], name=c.get("name", ""), trials=int(c.get("trials", 0)),
                age_days=float(c.get("age_days", 0.0)),
                exposure_count=0, max_similarity=0.0, mean_similarity=0.0,
                rank_when_best=-1,
            )
            for c in candidates
        ]
        return {
            "summary": {
                "n_candidates": len(candidates), "n_episodes": 0, "top_k": top_k,
                "invisible_count": len(candidates), "invisible_fraction": 1.0,
                "ever_seen_count": 0, "mean_exposure": 0.0, "median_exposure": 0.0,
                "candidates_with_trials_0": sum(1 for c in candidates if int(c.get("trials", 0)) == 0),
                "ever_seen_but_no_trials": 0,
            },
            "least_exposed": [c.__dict__ for c in details],
            "most_exposed": [],
            "invisible_all": [c.__dict__ for c in details],
        }

    cand_emb = np.stack([np.asarray(c["embedding"], dtype=np.float32) for c in candidates])
    ep_emb = np.stack([np.asarray(e["embedding"], dtype=np.float32) for e in episodes])

    # sim_matrix[i,j] = cos(episode_i, candidate_j)
    sim_matrix = _cosine_matrix(ep_emb, cand_emb)  # [n_episodes × n_candidates]

    n_episodes, n_candidates = sim_matrix.shape
    effective_k = min(top_k, n_candidates)

    # Per ogni riga (episodio), prendi gli indici top-k delle candidate.
    # argsort desc su ogni riga.
    top_idx = np.argsort(-sim_matrix, axis=1)[:, :effective_k]  # [n_episodes × top_k]

    # exposure_count[c] = quante righe contengono c nei loro top-k indici
    exposure = np.zeros(n_candidates, dtype=np.int64)
    for row in top_idx:
        # row è un array di indici candidate (top-k per quell'episodio)
        # Incrementa exposure[c] per ogni c in row. Una candidate non può apparire 2 volte nella stessa row.
        exposure[row] += 1

    # Per-candidate max sim e rank-when-best
    max_sim_per_cand = sim_matrix.max(axis=0)          # [n_candidates]
    mean_sim_per_cand = sim_matrix.mean(axis=0)        # [n_candidates]
    best_episode_idx = sim_matrix.argmax(axis=0)       # [n_candidates]
    # rank della candidate c nell'episodio best_episode_idx[c]
    rank_when_best = np.zeros(n_candidates, dtype=np.int64)
    for c_idx in range(n_candidates):
        e_idx = int(best_episode_idx[c_idx])
        row = sim_matrix[e_idx]
        # Argsort desc: posizione di c_idx nella sorted row
        rank_when_best[c_idx] = int(np.argsort(-row).tolist().index(c_idx))

    details = [
        CandidateExposure(
            skill_id=c["id"],
            name=c.get("name", ""),
            trials=int(c.get("trials", 0)),
            age_days=float(c.get("age_days", 0.0)),
            exposure_count=int(exposure[i]),
            max_similarity=float(max_sim_per_cand[i]),
            mean_similarity=float(mean_sim_per_cand[i]),
            rank_when_best=int(rank_when_best[i]),
        )
        for i, c in enumerate(candidates)
    ]

    invisible = [d for d in details if d.exposure_count == 0]
    ever_seen = [d for d in details if d.exposure_count > 0]
    no_trials_total = sum(1 for d in details if d.trials == 0)
    ever_seen_but_no_trials = sum(1 for d in ever_seen if d.trials == 0)
    exposures_arr = np.array([d.exposure_count for d in details])

    summary = {
        "n_candidates": n_candidates,
        "n_episodes": n_episodes,
        "top_k": effective_k,
        "invisible_count": len(invisible),
        "invisible_fraction": len(invisible) / n_candidates if n_candidates > 0 else 0.0,
        "ever_seen_count": len(ever_seen),
        "mean_exposure": float(exposures_arr.mean()),
        "median_exposure": float(np.median(exposures_arr)),
        "candidates_with_trials_0": no_trials_total,
        "ever_seen_but_no_trials": ever_seen_but_no_trials,
    }

    details_sorted_asc = sorted(details, key=lambda d: (d.exposure_count, d.max_similarity))
    details_sorted_desc = sorted(details, key=lambda d: -d.exposure_count)

    # `least_exposed` è capped per UI dashboard (display 50 row), ma il caller
    # del retire selector ha bisogno della lista COMPLETA invisibili. Esporrla
    # come campo dedicato `invisible_all` evita di dover ri-eseguire l'audit.
    invisible_all = [d.__dict__ for d in details_sorted_asc if d.exposure_count == 0]

    return {
        "summary": summary,
        "least_exposed": [d.__dict__ for d in details_sorted_asc[:50]],
        "most_exposed": [d.__dict__ for d in details_sorted_desc[:20]],
        "invisible_all": invisible_all,
    }


def select_invisible_for_retire(
    *,
    audit_result: dict[str, Any],
    min_age_days: float = 14.0,
    require_zero_trials: bool = True,
) -> list[dict[str, Any]]:
    """Seleziona candidate "morte alla nascita" pronte per retire.

    Criteri (TUTTI obbligatori):
      - `exposure_count == 0` (mai entrata nel top-k semantico)
      - `age_days >= min_age_days` (default 14 giorni di grace period)
      - `trials == 0` se `require_zero_trials` (default True)

    Args:
        audit_result: output di `audit_candidate_exposure`.
        min_age_days: età minima per il retire (default 14).
        require_zero_trials: se True (default), salta candidate che hanno
            trials > 0 anche se invisibili nei recenti — significa che sono
            state usate in passato.

    Returns:
        Lista di dict {skill_id, name, age_days, max_similarity, trials,
        exposure_count}, ordinata per età decrescente (oldest first).

    NOTE: pure-function, non muta nulla. Il caller decide se applicare
    `skill.status = 'retired'` (vedi `mcp_server.hippo_skill_retire_invisible`).
    """
    # Prefer the full invisible list when present; fall back to `least_exposed`
    # (cap=50) for compatibility with audit_result dict that pre-dates the
    # `invisible_all` field.
    invisible_source = audit_result.get("invisible_all")
    if invisible_source is None:
        invisible_source = [d for d in audit_result.get("least_exposed", [])
                            if d["exposure_count"] == 0]
    eligible = []
    for d in invisible_source:
        if d["exposure_count"] != 0:
            continue
        if d["age_days"] < min_age_days:
            continue
        if require_zero_trials and d["trials"] > 0:
            continue
        eligible.append({
            "skill_id": d["skill_id"],
            "name": d["name"],
            "age_days": d["age_days"],
            "max_similarity": d["max_similarity"],
            "trials": d["trials"],
            "exposure_count": d["exposure_count"],
        })
    eligible.sort(key=lambda x: -x["age_days"])
    return eligible


def load_audit_inputs_from_agent(
    *,
    agent: Any,
    recent_n: int = 200,
    now: float | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Adapter: carica candidate + episodi recenti per audit_candidate_exposure.

    Legge direttamente dai SQLite per ottenere i BLOB embedding pre-calcolati,
    evitando di ri-encodare con sentence-transformers a runtime.

    Args:
        agent: WakeAgent (uses agent.skills.db_path and agent.memory.episodes_db).
        recent_n: numero di episodi recenti da considerare (default 200).
        now: epoch override per `age_days` (testability).

    Returns:
        (candidates, episodes) in formato pronto per
        `audit_candidate_exposure(candidates=..., episodes=...)`.

    Raises:
        FileNotFoundError se i DB non esistono ancora (corpus vuoto).
    """
    import sqlite3
    import time as _time

    from . import embedding

    if now is None:
        now = _time.time()

    candidates: list[dict[str, Any]] = []
    skills_db = getattr(agent.skills, "db_path", None)
    if skills_db is None:
        return [], []
    with sqlite3.connect(skills_db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, name, trials, created_at, trigger_embedding "
            "FROM skills WHERE status = 'candidate'"
        ).fetchall()
        for r in rows:
            try:
                emb = embedding.deserialize(r["trigger_embedding"])
            except Exception:
                continue
            candidates.append({
                "id": r["id"],
                "name": r["name"] or "",
                "trials": int(r["trials"] or 0),
                "age_days": max(0.0, (now - float(r["created_at"])) / 86400.0),
                "embedding": emb,
            })

    episodes: list[dict[str, Any]] = []
    memory = getattr(agent, "memory", None)
    ep_db = getattr(memory, "episodes_db", None) if memory else None
    if ep_db is None:
        return candidates, []
    with sqlite3.connect(ep_db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, summary_embedding FROM episodes "
            "ORDER BY created_at DESC LIMIT ?", (int(recent_n),),
        ).fetchall()
        for r in rows:
            blob = r["summary_embedding"]
            if blob is None:
                continue
            try:
                emb = embedding.deserialize(blob)
            except Exception:
                continue
            episodes.append({"id": r["id"], "embedding": emb})

    return candidates, episodes


__all__ = [
    "audit_candidate_exposure", "CandidateExposure",
    "select_invisible_for_retire",
    "load_audit_inputs_from_agent",
]
