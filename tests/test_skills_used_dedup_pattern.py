"""CYCLE #17 — regression tests per il pattern 'loop su skills_used dup'.

Background: cycle #16 critic-orchestrator counterexample worker ha trovato
che hippo_record_episode handler aveva double-count bug se l'host mandava
skills_used con duplicati. Investigato pattern in tutto il codebase:

  - hippoagent/dashboard_routes/chat.py:140 (user feedback) — SAME BUG
  - hippoagent/memory.py:1364 (skill_usage_histogram) — over-count
  - hippoagent/sleep.py:90,137 — marginale (statistiche identiche)

Questo file pinna il comportamento corretto per chat.py + memory.py.
"""
from __future__ import annotations

import time

import pytest

from engram.memory import Episode, EpisodicMemory


@pytest.fixture
def memory(tmp_path):
    return EpisodicMemory(db_path=tmp_path / "ep.db")


def _store_ep(memory, eid: str, *, skills_used: list[str],
              created_at: float | None = None) -> None:
    memory.store(Episode(
        id=eid, task_id=f"t-{eid}", task_text=f"task-{eid}",
        outcome="success", final_answer="a",
        tokens_used=0, skills_used=skills_used, traces=[],
        created_at=created_at if created_at is not None else time.time(),
    ))


# ---------- memory.skill_usage_histogram ---------------------------------


def test_histogram_counts_episode_not_occurrence(memory):
    """1 episodio con skills_used=['sk1','sk1','sk1'] deve contare 1 (non 3)."""
    _store_ep(memory, "e1", skills_used=["sk1", "sk1", "sk1"])
    hist = memory.skill_usage_histogram()
    assert hist == {"sk1": 1}, f"BUG: histogram conta occorrenze invece di episodi: {hist}"


def test_histogram_no_dup_correct(memory):
    """Sanity: 2 episodi unique con 1 skill each → counts 1 ciascuno."""
    _store_ep(memory, "e1", skills_used=["sk1"])
    _store_ep(memory, "e2", skills_used=["sk2"])
    hist = memory.skill_usage_histogram()
    assert hist == {"sk1": 1, "sk2": 1}


def test_histogram_mixed_dups_correct(memory):
    """ep1 sk1×3, sk2×1 + ep2 sk1×2 = counts sk1=2, sk2=1."""
    _store_ep(memory, "e1", skills_used=["sk1", "sk1", "sk2", "sk1"])
    _store_ep(memory, "e2", skills_used=["sk1", "sk1"])
    hist = memory.skill_usage_histogram()
    assert hist == {"sk1": 2, "sk2": 1}


# ---------- chat.py user feedback dedup pattern --------------------------
# I 2 test tautologici che stavano qui (test_chat_feedback_dedup_pattern_via_
# dict_fromkeys / test_dedup_preserves_first_occurrence_order) asserivano SOLO
# su dict.fromkeys (stdlib) ricostruito localmente -> NON esercitavano chat.py,
# quindi passavano anche col dedup ROTTO = FALSA COPERTURA. Rimossi 2026-06-05 e
# sostituiti da copertura REALE della route POST /api/feedback in
# tests/test_dashboard_api.py::test_feedback_dedups_skills_before_update_fitness
# (verificato che FALLISCE se il dedup di chat.py viene rimosso). Le 3 funzioni
# histogram sopra restano: chiamano davvero memory.skill_usage_histogram().
