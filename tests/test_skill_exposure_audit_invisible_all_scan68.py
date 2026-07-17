"""TDD — audit_candidate_exposure deve esporre 'invisible_all' in TUTTI i rami
(rescan2 HIGH: KeyError 'invisible_all' su corpus senza emerging skills).

Il ramo principale ritorna 'invisible_all', ma i due early-return (candidates
vuote / episodes vuoti) lo OMETTEVANO → il consumer mcp_server.py:8603
(len(audit["invisible_all"])) e select_invisible_for_retire crashavano con
KeyError su corpus senza skill candidate / senza episodi recenti.

Fix-class: contratto consistente (chiave sempre presente) protegge tutti i
consumer, non solo quello segnalato.
"""
from __future__ import annotations

from verimem.skill_exposure_audit import audit_candidate_exposure


def test_no_candidates_still_exposes_invisible_all():
    out = audit_candidate_exposure(candidates=[], episodes=[], top_k=3)
    assert "invisible_all" in out, "early-return (no candidates) deve avere invisible_all"
    assert out["invisible_all"] == []


def test_candidates_but_no_episodes_all_invisible():
    cands = [
        {"id": "s1", "name": "skill one", "trials": 0, "age_days": 2.0},
        {"id": "s2", "name": "skill two", "trials": 1, "age_days": 9.0},
    ]
    out = audit_candidate_exposure(candidates=cands, episodes=[], top_k=3)
    assert "invisible_all" in out, "early-return (no episodes) deve avere invisible_all"
    # senza episodi tutte le candidate sono invisibili
    assert len(out["invisible_all"]) == 2
    ids = {d["skill_id"] for d in out["invisible_all"]}
    assert ids == {"s1", "s2"}
