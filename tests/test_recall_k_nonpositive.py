"""recall(k<=0) deve restituire [] — non (quasi) l'intero corpus.

Buco robustezza (hunt 2026-06-04): lo slice ``np.argsort(-sims)[:k]`` con k
NEGATIVO restituisce N-|k| risultati (k=-1 -> tutto tranne l'ultimo) invece di
vuoto; con k=0 il comportamento e' [] ma e' incidentale. Un k<=0 puo' arrivare da
aritmetica del caller (limit-offset) o da input malevolo -> sversa il corpus.
Difesa: guard k<=0 -> [] all'inizio di ogni entrypoint di recall.

Hermetic: DB temporaneo; gate-independent (delenv) cosi' il test non dipende
dall'ambiente live di Aurelio.
"""
from __future__ import annotations

import pytest

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory
from verimem.semantic import Fact, SemanticMemory


@pytest.fixture(autouse=True)
def _gate_off(monkeypatch):
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)


def _seed_facts(sm: SemanticMemory, n: int) -> None:
    for i in range(n):
        sm.store(Fact(proposition=f"fatto {i} sulla procedura zorp di deploy",
                      topic="t", source_episodes=["ep"]))


def _seed_eps(em: EpisodicMemory, n: int, *, ctx=None) -> None:
    for i in range(n):
        em.store(
            Episode(id=f"e{i}", task_id=f"e{i}", task_text=f"procedura zorp deploy {i}",
                    outcome="success", final_answer="x",
                    traces=[Trace(step=1, thought="t", action="a", action_input="{}", observation="o")],
                    tokens_used=1),
            context_emb=ctx,
        )


def test_semantic_recall_negative_k_returns_empty(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed_facts(sm, 5)
    got = sm.recall("procedura zorp deploy", k=-1)
    assert got == [], f"k=-1 deve dare [] (non {len(got)} fatti del corpus)"


def test_semantic_recall_zero_k_returns_empty(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed_facts(sm, 5)
    assert sm.recall("procedura zorp deploy", k=0) == []


def test_episodic_recall_negative_k_returns_empty(tmp_path):
    em = EpisodicMemory(tmp_path / "e.db")
    _seed_eps(em, 5)
    got = em.recall("procedura zorp deploy", k=-1)
    assert got == [], f"k=-1 deve dare [] (non {len(got)} episodi del corpus)"


def test_episodic_recall_by_context_negative_k_returns_empty(tmp_path):
    from verimem import embedding as emb
    em = EpisodicMemory(tmp_path / "e.db")
    ctx = emb.encode("contesto cognitivo zorp deploy")
    _seed_eps(em, 5, ctx=ctx)
    got = em.recall_by_context(ctx, k=-1)
    assert got == [], f"recall_by_context k=-1 deve dare [] (non {len(got)})"
