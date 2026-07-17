"""Test offline per `skill_exposure_audit.audit_candidate_exposure`.

Strategia:
  - Costruisce embedding manuali (vettori 4D) per controllare esattamente
    quali candidate finiscono in top-k su quali episodi.
  - Tre scenari coperti:
      * empty inputs (degenerate)
      * candidate visibile (alta sim almeno con 1 episodio)
      * candidate invisibile (bassa sim con tutti gli episodi)
      * episodio con duplicati (verifica che la stessa skill non venga
        contata 2 volte per lo stesso episodio)
"""
from __future__ import annotations

import numpy as np

from verimem.skill_exposure_audit import audit_candidate_exposure


def _ep(eid: str, vec: list[float]) -> dict:
    return {"id": eid, "embedding": np.asarray(vec, dtype=np.float32)}


def _cand(sid: str, name: str, vec: list[float], trials: int = 0,
          age_days: float = 0.0) -> dict:
    return {
        "id": sid, "name": name, "trials": trials,
        "age_days": age_days,
        "embedding": np.asarray(vec, dtype=np.float32),
    }


def test_empty_candidates_returns_zeros() -> None:
    out = audit_candidate_exposure(candidates=[], episodes=[_ep("e1", [1, 0, 0, 0])])
    assert out["summary"]["n_candidates"] == 0
    assert out["summary"]["invisible_fraction"] == 0.0
    assert out["least_exposed"] == []


def test_empty_episodes_marks_all_invisible() -> None:
    cands = [_cand("c1", "x", [1, 0, 0, 0], trials=0)]
    out = audit_candidate_exposure(candidates=cands, episodes=[])
    s = out["summary"]
    assert s["n_episodes"] == 0
    assert s["invisible_count"] == 1
    assert s["invisible_fraction"] == 1.0
    assert s["candidates_with_trials_0"] == 1


def test_visible_candidate_counted_when_in_top_k() -> None:
    """Candidate aligned with episode → max similarity 1.0 → in top-k."""
    cands = [
        _cand("hit", "Aligned", [1, 0, 0, 0], trials=0),
        _cand("miss", "Orthogonal", [0, 1, 0, 0], trials=0),
        _cand("anti", "Opposite", [-1, 0, 0, 0], trials=0),
    ]
    eps = [_ep("e1", [1, 0, 0, 0]), _ep("e2", [1, 0, 0, 0])]
    out = audit_candidate_exposure(candidates=cands, episodes=eps, top_k=1)
    by_id = {d["skill_id"]: d for d in out["most_exposed"] + out["least_exposed"]}
    assert by_id["hit"]["exposure_count"] == 2     # in top-1 di entrambi gli episodi
    assert by_id["miss"]["exposure_count"] == 0    # orthogonal mai in top-1
    assert by_id["anti"]["exposure_count"] == 0    # opposite mai in top-1 (sim = -1)
    assert out["summary"]["invisible_count"] == 2
    assert out["summary"]["ever_seen_count"] == 1


def test_top_k_3_allows_more_visibility() -> None:
    """Con top_k=3 e 3 candidate, tutte e 3 entrano nel top-k di ogni episodio."""
    cands = [
        _cand("c1", "A", [1, 0, 0, 0]),
        _cand("c2", "B", [0, 1, 0, 0]),
        _cand("c3", "C", [0, 0, 1, 0]),
    ]
    eps = [_ep("e1", [0.5, 0.5, 0.5, 0])]
    out = audit_candidate_exposure(candidates=cands, episodes=eps, top_k=3)
    s = out["summary"]
    assert s["ever_seen_count"] == 3
    assert s["invisible_count"] == 0


def test_top_k_capped_at_n_candidates() -> None:
    """Se top_k > n_candidates, l'audit clampa effettivamente."""
    cands = [_cand("only", "alone", [1, 0, 0, 0])]
    eps = [_ep("e1", [1, 0, 0, 0])]
    out = audit_candidate_exposure(candidates=cands, episodes=eps, top_k=10)
    assert out["summary"]["top_k"] == 1
    assert out["summary"]["ever_seen_count"] == 1


def test_ever_seen_but_no_trials_metric() -> None:
    """Misura il mistero secondario: candidate esposta semanticamente
    ma con 0 trials reali (= update_fitness non viene mai chiamato)."""
    cands = [
        _cand("seen_no_trial", "A", [1, 0, 0, 0], trials=0),
        _cand("seen_w_trial", "B", [0.99, 0.1, 0, 0], trials=5),
    ]
    eps = [_ep("e1", [1, 0, 0, 0])]
    out = audit_candidate_exposure(candidates=cands, episodes=eps, top_k=2)
    s = out["summary"]
    assert s["ever_seen_count"] == 2
    # Solo seen_no_trial ha trials==0 ma è stata esposta
    assert s["ever_seen_but_no_trials"] == 1


def test_zero_vector_does_not_crash() -> None:
    """Una candidate con embedding tutto-zero non deve crashare (div-by-zero)."""
    cands = [
        _cand("zero", "Zero", [0, 0, 0, 0]),
        _cand("real", "Real", [1, 0, 0, 0]),
    ]
    eps = [_ep("e1", [1, 0, 0, 0])]
    out = audit_candidate_exposure(candidates=cands, episodes=eps, top_k=1)
    by_id = {d["skill_id"]: d for d in out["most_exposed"] + out["least_exposed"]}
    assert by_id["real"]["exposure_count"] == 1
    assert by_id["zero"]["exposure_count"] == 0


def test_select_invisible_for_retire_filters_correctly() -> None:
    """Selezione retire: solo invisible + old + zero-trials."""
    from verimem.skill_exposure_audit import select_invisible_for_retire

    # Fingo un audit_result manuale
    audit_result = {
        "least_exposed": [
            # 1: invisible + vecchio + 0 trials → eligible
            {"skill_id": "a", "name": "old-invisible", "exposure_count": 0,
             "age_days": 30.0, "max_similarity": 0.1, "trials": 0,
             "mean_similarity": 0.05, "rank_when_best": 99},
            # 2: invisible ma GIOVANE → skip
            {"skill_id": "b", "name": "young-invisible", "exposure_count": 0,
             "age_days": 3.0, "max_similarity": 0.1, "trials": 0,
             "mean_similarity": 0.05, "rank_when_best": 99},
            # 3: invisible + vecchio ma con TRIALS → skip
            {"skill_id": "c", "name": "old-invisible-with-trials", "exposure_count": 0,
             "age_days": 30.0, "max_similarity": 0.1, "trials": 5,
             "mean_similarity": 0.05, "rank_when_best": 99},
            # 4: visibile (exposure>0) → skip
            {"skill_id": "d", "name": "visible", "exposure_count": 7,
             "age_days": 30.0, "max_similarity": 0.8, "trials": 0,
             "mean_similarity": 0.5, "rank_when_best": 1},
            # 5: invisible + molto vecchio + 0 trials → eligible, ordinato per primo
            {"skill_id": "e", "name": "very-old", "exposure_count": 0,
             "age_days": 90.0, "max_similarity": 0.1, "trials": 0,
             "mean_similarity": 0.05, "rank_when_best": 200},
        ],
        "most_exposed": [],
    }
    eligible = select_invisible_for_retire(audit_result=audit_result, min_age_days=14.0)
    ids = [e["skill_id"] for e in eligible]
    # Solo a ed e sono eligible
    assert set(ids) == {"a", "e"}
    # Ordinati per age decrescente: e (90d) prima di a (30d)
    assert ids == ["e", "a"]


def test_invisible_all_contains_every_invisible_not_just_50() -> None:
    """Regression: la lista invisibili NON deve essere cappata a 50.
    Il select_invisible_for_retire ha bisogno di vederle tutte."""
    # 60 candidate ortogonali due a due tra loro (sim ≈ 0), top_k=1
    # → 59 saranno invisibili (solo 1 wins ogni episodio)
    cands = []
    n = 60
    for i in range(n):
        vec = [0.0] * n
        vec[i] = 1.0
        cands.append(_cand(f"c{i}", f"name{i}", vec, trials=0))
    # Un solo episodio aligned con c0
    eps = [_ep("e1", [1.0] + [0.0] * (n - 1))]
    out = audit_candidate_exposure(candidates=cands, episodes=eps, top_k=1)
    assert out["summary"]["invisible_count"] == n - 1
    # invisible_all DEVE contenere tutti gli n-1 invisibili, non solo 50
    assert len(out["invisible_all"]) == n - 1
    # least_exposed resta cappato a 50 per UI compat
    assert len(out["least_exposed"]) == 50


def test_select_invisible_respects_require_zero_trials_off() -> None:
    """Se require_zero_trials=False, anche candidate con trials>0 entrano."""
    from verimem.skill_exposure_audit import select_invisible_for_retire

    audit_result = {
        "least_exposed": [
            {"skill_id": "c", "name": "old-with-trials", "exposure_count": 0,
             "age_days": 30.0, "max_similarity": 0.1, "trials": 5,
             "mean_similarity": 0.05, "rank_when_best": 99},
        ],
        "most_exposed": [],
    }
    eligible = select_invisible_for_retire(
        audit_result=audit_result, min_age_days=14.0, require_zero_trials=False,
    )
    assert [e["skill_id"] for e in eligible] == ["c"]


def test_summary_stats_match_details() -> None:
    """Le aggregate (mean/median exposure) devono essere coerenti col dettaglio."""
    cands = [
        _cand("a", "A", [1, 0, 0, 0]),
        _cand("b", "B", [0.95, 0.1, 0, 0]),
        _cand("c", "C", [0, 1, 0, 0]),
    ]
    eps = [_ep("e1", [1, 0, 0, 0]), _ep("e2", [1, 0, 0, 0])]
    out = audit_candidate_exposure(candidates=cands, episodes=eps, top_k=2)
    s = out["summary"]
    # a e b sempre in top-2, c mai
    assert s["ever_seen_count"] == 2
    assert s["invisible_count"] == 1
    assert s["mean_exposure"] == (2 + 2 + 0) / 3
